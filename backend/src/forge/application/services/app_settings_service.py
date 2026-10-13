"""应用级设置 KV 读写（app_settings 表）。

提供业务开关/配置的统一读写入口，供 Admin settings API 与各业务服务
（如商品审核开关 product_audit_enabled）使用。
"""

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from forge.infrastructure.persistence.models import ORMAppSetting

# 默认设置：未落库时使用的兜底值（种子仅保证 product_audit_enabled 存在）
DEFAULT_SETTINGS: dict[str, Any] = {
    "product_audit_enabled": False,
    "trust_badges": {
        "free_shipping": {"enabled": True, "threshold": 50},
        "returns": {"enabled": True, "days": 30},
        "secure_checkout": {"enabled": True},
    },
}


async def get_trust_badges(db: AsyncSession) -> dict[str, Any]:
    """读取信任标识配置（未落库或字段缺失时以默认值兜底，保证结构完整）。"""
    raw = await get_setting(db, "trust_badges", None)
    if not isinstance(raw, dict):
        return dict(DEFAULT_SETTINGS["trust_badges"])
    merged = dict(DEFAULT_SETTINGS["trust_badges"])
    for key, value in raw.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value
    return merged


async def get_free_shipping_threshold(db: AsyncSession) -> Decimal | None:
    """免邮阈值：trust_badges.free_shipping.threshold（默认 50）；enabled=False 或阈值<=0 时返回 None（免邮关闭）。"""
    tb = await get_trust_badges(db)
    try:
        fs = tb["free_shipping"]
        if not bool(fs.get("enabled", True)):
            return None
        threshold = Decimal(str(fs.get("threshold", 50)))
    except (KeyError, TypeError, ValueError):
        return Decimal("50")
    return threshold if threshold > 0 else None


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
