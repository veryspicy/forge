"""Admin AI（LLM）配置 API。

- ``GET  /api/admin/v1/ai-config/config``  读取当前配置（API Key 仅返回脱敏串）
- ``PUT  /api/admin/v1/ai-config/config``  保存配置（api_key 留空 = 保留原密钥）
- ``POST /api/admin/v1/ai-config/test``    可用性测试（模型列表 + 一次最小对话调用）
- ``POST /api/admin/v1/ai-config/models``  拉取上游可选模型列表（供模型选择下拉）

配置持久化在 ``system_configs`` 表的 ``ai.llm`` 键，API Key 密文落库。
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from forge.application.services.ai_config_service import (
    get_ai_config_row,
    load_llm_config,
    save_llm_config,
    to_admin_view,
)
from forge.infrastructure.services.llm_client import LLMConfig, list_models, test_connection
from forge.main.dependencies import get_db
from forge.main.rbac import require_permission

logger = logging.getLogger(__name__)

router = APIRouter()


class AIConfigPayload(BaseModel):
    """AI 配置写入 / 测试载荷；None 字段表示「不覆盖已保存值」。"""

    base_url: str | None = None
    api_key: str | None = None
    model: str | None = None
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1, le=65536)
    enabled: bool | None = None

    def merged_with(self, base: LLMConfig) -> LLMConfig:
        """表单当前值覆盖已保存配置；api_key 为空则沿用已保存密钥。"""
        return LLMConfig(
            base_url=(self.base_url or base.base_url).strip(),
            api_key=(self.api_key or "").strip() or base.api_key,
            model=(self.model or base.model).strip(),
            temperature=base.temperature if self.temperature is None else float(self.temperature),
            max_tokens=base.max_tokens if self.max_tokens is None else int(self.max_tokens),
            enabled=base.enabled if self.enabled is None else bool(self.enabled),
        )


async def _resolve_config(db: AsyncSession, payload: AIConfigPayload | None) -> LLMConfig:
    """测试 / 拉模型时解析实际使用的配置：优先请求体覆盖值，其余取已保存值。"""
    base = await load_llm_config(db)
    if payload is None:
        return base
    return payload.merged_with(base)


@router.get("/config")
async def get_ai_config(
    admin: dict[str, Any] = Depends(require_permission("ai_config", "view")),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict[str, Any]:
    """读取当前 AI 配置（密钥脱敏）。"""
    row = await get_ai_config_row(db)
    cfg = await load_llm_config(db)
    return {"data": to_admin_view(cfg, row)}


@router.put("/config")
async def update_ai_config(
    payload: AIConfigPayload,
    admin: dict[str, Any] = Depends(require_permission("ai_config", "manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict[str, Any]:
    """保存 AI 配置。"""
    updated_by = str(admin.get("email") or admin.get("sub") or "") or None
    try:
        data = await save_llm_config(db, payload.model_dump(), updated_by)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return {"data": data}


@router.post("/test")
async def test_ai_config(
    payload: AIConfigPayload | None = Body(default=None),
    admin: dict[str, Any] = Depends(require_permission("ai_config", "view")),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict[str, Any]:
    """可用性测试：拉取模型列表并发起一次最小对话调用。"""
    cfg = await _resolve_config(db, payload)
    result = await test_connection(cfg)
    return {"data": result}


@router.post("/models")
async def fetch_ai_models(
    payload: AIConfigPayload | None = Body(default=None),
    admin: dict[str, Any] = Depends(require_permission("ai_config", "view")),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict[str, Any]:
    """拉取上游可选模型列表（GET {base_url}/models）。"""
    cfg = await _resolve_config(db, payload)
    if not cfg.base_url:
        raise HTTPException(status_code=400, detail="缺少 Base URL")
    if not cfg.api_key:
        raise HTTPException(status_code=400, detail="缺少 API Key")
    try:
        models = await list_models(cfg.base_url, cfg.api_key)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"上游返回 HTTP {exc.response.status_code}",
        ) from None
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"无法连接上游：{type(exc).__name__}") from None
    except ValueError:
        raise HTTPException(status_code=502, detail="上游响应不是合法 JSON") from None
    return {"data": {"models": models, "count": len(models)}}
