"""税费引擎（A 方案：静态税率表，Admin 可配）+ B 方案适配器预留位。

设计要点
--------
- **税率表静态可配**：税率存在 ``app_settings`` key ``tax``，Admin 页面维护；
  保存后运行期快照立即失效，下一次报价/下单即生效，无需发布。
- **供应商抽象**：``TaxProvider`` 协议 + ``ProviderRegistry``。当前内置
  ``StaticTaxProvider``（本地表）；后续接 Avalara / TaxJar / Stripe Tax 时只新增
  一个 provider 并在配置里切 ``provider`` 字段，调用方（购物车 / 下单 / 发票）不变。
- **订单落快照**：下单时把 (rate, 税额, 税名, 辖区) 固化到订单，税率后续调整不影响
  历史订单与退款金额。
- **价内含税**：``prices_include_tax=true`` 时（EU/UK 常见）税额从含税价倒推，
  订单总额不变。

配置结构（``app_settings.tax``）::

    {
      "provider": "static",
      "enabled": true,
      "prices_include_tax": false,
      "default_rate": "0",
      "rates": [
        {"country": "US", "region": "CA", "category": "*",
         "rate": "0.0725", "name": "CA Sales Tax", "applies_to_shipping": false}
      ]
    }

匹配优先级：国家+州/省+类目 > 国家+州/省+* > 国家+*+类目 > 国家+*+* > default_rate。
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any, Protocol, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from forge.infrastructure.persistence.models import ORMAppSetting

logger = logging.getLogger(__name__)

TAX_SETTING_KEY = "tax"
SNAPSHOT_TTL_SECONDS = 5.0
ANY = "*"

# 默认税率表（Admin 可改；未保存过配置时生效）
# 说明：仅作开站兜底，正式经营需按实际注册辖区与商品类目（如部分美国州宠物食品免税）调整。
DEFAULT_RATES: tuple[dict[str, Any], ...] = (
    {"country": "US", "region": ANY, "category": ANY, "rate": "0", "name": "US Sales Tax",
     "applies_to_shipping": False},
    {"country": "CA", "region": ANY, "category": ANY, "rate": "0.05", "name": "GST", "applies_to_shipping": False},
    {"country": "GB", "region": ANY, "category": ANY, "rate": "0.20", "name": "VAT", "applies_to_shipping": True},
    {"country": "DE", "region": ANY, "category": ANY, "rate": "0.19", "name": "VAT", "applies_to_shipping": True},
    {"country": "FR", "region": ANY, "category": ANY, "rate": "0.20", "name": "VAT", "applies_to_shipping": True},
    {"country": "IT", "region": ANY, "category": ANY, "rate": "0.22", "name": "VAT", "applies_to_shipping": True},
    {"country": "ES", "region": ANY, "category": ANY, "rate": "0.21", "name": "VAT", "applies_to_shipping": True},
    {"country": "NL", "region": ANY, "category": ANY, "rate": "0.21", "name": "VAT", "applies_to_shipping": True},
    {"country": "AU", "region": ANY, "category": ANY, "rate": "0.10", "name": "GST", "applies_to_shipping": True},
    {"country": "JP", "region": ANY, "category": ANY, "rate": "0.10", "name": "Consumption Tax",
     "applies_to_shipping": True},
    {"country": "CN", "region": ANY, "category": ANY, "rate": "0.13", "name": "VAT", "applies_to_shipping": True},
)


def _dec(value: Any, default: str = "0") -> Decimal:
    try:
        return Decimal(str(value if value not in (None, "") else default))
    except (InvalidOperation, ValueError):
        return Decimal(default)


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class TaxRule:
    """一条税率档。"""

    country: str
    region: str = ANY
    category: str = ANY
    rate: Decimal = Decimal("0")
    name: str = "Tax"
    applies_to_shipping: bool = False

    @property
    def specificity(self) -> int:
        return (self.region != ANY) + (self.category != ANY)

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> TaxRule:
        return cls(
            country=str(row.get("country") or ANY).upper(),
            region=str(row.get("region") or ANY) or ANY,
            category=str(row.get("category") or ANY) or ANY,
            rate=_dec(row.get("rate")),
            name=str(row.get("name") or "Tax"),
            applies_to_shipping=bool(row.get("applies_to_shipping")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "country": self.country,
            "region": self.region,
            "category": self.category,
            "rate": str(self.rate),
            "name": self.name,
            "applies_to_shipping": self.applies_to_shipping,
        }


@dataclass(frozen=True)
class TaxResult:
    """一次计税结果（可直接落订单快照）。"""

    tax_amount: Decimal = Decimal("0")
    rate: Decimal = Decimal("0")
    name: str = "Tax"
    jurisdiction: str = ""
    taxable_amount: Decimal = Decimal("0")
    inclusive: bool = False
    provider: str = "static"

    @property
    def label(self) -> str:
        """C 端展示名，如 ``VAT (DE) 19%``。"""
        pct_text = format((self.rate * 100).normalize(), "f")
        if "." in pct_text:
            pct_text = pct_text.rstrip("0").rstrip(".")
        if not self.jurisdiction:
            return self.name
        return f"{self.name} ({self.jurisdiction}) {pct_text}%".strip()


class TaxProvider(Protocol):
    """B 方案（第三方税务 API）实现该协议即可无缝替换。"""

    name: str

    async def calculate(
        self,
        db: AsyncSession,
        *,
        country: str | None,
        region: str | None,
        lines: list[tuple[str | None, Decimal]],
        shipping: Decimal,
    ) -> TaxResult:  # pragma: no cover - protocol
        ...


# --------------------------------------------------------------------------- #
# 运行期快照
# --------------------------------------------------------------------------- #


@dataclass
class _TaxConfig:
    enabled: bool = True
    prices_include_tax: bool = False
    default_rate: Decimal = Decimal("0")
    provider: str = "static"
    rates: list[TaxRule] = field(default_factory=list)
    loaded_at: float = 0.0


_CONFIG: _TaxConfig = _TaxConfig(rates=[TaxRule.from_dict(r) for r in DEFAULT_RATES])


def invalidate() -> None:
    """配置写入后使快照立即失效。"""
    _CONFIG.loaded_at = 0.0


def _from_dict(value: dict[str, Any]) -> _TaxConfig:
    raw_rates = value.get("rates")
    rates = (
        [TaxRule.from_dict(r) for r in raw_rates if isinstance(r, dict)]
        if isinstance(raw_rates, list)
        else [TaxRule.from_dict(r) for r in DEFAULT_RATES]
    )
    return _TaxConfig(
        enabled=bool(value.get("enabled", True)),
        prices_include_tax=bool(value.get("prices_include_tax", False)),
        default_rate=_dec(value.get("default_rate")),
        provider=str(value.get("provider") or "static").lower(),
        rates=rates,
        loaded_at=time.monotonic(),
    )


async def _load_row(db: AsyncSession) -> dict[str, Any] | None:
    row = (
        await db.execute(select(ORMAppSetting).where(ORMAppSetting.key == TAX_SETTING_KEY))
    ).scalar_one_or_none()
    value = row.value if row is not None else None
    return dict(value) if isinstance(value, dict) else None


async def refresh(db: AsyncSession, *, force: bool = False) -> None:
    """从 DB 重建税率快照（TTL 内跳过）。"""
    global _CONFIG
    if not force and _CONFIG.loaded_at > 0 and (time.monotonic() - _CONFIG.loaded_at) < SNAPSHOT_TTL_SECONDS:
        return
    try:
        value = await _load_row(db)
    except Exception:  # noqa: BLE001 - 配置读取失败不应打断下单
        logger.exception("tax config refresh failed; keeping previous snapshot")
        return
    if value is None:
        _CONFIG = _TaxConfig(rates=[TaxRule.from_dict(r) for r in DEFAULT_RATES], loaded_at=time.monotonic())
        return
    _CONFIG = _from_dict(value)


def current_config() -> dict[str, Any]:
    """当前生效配置（Admin 页面回显用）。"""
    return {
        "provider": _CONFIG.provider,
        "enabled": _CONFIG.enabled,
        "prices_include_tax": _CONFIG.prices_include_tax,
        "default_rate": str(_CONFIG.default_rate),
        "rates": [r.to_dict() for r in _CONFIG.rates],
    }


def available_providers() -> list[dict[str, Any]]:
    """可选计税 provider（B 方案接第三方后在此追加）。"""
    return [
        {
            "value": "static",
            "label": "静态税率表（本地）",
            "description": "按国家/州省/类目配置税率，无需外部依赖；适合起步与预扣税模式。",
            "available": True,
        },
        {
            "value": "external",
            "label": "第三方税务引擎（预留）",
            "description": "对接 Avalara / TaxJar / Stripe Tax，按交易地址实时计算；尚未接入。",
            "available": False,
        },
    ]


# --------------------------------------------------------------------------- #
# 计税
# --------------------------------------------------------------------------- #


def _match(rates: list[TaxRule], country: str, region: str, category: str) -> TaxRule | None:
    candidates = [r for r in rates if r.country in (country, ANY)]
    best: TaxRule | None = None
    for rule in candidates:
        if rule.region not in (region, ANY):
            continue
        if rule.category not in (category, ANY):
            continue
        if best is None or rule.specificity > best.specificity:
            best = rule
    return best


class StaticTaxProvider:
    """静态税率表实现。"""

    name = "static"

    async def calculate(
        self,
        db: AsyncSession,
        *,
        country: str | None,
        region: str | None,
        lines: list[tuple[str | None, Decimal]],
        shipping: Decimal,
    ) -> TaxResult:
        await refresh(db)
        if not _CONFIG.enabled:
            return TaxResult(provider=self.name)
        iso = (country or "").upper()
        region_code = (region or "").upper() or ANY

        taxable = Decimal("0")
        tax_total = Decimal("0")
        names: list[str] = []
        max_rate = Decimal("0")
        for category, amount in lines:
            rule = _match(_CONFIG.rates, iso, region_code, (category or ANY).lower() or ANY)
            rate = rule.rate if rule is not None else _CONFIG.default_rate
            if rule is not None and rule.name not in names:
                names.append(rule.name)
            taxable += amount
            max_rate = max(max_rate, rate)
            tax_total += amount * rate
        # 运费是否计税：取命中的第一条规则（无规则时按默认不计税）
        shipping_rule = _match(_CONFIG.rates, iso, region_code, ANY)
        if shipping and shipping_rule is not None and shipping_rule.applies_to_shipping:
            taxable += shipping
            tax_total += shipping * shipping_rule.rate
            max_rate = max(max_rate, shipping_rule.rate)

        if _CONFIG.prices_include_tax and max_rate > 0:
            gross = taxable
            net = gross / (Decimal("1") + max_rate)
            tax_total = _money(gross - net)
            taxable = _money(net)
        else:
            tax_total = _money(tax_total)
            taxable = _money(taxable)

        return TaxResult(
            tax_amount=tax_total,
            rate=max_rate,
            name=names[0] if names else ("Tax" if tax_total else "Tax"),
            jurisdiction=iso + (f"-{region_code}" if region_code != ANY else ""),
            taxable_amount=taxable,
            inclusive=_CONFIG.prices_include_tax,
            provider=self.name,
        )


_PROVIDERS: dict[str, TaxProvider] = {"static": StaticTaxProvider()}


def register_provider(provider: TaxProvider) -> None:
    """注册 B 方案 provider（如第三方税务 API 适配器）。"""
    _PROVIDERS[provider.name] = provider


def get_tax_provider() -> TaxProvider:
    """按当前配置返回生效 provider；未实现的配置回退静态表。"""
    provider = _PROVIDERS.get(_CONFIG.provider)
    if provider is None:
        if _CONFIG.provider != "static":
            logger.warning("tax provider '%s' not registered; falling back to static", _CONFIG.provider)
        return _PROVIDERS["static"]
    return provider


async def calculate_tax(
    db: AsyncSession,
    *,
    country: str | None,
    region: str | None,
    lines: list[tuple[str | None, Decimal]],
    shipping: Decimal = Decimal("0"),
) -> TaxResult:
    """统一计税入口（购物车报价与下单共用）。"""
    return await get_tax_provider().calculate(
        db, country=country, region=region, lines=lines, shipping=shipping
    )


async def save_config(db: AsyncSession, values: dict[str, Any], updated_by: str | None = None) -> dict[str, Any]:
    """保存税率配置（Admin）。"""
    from forge.api.errors import APIError, ErrorCode

    provider = str(values.get("provider") or "static").lower()
    if provider not in {p["value"] for p in available_providers()}:
        raise APIError(ErrorCode.VALIDATION_ERROR, message=f"Unknown tax provider: {provider}")
    raw_rates = values.get("rates")
    if raw_rates is not None and not isinstance(raw_rates, list):
        raise APIError(ErrorCode.VALIDATION_ERROR, message="rates must be a list")
    rates: list[dict[str, Any]] = []
    for row in raw_rates or []:
        if not isinstance(row, dict):
            raise APIError(ErrorCode.VALIDATION_ERROR, message="each rate must be an object")
        country = str(row.get("country") or "").strip().upper()
        if not country:
            raise APIError(ErrorCode.VALIDATION_ERROR, message="rate.country is required")
        rate = _dec(row.get("rate"), "-1")
        if rate < 0 or rate >= 1:
            raise APIError(
                ErrorCode.VALIDATION_ERROR,
                message=f"rate for {country} must be a decimal between 0 and 1 (e.g. 0.19)",
            )
        rates.append(
            TaxRule(
                country=country,
                region=str(row.get("region") or ANY).strip().upper() or ANY,
                category=str(row.get("category") or ANY).strip().lower() or ANY,
                rate=rate,
                name=str(row.get("name") or "Tax").strip(),
                applies_to_shipping=bool(row.get("applies_to_shipping")),
            ).to_dict()
        )
    default_rate = _dec(values.get("default_rate"))
    if default_rate < 0 or default_rate >= 1:
        raise APIError(
            ErrorCode.VALIDATION_ERROR,
            message="default_rate must be a decimal between 0 and 1 (e.g. 0.19)",
        )
    payload = {
        "provider": provider,
        "enabled": bool(values.get("enabled", True)),
        "prices_include_tax": bool(values.get("prices_include_tax", False)),
        "default_rate": str(default_rate),
        "rates": rates,
    }
    row = (
        await db.execute(select(ORMAppSetting).where(ORMAppSetting.key == TAX_SETTING_KEY))
    ).scalar_one_or_none()
    if row is None:
        db.add(ORMAppSetting(key=TAX_SETTING_KEY, value=payload, updated_by=updated_by))
    else:
        row.value = cast(Any, payload)
        row.updated_by = cast(Any, updated_by)
    invalidate()
    return payload


def env_tax_enabled() -> bool:
    """环境变量总闸（应急关闭计税，回退为 0）。"""
    return (os.getenv("FORGE_TAX_ENABLED", "1") or "1").lower() not in {"0", "false", "off"}
