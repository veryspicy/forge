"""多供应商 AI 路由（额度治理 + 加权负载均衡 + 故障转移）。

设计要点
--------
1. **数据来源**：``ai_config_service`` 的供应商集合（``system_configs['ai.providers']``），
   每个供应商可配置 ``daily_request_limit`` / ``daily_token_limit`` / ``weight`` /
   ``priority``；聚合供应商的每个上游端点都会展开成独立候选端点。
2. **额度治理**：当日用量记录在 ``ai_usage_daily``（仓储层原子自增）。任一维度触顶即
   该供应商当日不再被选中（``quota_skipped``），并把 ``quota_hits`` 累加用于运营观察。
3. **负载均衡**：同一 ``priority`` 内按「剩余额度比例 → 单位权重负载 → 日请求量」排序，
   ``weight`` 越大分到的流量越多，天然形成加权分流。
4. **故障转移**：调用异常按供应商维度熔断（进程内冷却窗口），冷却中的供应商排到最后
   但仍会兜底尝试，避免全部冷却时彻底不可用；上游返回额度类错误（402/429/quota 字样）
   直接锁定该供应商当日不再尝试。
5. **降级判定**：所有候选都不可用 → 返回 ``ok=False``，由 API 层落 ``ai_handoff_requests``
   （转人工工单）并给用户可读的兜底话术。
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from forge.application.services import ai_config_service
from forge.infrastructure.persistence.models import ORMAIUsageDaily
from forge.infrastructure.persistence.repositories.ai_chat_repo import (
    SQLAlchemyAIChatRepository,
    business_day,
)
from forge.infrastructure.services.llm_client import CHAT_TIMEOUT, LLMConfig, chat_completion

logger = logging.getLogger(__name__)

DEFAULT_WEIGHT = 10
DEFAULT_PRIORITY = 50
COOLDOWN_SECONDS = 120

# 上游返回这些信号时，视为「该供应商额度用尽」，当日不再尝试。
QUOTA_STATUS_CODES = {402, 429}
QUOTA_KEYWORDS = (
    "quota",
    "insufficient",
    "exceeded",
    "rate limit",
    "too many requests",
    "balance",
    "credit",
    "neurons",
)

# provider_id -> 冷却截止时间戳（进程内）
_COOLDOWN_UNTIL: dict[str, float] = {}
# (provider_id, 业务日) -> 当日额度已锁定
_QUOTA_LOCK: set[tuple[str, str]] = set()


@dataclass(frozen=True)
class RouteEndpoint:
    """一个可调用端点（供应商或聚合供应商中的某个上游）。"""

    provider_id: str
    provider_name: str
    upstream_id: str | None
    upstream_name: str | None
    cfg: LLMConfig
    weight: int
    priority: int
    daily_request_limit: int
    daily_token_limit: int

    @property
    def label(self) -> str:
        if self.upstream_name:
            return f"{self.provider_name} / {self.upstream_name}"
        return self.provider_name


@dataclass
class RouteAttempt:
    """一次候选端点的尝试记录（用于运营排查与响应回执）。"""

    provider_id: str
    label: str
    status: str  # ok / failed / quota_skipped / quota_exhausted
    detail: str = ""
    latency_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "label": self.label,
            "status": self.status,
            "detail": self.detail,
            "latency_ms": self.latency_ms,
        }


@dataclass
class RouteResult:
    """路由调用的最终结果。"""

    ok: bool
    content: str = ""
    model: str = ""
    provider_id: str | None = None
    provider_name: str | None = None
    upstream_name: str | None = None
    latency_ms: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    reason: str = ""
    detail: str = ""
    attempts: list[RouteAttempt] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "reason": self.reason,
            "detail": self.detail,
            "provider_id": self.provider_id,
            "provider_name": self.provider_name,
            "upstream_name": self.upstream_name,
            "model": self.model,
            "latency_ms": self.latency_ms,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "attempts": [attempt.to_dict() for attempt in self.attempts],
        }


# --------------------------------------------------------------------------- #
# 端点装载
# --------------------------------------------------------------------------- #


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def build_endpoints(store: dict[str, Any], secrets: dict[str, str]) -> list[RouteEndpoint]:
    """把供应商配置展开成候选端点列表（已启用供应商 + 已启用上游）。"""
    endpoints: list[RouteEndpoint] = []
    for provider in store.get("items") or []:
        if not provider.get("enabled", True):
            continue
        provider_id = str(provider.get("id") or "")
        if not provider_id:
            continue
        weight = max(1, min(100, _as_int(provider.get("weight"), DEFAULT_WEIGHT)))
        priority = max(1, min(99, _as_int(provider.get("priority"), DEFAULT_PRIORITY)))
        request_limit = max(0, _as_int(provider.get("daily_request_limit"), 0))
        token_limit = max(0, _as_int(provider.get("daily_token_limit"), 0))
        for label, cfg in ai_config_service.provider_endpoint_specs(provider, secrets):
            if not cfg.base_url:
                continue
            upstream_name = label if provider.get("type") == ai_config_service.PROVIDER_TYPE_AGGREGATE else None
            endpoints.append(
                RouteEndpoint(
                    provider_id=provider_id,
                    provider_name=str(provider.get("name") or provider_id),
                    upstream_id=None,
                    upstream_name=upstream_name,
                    cfg=cfg,
                    weight=weight,
                    priority=priority,
                    daily_request_limit=request_limit,
                    daily_token_limit=token_limit,
                )
            )
    return endpoints


# --------------------------------------------------------------------------- #
# 额度与排序
# --------------------------------------------------------------------------- #


def _usage_of(usage: dict[str, ORMAIUsageDaily], provider_id: str) -> tuple[int, int]:
    row = usage.get(provider_id)
    if row is None:
        return 0, 0
    return int(row.requests or 0), int(row.tokens or 0)


def _exhausted(endpoint: RouteEndpoint, usage: dict[str, ORMAIUsageDaily], day: str) -> bool:
    if (endpoint.provider_id, day) in _QUOTA_LOCK:
        return True
    requests, tokens = _usage_of(usage, endpoint.provider_id)
    if endpoint.daily_request_limit > 0 and requests >= endpoint.daily_request_limit:
        return True
    return endpoint.daily_token_limit > 0 and tokens >= endpoint.daily_token_limit


def _cooldown_active(provider_id: str) -> bool:
    until = _COOLDOWN_UNTIL.get(provider_id)
    return bool(until and until > time.monotonic())


def order_endpoints(
    endpoints: list[RouteEndpoint],
    usage: dict[str, ORMAIUsageDaily],
) -> list[RouteEndpoint]:
    """负载均衡排序：冷却的靠后 → priority 升序 → 剩余额度比例降序 → 单位权重负载升序。"""

    def key(endpoint: RouteEndpoint) -> tuple[int, int, float, float]:
        requests, tokens = _usage_of(usage, endpoint.provider_id)
        request_ratio = 1.0
        if endpoint.daily_request_limit > 0:
            request_ratio = max(0.0, 1.0 - requests / endpoint.daily_request_limit)
        token_ratio = 1.0
        if endpoint.daily_token_limit > 0:
            token_ratio = max(0.0, 1.0 - tokens / endpoint.daily_token_limit)
        remaining = min(request_ratio, token_ratio)
        load = requests / max(1, endpoint.weight)
        return (1 if _cooldown_active(endpoint.provider_id) else 0, endpoint.priority, -remaining, load)

    return sorted(endpoints, key=key)


# --------------------------------------------------------------------------- #
# 错误归类
# --------------------------------------------------------------------------- #


def _describe_error(exc: Exception) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        try:
            body = exc.response.text or ""
        except Exception:  # pragma: no cover - 极端情况
            body = ""
        return f"HTTP {exc.response.status_code}: {body[:200]}".strip()
    return f"{type(exc).__name__}: {exc}"[:300]


def _is_quota_error(exc: Exception) -> bool:
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code in QUOTA_STATUS_CODES:
        return True
    text = str(exc).lower()
    return any(keyword in text for keyword in QUOTA_KEYWORDS)


def _token_usage(usage: dict[str, Any] | None) -> tuple[int, int]:
    if not isinstance(usage, dict):
        return 0, 0
    tokens_in = _as_int(usage.get("prompt_tokens") or usage.get("input_tokens"), 0)
    tokens_out = _as_int(usage.get("completion_tokens") or usage.get("output_tokens"), 0)
    return tokens_in, tokens_out


def reset_runtime_state() -> None:
    """清空进程内冷却与额度锁（测试用）。"""
    _COOLDOWN_UNTIL.clear()
    _QUOTA_LOCK.clear()


# --------------------------------------------------------------------------- #
# 路由主流程
# --------------------------------------------------------------------------- #


async def route_chat(
    db: AsyncSession,
    messages: list[dict[str, Any]],
    *,
    timeout: float = CHAT_TIMEOUT,
) -> RouteResult:
    """按额度与负载顺序择优调用，失败自动换供应商。

    返回 ``RouteResult``；``ok=False`` 时由调用方决定降级动作（转人工工单）。
    """
    store, secrets = await ai_config_service.load_providers_snapshot(db)
    if not store.get("enabled", True):
        return RouteResult(ok=False, reason="disabled", detail="AI 服务已关闭")

    endpoints = build_endpoints(store, secrets)
    if not endpoints:
        return RouteResult(ok=False, reason="no_provider", detail="未配置可用的 AI 供应商")

    day = business_day()
    usage = await SQLAlchemyAIChatRepository.usage_today(db, sorted({item.provider_id for item in endpoints}))
    ordered = order_endpoints(endpoints, usage)

    attempts: list[RouteAttempt] = []
    for endpoint in ordered:
        if _exhausted(endpoint, usage, day):
            await SQLAlchemyAIChatRepository.bump_usage(db, provider_id=endpoint.provider_id, quota_hits=1)
            attempts.append(
                RouteAttempt(
                    provider_id=endpoint.provider_id,
                    label=endpoint.label,
                    status="quota_exhausted",
                    detail="当日额度已用尽",
                )
            )
            continue

        started = time.perf_counter()
        try:
            result = await chat_completion(endpoint.cfg, messages, timeout=timeout)
        except Exception as exc:  # noqa: BLE001 - 任何上游异常都要能切下一个供应商
            latency_ms = int((time.perf_counter() - started) * 1000)
            detail = _describe_error(exc)
            _COOLDOWN_UNTIL[endpoint.provider_id] = time.monotonic() + COOLDOWN_SECONDS
            if _is_quota_error(exc):
                _QUOTA_LOCK.add((endpoint.provider_id, day))
            await SQLAlchemyAIChatRepository.bump_usage(
                db,
                provider_id=endpoint.provider_id,
                requests=1,
                failures=1,
                quota_hits=1 if _is_quota_error(exc) else 0,
                last_error=detail,
            )
            logger.warning("AI 供应商调用失败，转下一个: %s (%s)", endpoint.label, detail)
            attempts.append(
                RouteAttempt(
                    provider_id=endpoint.provider_id,
                    label=endpoint.label,
                    status="failed",
                    detail=detail,
                    latency_ms=latency_ms,
                )
            )
            continue

        latency_ms = int(result.latency_ms or (time.perf_counter() - started) * 1000)
        tokens_in, tokens_out = _token_usage(result.usage)
        await SQLAlchemyAIChatRepository.bump_usage(
            db,
            provider_id=endpoint.provider_id,
            requests=1,
            tokens=tokens_in + tokens_out,
        )
        _COOLDOWN_UNTIL.pop(endpoint.provider_id, None)
        attempts.append(
            RouteAttempt(
                provider_id=endpoint.provider_id,
                label=endpoint.label,
                status="ok",
                latency_ms=latency_ms,
            )
        )
        return RouteResult(
            ok=True,
            content=str(result.content or ""),
            model=str(result.model or endpoint.cfg.model or ""),
            provider_id=endpoint.provider_id,
            provider_name=endpoint.provider_name,
            upstream_name=endpoint.upstream_name,
            latency_ms=latency_ms,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            attempts=attempts,
        )

    quota_blocked = all(attempt.status == "quota_exhausted" for attempt in attempts) if attempts else False
    reason = "quota_exhausted" if quota_blocked else "all_failed"
    detail = "；".join(f"{attempt.label}: {attempt.detail}" for attempt in attempts if attempt.detail)[:500]
    return RouteResult(ok=False, reason=reason, detail=detail or "全部候选端点不可用", attempts=attempts)


async def providers_usage_overview(db: AsyncSession) -> dict[str, Any]:
    """供应商额度用量总览（Admin 展示用）：配置额度 + 当日已用 + 剩余。"""
    store, secrets = await ai_config_service.load_providers_snapshot(db)
    endpoints = build_endpoints(store, secrets)
    provider_ids = sorted({item.provider_id for item in endpoints})
    usage = await SQLAlchemyAIChatRepository.usage_today(db, provider_ids)

    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for endpoint in endpoints:
        if endpoint.provider_id in seen:
            continue
        seen.add(endpoint.provider_id)
        row = usage.get(endpoint.provider_id)
        requests = int(row.requests or 0) if row else 0
        tokens = int(row.tokens or 0) if row else 0
        items.append(
            {
                "provider_id": endpoint.provider_id,
                "provider_name": endpoint.provider_name,
                "priority": endpoint.priority,
                "weight": endpoint.weight,
                "daily_request_limit": endpoint.daily_request_limit,
                "daily_token_limit": endpoint.daily_token_limit,
                "requests_today": requests,
                "tokens_today": tokens,
                "failures_today": int(row.failures or 0) if row else 0,
                "quota_hits_today": int(row.quota_hits or 0) if row else 0,
                "requests_remaining": max(0, endpoint.daily_request_limit - requests)
                if endpoint.daily_request_limit > 0
                else None,
                "tokens_remaining": max(0, endpoint.daily_token_limit - tokens)
                if endpoint.daily_token_limit > 0
                else None,
                "quota_exhausted": _exhausted(endpoint, usage, business_day()),
                "cooling_down": _cooldown_active(endpoint.provider_id),
                "last_error": getattr(row, "last_error", None) if row else None,
            }
        )
    return {"usage_date": business_day(), "items": items}
