"""站点配置读取服务（业务消费方统一入口）。

店铺级配置（Trust Badges / 商品审核开关 / 订单设置 / 店铺基础信息）统一存放于
site_profiles.config（active profile），由 Admin 站点设置页（site-config）写入，
C 端 /api/v1/site-profile 与业务消费方从同一数据源读取。

存量兼容：DB 中 stored config 若缺失对应块（旧数据，站点设置尚未保存过），
按块回退读取 app_settings 中的旧值，避免配置迁移后丢失或行为突变。
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, cast

from sqlalchemy.ext.asyncio import AsyncSession

from forge.application.services.app_settings_service import (
    get_free_shipping_threshold as _legacy_free_shipping_threshold,
)
from forge.application.services.app_settings_service import get_trust_badges as _legacy_trust_badges
from forge.application.services.app_settings_service import (
    is_product_audit_enabled as _legacy_product_audit_enabled,
)
from forge.infrastructure.persistence.repositories.site_profile_repo import SQLAlchemySiteProfileRepository
from forge.infrastructure.site_defaults import merge_for_response

# orderSettings 缺失回退时的默认结构（与 site_defaults.DEFAULT_CONFIG 保持一致）
_DEFAULT_ORDER_SETTINGS: dict[str, Any] = {
    "autoReview": False,
    "maxItemsPerOrder": 10,
    "orderPrefix": "PAI",
    "expiryHours": 24,
}


async def _get_stored_config(db: AsyncSession) -> dict[str, Any]:
    """读取 active profile 的 stored config（DB 原始 JSON，未合并默认值）。"""
    profile = await SQLAlchemySiteProfileRepository.get_active(db)
    if profile is None:
        return {}
    return cast(dict[str, Any], profile.config) or {}


async def _read_block(db: AsyncSession, block: str) -> dict[str, Any] | None:
    """读取 stored config 中的指定块；未配置该块时返回 None。"""
    stored = await _get_stored_config(db)
    raw = stored.get(block)
    return raw if isinstance(raw, dict) else None


async def get_site_config(db: AsyncSession) -> dict[str, Any]:
    """返回完整站点配置（默认值兜底合并，结构安全，与 C 端 site-profile 同源）。"""
    profile = await SQLAlchemySiteProfileRepository.get_active(db)
    return merge_for_response(profile.config if profile is not None else None)  # type: ignore[arg-type]


def _to_public_trust_badges(block: dict[str, Any]) -> dict[str, Any]:
    """将站点配置 camelCase 的 trustBadges 转换为 C 端契约（snake_case，与 app_settings 旧格式一致）。

    旧 app_settings 结构为 free_shipping / returns / secure_checkout，portal-web [id].vue
    等消费方均按 snake_case 读取；站点设置存储为 freeShipping / returns / secureCheckout，
    此处做字段映射避免前端契约破坏。
    """
    free_shipping = block.get("freeShipping")
    returns = block.get("returns")
    secure_checkout = block.get("secureCheckout")
    result: dict[str, Any] = {}
    if isinstance(free_shipping, dict):
        result["free_shipping"] = free_shipping
    if isinstance(returns, dict):
        result["returns"] = returns
    if isinstance(secure_checkout, dict):
        result["secure_checkout"] = secure_checkout
    return result


async def get_trust_badges(db: AsyncSession) -> dict[str, Any]:
    """信任标识配置：优先站点配置 trustBadges；存量缺失该块时回退 app_settings。

    返回给 C 端时统一为 snake_case 契约（free_shipping / returns / secure_checkout）。
    """
    block = await _read_block(db, "trustBadges")
    if block is None:
        return await _legacy_trust_badges(db)
    return _to_public_trust_badges(block)


async def get_free_shipping_threshold(db: AsyncSession) -> Decimal | None:
    """免邮阈值：读站点配置 trustBadges.freeShipping；存量缺失时回退 app_settings。

    返回 None 表示免邮关闭；返回正数表示 subtotal 超过该阈值才免邮。
    """
    block = await _read_block(db, "trustBadges")
    if block is None:
        return await _legacy_free_shipping_threshold(db)
    try:
        free_shipping = block.get("freeShipping") or {}
        if not bool(free_shipping.get("enabled", True)):
            return None
        threshold = Decimal(str(free_shipping.get("threshold", 50)))
    except (KeyError, TypeError, ValueError):
        return Decimal("50")
    return threshold if threshold > 0 else None


async def is_product_audit_enabled(db: AsyncSession) -> bool:
    """商品审核开关：读站点配置 productAudit.enabled；存量缺失时回退 app_settings。"""
    block = await _read_block(db, "productAudit")
    if block is None:
        return await _legacy_product_audit_enabled(db)
    return bool(block.get("enabled", False))


async def get_order_settings(db: AsyncSession) -> dict[str, Any]:
    """订单设置：读站点配置 orderSettings；缺失时返回默认结构。"""
    block = await _read_block(db, "orderSettings")
    if block is None:
        return _DEFAULT_ORDER_SETTINGS
    # 兼容旧数据：defaultCurrency 已移除（与 currencies[0] 重复且无消费方）
    if isinstance(block, dict):
        block.pop("defaultCurrency", None)
    return block
