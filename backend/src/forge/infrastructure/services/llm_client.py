"""OpenAI 兼容协议的 LLM 客户端（httpx 直连，不依赖 OpenAI SDK）。

统一封装：
- ``list_models``      : ``GET  {base_url}/models``             拉取上游可用模型
- ``chat_completion``  : 按 ``cfg.protocol`` 分发：
  - chat      → ``POST {base_url}/chat/completions``（Chat Completions）
  - responses → ``POST {base_url}/responses``（OpenAI Responses）
- ``test_connection``  : 单端点可用性测试（模型列表 + 一次最小对话，发送 ``hi``）
- ``test_endpoints``   : 多端点按序测试（聚合供应商）
- ``chat_completion_with_failover`` : 多端点按序调用，首个成功即返回（聚合故障转移）

兼容 NVIDIA integrate API（https://integrate.api.nvidia.com/v1）、DeepSeek、OpenAI 等
任意 OpenAI 协议上游。
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)

PROBE_TIMEOUT = 20.0
CHAT_TIMEOUT = 60.0

PROTOCOL_CHAT = "chat"
PROTOCOL_RESPONSES = "responses"

PROBE_MESSAGE = "hi"


class LLMFailoverError(RuntimeError):
    """所有端点均调用失败。"""


@dataclass
class LLMConfig:
    """LLM 连接配置。"""

    base_url: str = ""
    api_key: str = ""
    model: str = ""
    temperature: float = 0.7
    max_tokens: int = 1024
    enabled: bool = True
    protocol: str = PROTOCOL_CHAT

    def to_public_dict(self) -> dict[str, Any]:
        """不含敏感字段的公开视图。"""
        return {
            "base_url": self.base_url,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "enabled": self.enabled,
            "protocol": self.protocol,
        }


@dataclass
class LLMResult:
    """一次对话调用的结果。"""

    content: str
    model: str
    latency_ms: int
    usage: dict[str, Any] = field(default_factory=dict)


def normalize_base_url(base_url: str) -> str:
    """去掉尾部斜杠，统一 ``https://host/v1`` 形态。"""
    return (base_url or "").strip().rstrip("/")


def _headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _error_detail(exc: httpx.HTTPStatusError) -> str:
    """从上游错误响应中提取尽可能可读的说明（截断 300 字）。"""
    try:
        body = exc.response.json()
    except ValueError:
        body = None
    detail = ""
    if isinstance(body, dict):
        err = body.get("error")
        if isinstance(err, dict):
            detail = str(err.get("message") or err)
        elif err:
            detail = str(err)
        detail = detail or str(body.get("detail") or body.get("message") or "")
    if not detail:
        detail = (exc.response.text or "")[:300]
    return detail.strip()[:300]


async def list_models(base_url: str, api_key: str, timeout: float = PROBE_TIMEOUT) -> list[str]:
    """拉取上游可用模型 ID 列表。"""
    url = f"{normalize_base_url(base_url)}/models"
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.get(url, headers=_headers(api_key))
        resp.raise_for_status()
        data = resp.json()
    items = data.get("data") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return []
    models = [str(item["id"]) for item in items if isinstance(item, dict) and item.get("id")]
    return sorted(set(models))


async def chat_completion(
    cfg: LLMConfig,
    messages: list[dict[str, str]],
    timeout: float = CHAT_TIMEOUT,
) -> LLMResult:
    """按 ``cfg.protocol`` 分发到对应协议实现，返回首条回复内容。"""
    if cfg.protocol == PROTOCOL_RESPONSES:
        return await responses_completion(cfg, messages, timeout)
    return await chat_completions(cfg, messages, timeout)


async def chat_completions(
    cfg: LLMConfig,
    messages: list[dict[str, str]],
    timeout: float = CHAT_TIMEOUT,
) -> LLMResult:
    """调用 ``/chat/completions``（Chat Completions 协议）。"""
    url = f"{normalize_base_url(cfg.base_url)}/chat/completions"
    payload: dict[str, Any] = {
        "model": cfg.model,
        "messages": messages,
        "temperature": cfg.temperature,
        "max_tokens": cfg.max_tokens,
    }
    start = time.perf_counter()
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, headers=_headers(cfg.api_key), json=payload)
        resp.raise_for_status()
        data = resp.json()
    latency_ms = int((time.perf_counter() - start) * 1000)

    content = ""
    choices = data.get("choices") if isinstance(data, dict) else None
    if isinstance(choices, list) and choices:
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        if isinstance(message, dict):
            content = str(message.get("content") or "")
    usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
    return LLMResult(content=content, model=str(data.get("model") or cfg.model), latency_ms=latency_ms, usage=usage)


async def responses_completion(
    cfg: LLMConfig,
    messages: list[dict[str, str]],
    timeout: float = CHAT_TIMEOUT,
) -> LLMResult:
    """调用 ``/responses``（OpenAI Responses 协议）。"""
    url = f"{normalize_base_url(cfg.base_url)}/responses"
    payload: dict[str, Any] = {
        "model": cfg.model,
        "input": [{"role": str(m.get("role") or "user"), "content": str(m.get("content") or "")} for m in messages],
        "temperature": cfg.temperature,
        "max_output_tokens": cfg.max_tokens,
    }
    start = time.perf_counter()
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, headers=_headers(cfg.api_key), json=payload)
        resp.raise_for_status()
        data = resp.json()
    latency_ms = int((time.perf_counter() - start) * 1000)
    usage: dict[str, Any] = {}
    raw_usage = data.get("usage") if isinstance(data, dict) else None
    if isinstance(raw_usage, dict):
        usage = {str(key): value for key, value in raw_usage.items()}
    model = str(data.get("model") or cfg.model) if isinstance(data, dict) else cfg.model
    return LLMResult(content=_extract_responses_text(data), model=model, latency_ms=latency_ms, usage=usage)


def _extract_responses_text(data: Any) -> str:
    """从 Responses 响应中提取文本（兼容 ``output_text`` 与 ``output[].content[].text``）。"""
    if not isinstance(data, dict):
        return ""
    direct = data.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct
    parts: list[str] = []
    for item in data.get("output") or []:
        if not isinstance(item, dict):
            continue
        for block in item.get("content") or []:
            if isinstance(block, dict) and isinstance(block.get("text"), str):
                parts.append(block["text"])
    return "".join(parts)


def _fail(detail: str, latency_ms: int = 0) -> dict[str, Any]:
    return {
        "status": "fail",
        "latency_ms": latency_ms,
        "detail": detail,
        "models_count": 0,
        "chat_ok": False,
        "reply": "",
    }


async def test_connection(cfg: LLMConfig) -> dict[str, Any]:
    """单端点可用性测试：先取模型列表，再发一次最小对话（发送 ``hi``）。

    返回 ``{status, latency_ms, detail, models_count, chat_ok, reply}``，
    status ∈ ok / fail（不做 warn，避免语义含混）。未指定模型时用上游首个模型探测。
    """
    if not cfg.base_url:
        return _fail("缺少 Base URL")
    if not cfg.api_key:
        return _fail("缺少 API Key")

    models: list[str] = []
    try:
        models = await list_models(cfg.base_url, cfg.api_key)
    except httpx.HTTPStatusError as exc:
        return _fail(f"模型列表请求失败：HTTP {exc.response.status_code} {_error_detail(exc)}")
    except httpx.HTTPError as exc:
        return _fail(f"无法连接上游：{type(exc).__name__} {exc}")
    except ValueError as exc:
        return _fail(f"响应不是合法 JSON：{exc}")

    probe_model = cfg.model or (models[0] if models else "")
    if not probe_model:
        return _fail("上游未返回可用模型，请手动填写模型名称")

    probe_cfg = LLMConfig(
        base_url=cfg.base_url,
        api_key=cfg.api_key,
        model=probe_model,
        temperature=cfg.temperature,
        max_tokens=16,
        protocol=cfg.protocol,
    )
    try:
        result = await chat_completion(probe_cfg, [{"role": "user", "content": PROBE_MESSAGE}])
    except httpx.HTTPStatusError as exc:
        return _fail(f"对话调用失败：HTTP {exc.response.status_code} {_error_detail(exc)}")
    except httpx.HTTPError as exc:
        return _fail(f"对话调用失败：{type(exc).__name__} {exc}")
    except ValueError as exc:
        return _fail(f"对话响应不是合法 JSON：{exc}")

    return {
        "status": "ok",
        "latency_ms": result.latency_ms,
        "detail": f"模型 {probe_model} 调用正常，上游可选模型 {len(models)} 个",
        "models_count": len(models),
        "chat_ok": bool(result.content),
        "reply": result.content.strip()[:200],
    }


async def test_endpoints(cfgs: list[LLMConfig], labels: list[str] | None = None) -> dict[str, Any]:
    """多端点按序测试（聚合供应商）；任一成功即 ``status="ok"``，并附带各端点明细。"""
    if not cfgs:
        return {**_fail("没有可测试的上游端点"), "endpoints": []}

    names = list(labels or [])
    results: list[dict[str, Any]] = []
    for index, cfg in enumerate(cfgs):
        label = names[index] if index < len(names) else f"端点 {index + 1}"
        results.append({"label": label, **await test_connection(cfg)})

    succeeded = next((item for item in results if item["status"] == "ok"), None)
    chosen = succeeded or results[0]
    detail = str(chosen["detail"])
    if len(results) > 1:
        summary = "、".join(f"{item['label']} {'正常' if item['status'] == 'ok' else '失败'}" for item in results)
        detail = f"{summary}；{detail}"

    return {
        "status": chosen["status"],
        "latency_ms": chosen["latency_ms"],
        "detail": detail[:500],
        "models_count": chosen["models_count"],
        "chat_ok": chosen["chat_ok"],
        "reply": chosen["reply"],
        "endpoints": results,
    }


async def chat_completion_with_failover(
    cfgs: list[LLMConfig],
    messages: list[dict[str, str]],
    timeout: float = CHAT_TIMEOUT,
) -> LLMResult:
    """按序调用多个端点，返回首个成功结果；全部失败抛 ``LLMFailoverError``。"""
    if not cfgs:
        raise LLMFailoverError("没有可用的 LLM 端点")

    errors: list[str] = []
    for cfg in cfgs:
        try:
            return await chat_completion(cfg, messages, timeout)
        except httpx.HTTPStatusError as exc:
            errors.append(f"{cfg.base_url} HTTP {exc.response.status_code} {_error_detail(exc)}")
        except httpx.HTTPError as exc:
            errors.append(f"{cfg.base_url} {type(exc).__name__}: {exc}")
        except ValueError as exc:
            errors.append(f"{cfg.base_url} 响应解析失败：{exc}")

    raise LLMFailoverError("；".join(errors)[:500])
