"""AI（LLM）配置服务。

配置存放于 ``system_configs`` 表的 ``ai.llm`` 键：
- ``value``        : base_url / model / temperature / max_tokens / enabled
- ``secret_value`` : API Key 的 Fernet 密文（落库即加密，读取时解密）

DB 无记录时回退到环境变量默认值（``AI_LLM_*``），保证首装可用。
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from forge.infrastructure.persistence.models import ORMSystemConfig
from forge.infrastructure.services.crypto_service import decrypt_str, encrypt_str, mask_secret
from forge.infrastructure.services.llm_client import LLMConfig
from forge.main.config import settings

logger = logging.getLogger(__name__)

AI_CONFIG_KEY = "ai.llm"


async def get_ai_config_row(db: AsyncSession) -> ORMSystemConfig | None:
    """读取 AI 配置行（不存在返回 None）。"""
    result = await db.execute(select(ORMSystemConfig).where(ORMSystemConfig.key == AI_CONFIG_KEY))
    return result.scalar_one_or_none()


def _env_fallback() -> LLMConfig:
    """环境变量回退配置。"""
    api_key = settings.ai_llm_api_key.strip()
    if not api_key and settings.openai_api_key and settings.openai_api_key != "sk-placeholder":
        api_key = settings.openai_api_key
    return LLMConfig(
        base_url=settings.ai_llm_base_url,
        api_key=api_key,
        model=settings.ai_llm_model,
        temperature=settings.ai_llm_temperature,
        max_tokens=settings.ai_llm_max_tokens,
        enabled=bool(api_key),
    )


async def load_llm_config(db: AsyncSession) -> LLMConfig:
    """读取当前生效的 LLM 配置（DB 优先，缺失字段回退环境变量）。"""
    row = await get_ai_config_row(db)
    if row is None:
        return _env_fallback()

    value: dict[str, Any] = dict(row.value or {})
    return LLMConfig(
        base_url=str(value.get("base_url") or settings.ai_llm_base_url),
        api_key=decrypt_str(row.secret_value),  # type: ignore[arg-type]
        model=str(value.get("model") or settings.ai_llm_model),
        temperature=float(value.get("temperature", settings.ai_llm_temperature)),
        max_tokens=int(value.get("max_tokens", settings.ai_llm_max_tokens)),
        enabled=bool(value.get("enabled", True)),
    )


def to_admin_view(cfg: LLMConfig, row: ORMSystemConfig | None) -> dict[str, Any]:
    """后台展示视图：密钥仅返回脱敏串与「是否已配置」标记，绝不回显明文。"""
    return {
        "base_url": cfg.base_url,
        "model": cfg.model,
        "temperature": cfg.temperature,
        "max_tokens": cfg.max_tokens,
        "enabled": cfg.enabled,
        "api_key_masked": mask_secret(cfg.api_key),
        "api_key_set": bool(cfg.api_key),
        "updated_at": row.updated_at.isoformat() if row is not None and row.updated_at else None,
        "updated_by": row.updated_by if row is not None else None,
    }


async def save_llm_config(
    db: AsyncSession,
    payload: dict[str, Any],
    updated_by: str | None = None,
) -> dict[str, Any]:
    """保存 LLM 配置。

    ``payload["api_key"]`` 为空 / None 表示「保留原密钥」，避免前端脱敏串覆盖真实密钥。
    """
    row = await get_ai_config_row(db)
    existing: dict[str, Any] = dict(row.value or {}) if row is not None else {}

    base_url = str(payload.get("base_url") or existing.get("base_url") or settings.ai_llm_base_url).strip()
    model = str(payload.get("model") or existing.get("model") or settings.ai_llm_model).strip()
    temperature = float(payload.get("temperature", existing.get("temperature", settings.ai_llm_temperature)))
    max_tokens = int(payload.get("max_tokens", existing.get("max_tokens", settings.ai_llm_max_tokens)))
    enabled = bool(payload.get("enabled", existing.get("enabled", True)))

    if base_url and not base_url.startswith(("http://", "https://")):
        raise ValueError("Base URL 必须以 http:// 或 https:// 开头")

    new_key = payload.get("api_key")
    if new_key is None or not str(new_key).strip():
        secret_value: str | None = row.secret_value if row is not None else None  # type: ignore[assignment]  # 保留原密钥
    else:
        secret_value = encrypt_str(str(new_key).strip())

    value = {
        "base_url": base_url,
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "enabled": enabled,
    }

    if row is None:
        row = ORMSystemConfig(
            key=AI_CONFIG_KEY,
            value=value,
            secret_value=secret_value,
            is_secret=bool(secret_value),
            updated_by=updated_by,
        )
        db.add(row)
    else:
        row.value = value  # type: ignore[assignment]  # 整体替换，避免 JSONB 原地变更不被追踪
        row.secret_value = secret_value  # type: ignore[assignment]
        row.is_secret = bool(secret_value)  # type: ignore[assignment]
        row.updated_by = updated_by  # type: ignore[assignment]
        row.updated_at = datetime.utcnow()  # type: ignore[assignment]
    await db.commit()
    await db.refresh(row)

    saved = LLMConfig(
        base_url=base_url,
        api_key=decrypt_str(row.secret_value),  # type: ignore[arg-type]
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        enabled=enabled,
    )
    return to_admin_view(saved, row)
