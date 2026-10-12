"""应用级设置 KV 读写（app_settings 表）。

提供业务开关/配置的统一读写入口，供 Admin settings API 与各业务服务
（如商品审核开关 product_audit_enabled）使用。
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from forge.infrastructure.persistence.models import ORMAppSetting

# 默认设置：未落库时使用的兜底值（种子仅保证 product_audit_enabled 存在）
DEFAULT_SETTINGS: dict[str, Any] = {
    "product_audit_enabled": False,
}


async def get_all_settings(db: AsyncSession) -> dict[str, Any]:
    """返回全量设置（默认值兜底 + 已持久化值覆盖）。"""
    rows = (await db.execute(select(ORMAppSetting))).scalars().all()
    merged = dict(DEFAULT_SETTINGS)
    for row in rows:
        merged[row.key] = row.value  # type: ignore[index]  # plugin 将 key 推断为 Column[str]，运行时为 str
    return merged


async def get_setting(db: AsyncSession, key: str, default: Any = None) -> Any:
    """读取单个设置，未配置时返回 default。"""
    row = (await db.execute(select(ORMAppSetting).where(ORMAppSetting.key == key))).scalar_one_or_none()
    return row.value if row is not None else default


async def set_setting(
    db: AsyncSession,
    key: str,
    value: Any,
    updated_by: str | None = None,
) -> ORMAppSetting:
    """写入单个设置（存在则更新，不存在则插入）。"""
    row = (await db.execute(select(ORMAppSetting).where(ORMAppSetting.key == key))).scalar_one_or_none()
    if row is None:
        row = ORMAppSetting(key=key, value=value, updated_by=updated_by)
        db.add(row)
    else:
        row.value = value
        row.updated_by = updated_by  # type: ignore[assignment]  # plugin 将 updated_by 推断为 Column[str]，实际 nullable
    return row


async def is_product_audit_enabled(db: AsyncSession) -> bool:
    """商品审核开关：默认关闭（对齐单商家自营主流平台）。"""
    return bool(await get_setting(db, "product_audit_enabled", False))
