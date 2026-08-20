"""AI Probe — 探测 AI 服务、LLM 配置与数据库连通性。

探测项：
- ai_service : AI 微服务 HTTP 健康（GET {ai_service_url}/health）
- llm_key    : OPENAI_API_KEY 是否已配置（非 placeholder）
- database   : 主数据库异步连接测试
"""

import logging
import time
from typing import Any

import httpx
from fastapi import APIRouter
from sqlalchemy import text

from forge.main.config import settings
from forge.main.dependencies import get_db

logger = logging.getLogger(__name__)

router = APIRouter()

AI_SERVICE_TIMEOUT = 5.0


@router.get("/probe")
async def ai_probe() -> dict[str, Any]:
    probes = [
        await _probe_ai_service(),
        _probe_llm_key(),
        await _probe_database(),
    ]
    overall = "ok"
    for p in probes:
        if p["status"] == "fail":
            overall = "fail"
            break
        if p["status"] == "warn":
            overall = "warn"
    return {"overall": overall, "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "items": probes}


async def _probe_ai_service() -> dict[str, Any]:
    url = f"{settings.ai_service_url}/health"
    start = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=AI_SERVICE_TIMEOUT) as client:
            resp = await client.get(url)
            latency_ms = int((time.perf_counter() - start) * 1000)
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "key": "ai_service",
                    "name": "AI Service",
                    "status": "ok",
                    "latency_ms": latency_ms,
                    "detail": data.get("status", "ok"),
                }
            return {
                "key": "ai_service",
                "name": "AI Service",
                "status": "fail",
                "latency_ms": latency_ms,
                "detail": f"HTTP {resp.status_code}",
            }
    except httpx.HTTPError as exc:
        latency_ms = int((time.perf_counter() - start) * 1000)
        return {
            "key": "ai_service",
            "name": "AI Service",
            "status": "fail",
            "latency_ms": latency_ms,
            "detail": f"unreachable: {type(exc).__name__}",
        }


def _probe_llm_key() -> dict[str, Any]:
    key = settings.openai_api_key
    if not key:
        return {"key": "llm_key", "name": "LLM API Key", "status": "fail", "latency_ms": 0, "detail": "not configured"}
    if key == "sk-placeholder":
        return {
            "key": "llm_key",
            "name": "LLM API Key",
            "status": "warn",
            "latency_ms": 0,
            "detail": "placeholder key (OPENAI_API_KEY not set)",
        }
    masked = key[:6] + "..." + key[-4:] if len(key) > 12 else "***"
    return {
        "key": "llm_key",
        "name": "LLM API Key",
        "status": "ok",
        "latency_ms": 0,
        "detail": f"configured ({masked})",
    }


async def _probe_database() -> dict[str, Any]:
    start = time.perf_counter()
    try:
        # 复用依赖中的 async engine，避免重复建连
        async for session in get_db():
            await session.execute(text("SELECT 1"))
        latency_ms = int((time.perf_counter() - start) * 1000)
        return {
            "key": "database",
            "name": "Database",
            "status": "ok",
            "latency_ms": latency_ms,
            "detail": "SELECT 1 ok",
        }
    except Exception as exc:  # noqa: BLE001
        latency_ms = int((time.perf_counter() - start) * 1000)
        return {
            "key": "database",
            "name": "Database",
            "status": "fail",
            "latency_ms": latency_ms,
            "detail": f"error: {type(exc).__name__}",
        }
