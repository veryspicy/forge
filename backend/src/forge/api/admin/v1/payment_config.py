"""Admin 支付配置 API（渠道启停 + 凭证 + 连通性测试）。

- ``GET  /api/admin/v1/payment-config``              渠道列表（含启停状态与脱敏凭证）
- ``PUT  /api/admin/v1/payment-config/channels``     整体保存启用渠道集合与顺序
- ``PUT  /api/admin/v1/payment-config/{channel}/enabled``  单渠道启停（开关）
- ``PUT  /api/admin/v1/payment-config/{channel}``    保存单渠道凭证
- ``POST /api/admin/v1/payment-config/{channel}/test``    连通性测试（不产生扣款）

配置直接写库（``app_settings.payment`` / ``system_configs.payment.channels``），
保存后运行期快照立即失效，下一次 C 端请求即生效——**不需要重新发布或重启容器**。
敏感字段以 Fernet 密文落库，接口只回 ``*_masked`` / ``*_set``。
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from forge.application.services import payment_config_service
from forge.main.dependencies import get_db
from forge.main.rbac import require_permission

logger = logging.getLogger(__name__)

router = APIRouter()


class ChannelsPayload(BaseModel):
    """整体保存启用渠道（顺序即 C 端展示顺序）。"""

    enabled_channels: list[str] = Field(default_factory=list)


class ChannelTogglePayload(BaseModel):
    """单渠道启停开关。"""

    enabled: bool


class CredentialsPayload(BaseModel):
    """渠道凭证表单；未提交/留空的字段保留原值。"""

    values: dict[str, Any] = Field(default_factory=dict)


def _actor_id(claims: dict[str, Any]) -> str | None:
    return str(claims.get("sub")) if claims.get("sub") else None


@router.get("")
async def get_payment_config(
    db: AsyncSession = Depends(get_db),
    claims: dict[str, Any] = Depends(require_permission("payment_config", "view")),
) -> dict[str, Any]:
    """返回所有可配置渠道及其启停/凭证（脱敏）状态。"""
    channels = await payment_config_service.load_channel_states(db)
    await payment_config_service.refresh(db, force=True)
    enabled = [c["channel"] for c in channels if c["enabled"]]
    return {
        "channels": channels,
        "enabled_channels": enabled,
        "note": "保存后立即生效，无需重新发布；至少保留一个启用渠道。",
    }


@router.put("/channels")
async def update_enabled_channels(
    payload: ChannelsPayload,
    db: AsyncSession = Depends(get_db),
    claims: dict[str, Any] = Depends(require_permission("payment_config", "manage")),
) -> dict[str, Any]:
    """整体保存启用渠道集合（顺序即前端按钮顺序）。"""
    saved = await payment_config_service.save_enabled_channels(
        db, payload.enabled_channels, updated_by=_actor_id(claims)
    )
    await db.commit()
    await payment_config_service.refresh(db, force=True)
    return {"enabled_channels": saved}


@router.put("/{channel}/enabled")
async def toggle_channel(
    channel: str,
    payload: ChannelTogglePayload,
    db: AsyncSession = Depends(get_db),
    claims: dict[str, Any] = Depends(require_permission("payment_config", "manage")),
) -> dict[str, Any]:
    """开关某个支付渠道（C 端按钮随之出现/消失）。"""
    saved = await payment_config_service.set_channel_enabled(
        db, channel, payload.enabled, updated_by=_actor_id(claims)
    )
    await db.commit()
    await payment_config_service.refresh(db, force=True)
    return {"channel": channel.lower(), "enabled": payload.enabled, "enabled_channels": saved}


@router.put("/{channel}")
async def update_channel_credentials(
    channel: str,
    payload: CredentialsPayload,
    db: AsyncSession = Depends(get_db),
    claims: dict[str, Any] = Depends(require_permission("payment_config", "manage")),
) -> dict[str, Any]:
    """保存渠道凭证（敏感字段加密入库，明文不回显）。"""
    await payment_config_service.save_credentials(
        db, channel, payload.values, updated_by=_actor_id(claims)
    )
    await db.commit()
    await payment_config_service.refresh(db, force=True)
    states = await payment_config_service.load_channel_states(db)
    target = next((c for c in states if c["channel"] == channel.lower()), None)
    return {"channel": channel.lower(), "config": target}


@router.post("/{channel}/test")
async def test_channel(
    channel: str,
    db: AsyncSession = Depends(get_db),
    claims: dict[str, Any] = Depends(require_permission("payment_config", "manage")),
) -> dict[str, Any]:
    """连通性测试（只读探测，不产生任何扣款）。"""
    return await payment_config_service.test_channel(db, channel)
