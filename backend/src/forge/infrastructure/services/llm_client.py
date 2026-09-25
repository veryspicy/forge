"""OpenAI 兼容协议的 LLM 客户端（httpx 直连，不依赖 OpenAI SDK）。

统一封装两类调用：
- ``list_models``       : ``GET  {base_url}/models``              拉取上游可用模型
- ``chat_completion``   : ``POST {base_url}/chat/completions``    对话补全
- ``test_connection``   : 可用性测试（模型列表 + 一次最小 chat 调用）

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


@dataclass
class LLMConfig:
    """LLM 连接配置。"""

    base_url: str = ""
    api_key: str = ""
    model: str = ""
    temperature: float = 0.7
    max_tokens: int = 1024
    enabled: bool = True

    def to_public_dict(self) -> dict[str, Any]:
        """不含敏感字段的公开视图。"""
        return {
            "base_url": self.base_url,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "enabled": self.enabled,
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
    """调用 ``/chat/completions``，返回首条回复内容。"""
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
    """可用性测试：先取模型列表，再发一次最小 chat 请求。

    返回 ``{status, latency_ms, detail, models_count, chat_ok, reply}``，
    status ∈ ok / fail（不做 warn，避免语义含混）。
    """
    if not cfg.base_url:
        return _fail("缺少 Base URL")
    if not cfg.api_key:
        return _fail("缺少 API Key")
    if not cfg.model:
        return _fail("缺少模型名称")

    models: list[str] = []
    try:
        models = await list_models(cfg.base_url, cfg.api_key)
    except httpx.HTTPStatusError as exc:
        return _fail(f"模型列表请求失败：HTTP {exc.response.status_code} {_error_detail(exc)}")
    except httpx.HTTPError as exc:
        return _fail(f"无法连接上游：{type(exc).__name__} {exc}")
    except ValueError as exc:
        return _fail(f"响应不是合法 JSON：{exc}")

    probe_cfg = LLMConfig(
        base_url=cfg.base_url,
        api_key=cfg.api_key,
        model=cfg.model,
        temperature=cfg.temperature,
        max_tokens=16,
    )
    try:
        result = await chat_completion(
            probe_cfg,
            [{"role": "user", "content": "Reply with the single word: pong"}],
        )
    except httpx.HTTPStatusError as exc:
        return _fail(f"对话调用失败：HTTP {exc.response.status_code} {_error_detail(exc)}")
    except httpx.HTTPError as exc:
        return _fail(f"对话调用失败：{type(exc).__name__} {exc}")
    except ValueError as exc:
        return _fail(f"对话响应不是合法 JSON：{exc}")

    return {
        "status": "ok",
        "latency_ms": result.latency_ms,
        "detail": f"模型 {cfg.model} 调用正常，上游可选模型 {len(models)} 个",
        "models_count": len(models),
        "chat_ok": bool(result.content),
        "reply": result.content.strip()[:200],
    }
