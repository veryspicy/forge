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

from forge.application.services.app_settings_service import DEFAULT_SETTINGS as _LEGACY_DEFAULTS
from forge.application.services.app_settings_service import (
    get_free_shipping_threshold as _legacy_free_shipping_threshold,
)
from forge.application.services.app_settings_service import get_setting as _legacy_get_setting
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


async def get_i18n_settings(db: AsyncSession) -> tuple[bool, list[str], str]:
    """站点多语言总闸、已勾选语言列表与默认语言（唯一数据源：site_profiles.config.i18n）。

    返回 ``(enabled, locales, default_locale)``：

    - ``enabled``：多语言总闸，缺省 True（兼容存量配置）；False 时站点只保留默认语言
    - ``locales``：Admin 里勾选的原始语言清单（小写去重、有序，不含默认语言兜底插入）
    - ``default_locale``：默认语言，保证被加入 ``locales`` 且位于其中
    """
    config = await get_site_config(db)
    i18n = config.get("i18n")
    block: dict[str, Any] = i18n if isinstance(i18n, dict) else {}

    enabled = bool(block.get("enabled", True))

    locales: list[str] = []
    raw = block.get("locales")
    if isinstance(raw, list):
        for item in raw:
            code = str(item).strip().lower()
            if code and code not in locales:
                locales.append(code)

    default_locale = str(block.get("defaultLocale") or "en").strip().lower() or "en"
    if not locales:
        locales = [default_locale]
    elif default_locale not in locales:
        locales.insert(0, default_locale)
    return enabled, locales, default_locale


async def get_i18n_locales(db: AsyncSession) -> tuple[list[str], str]:
    """站点**生效**语言列表与默认语言（业务消费方唯一入口）。

    总闸 ``i18n.enabled`` 关闭时只返回 ``[default_locale]``，即单语模式；
    打开时返回全部已勾选语言。业务消费方（CMS 内容 locale 校验、C 端内容接口回退链）
    统一从此派生，避免在代码里硬编码语言集合，新增语言只需在 Admin 站点设置中勾选。
    """
    enabled, locales, default_locale = await get_i18n_settings(db)
    if not enabled:
        return [default_locale], default_locale
    return locales, default_locale


def _to_public_shopping_info(block: dict[str, Any]) -> dict[str, Any]:
    """将站点配置 camelCase 的 shoppingInfo 转换为 C 端契约（snake_case，与 app_settings 旧格式一致）。

    旧 app_settings 结构为 delivery / import_fee / payment_methods，portal-web [id].vue
    等消费方均按 snake_case 读取；站点设置存储为 delivery / importFee / paymentMethods，
    此处做字段映射避免前端契约破坏。
    """
    delivery = block.get("delivery")
    import_fee = block.get("importFee")
    payment_methods = block.get("paymentMethods")
    result: dict[str, Any] = {}
    if isinstance(delivery, dict):
        mapped: dict[str, Any] = {}
        for k, v in delivery.items():
            if k == "handlingDays":
                mapped["handling_days"] = v
            elif k == "transitMinDays":
                mapped["transit_min_days"] = v
            elif k == "transitMaxDays":
                mapped["transit_max_days"] = v
            else:
                mapped[k] = v
        result["delivery"] = mapped
    if isinstance(import_fee, dict):
        result["import_fee"] = import_fee
    if isinstance(payment_methods, dict):
        result["payment_methods"] = payment_methods
    return result


# 法务信息块字段（camelCase，与 site_defaults.DEFAULT_CONFIG["legal"] 一致）
LEGAL_TEXT_FIELDS: tuple[str, ...] = (
    "companyLegalName",
    "registeredAddress",
    "privacyEmail",
    "jurisdiction",
    "lastUpdated",
    "vatId",
    "rcsNumber",
)


async def get_legal_info(db: AsyncSession) -> dict[str, Any]:
    """法务信息：公司主体名 / 注册地址 / 隐私邮箱 / 管辖法律 / 生效日期 / VAT ID / RCS 号。

    唯一数据源：site_profiles.config.legal（Admin → 站点设置 → 法务信息）。
    始终返回全部键（未配置为空字符串），供 CMS 法务占位符渲染与 C 端展示复用；
    调用方据空字符串判定“该占位符尚未配置”，不要在此处补默认文案。

    另返回可选的 ``byLocale``：``{locale: {字段: 值}}``，用于按语言覆盖全局值
    （占位符处于语法内嵌位置的字段，如德语 {{JURISDICTION}}）。空值不进入覆盖层。
    """
    block = await _read_block(db, "legal") or {}
    result: dict[str, Any] = {}
    for field in LEGAL_TEXT_FIELDS:
        raw = block.get(field)
        result[field] = "" if raw is None else str(raw).strip()

    overrides: dict[str, dict[str, str]] = {}
    raw_overrides = block.get("byLocale")
    if isinstance(raw_overrides, dict):
        for locale, values in raw_overrides.items():
            if not isinstance(values, dict):
                continue
            cleaned = {
                field: str(values.get(field) or "").strip()
                for field in LEGAL_TEXT_FIELDS
                if str(values.get(field) or "").strip()
            }
            if cleaned:
                overrides[str(locale).strip().lower()] = cleaned
    result["byLocale"] = overrides
    return result


async def get_shopping_info(db: AsyncSession) -> dict[str, Any]:
    """购物信息（运费/预计送达/进口费/付款方式）：优先站点配置 shoppingInfo；存量缺失时回退 app_settings。

    返回给 C 端时统一为 snake_case 契约（delivery / import_fee / payment_methods）。
    """
    block = await _read_block(db, "shoppingInfo")
    if block is None:
        legacy = await _legacy_get_setting(db, "shopping_info", None)
        if isinstance(legacy, dict):
            return legacy
        return dict(_LEGACY_DEFAULTS.get("shopping_info") or {})
    return _to_public_shopping_info(block)
