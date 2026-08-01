"""站点配置 — 领域模型 v2.0（纯 Python dataclasses）。

对应 site_profiles.config JSONB 的 8 个 section。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class SiteBrand:
    logo_url: str = ""
    site_name: str = "Forge Store"
    primary_color: str = "#3b82f6"
    secondary_color: str = "#10b981"


@dataclass
class SiteTheme:
    color_scheme: str = "light"
    palette: list[str] = field(default_factory=lambda: ["#3b82f6", "#10b981", "#f59e0b"])
    font_family: str = "Inter, sans-serif"
    border_radius: int = 8
    spacing_unit: int = 4


@dataclass
class SiteNavigation:
    items: list[dict] = field(default_factory=list)
    style: dict = field(default_factory=lambda: {"layout": "horizontal", "sticky": True})


@dataclass
class SiteFooter:
    copyright: str = "© 2026 Forge Store. All rights reserved."
    columns: list[dict] = field(default_factory=list)
    show_social_icons: bool = True


@dataclass
class SiteSEO:
    default_title: str = "Forge Store"
    default_description: str = ""
    og_image: str = ""


@dataclass
class SiteI18n:
    default_locale: str = "en"
    supported_locales: list[str] = field(default_factory=lambda: ["en"])
    translations: dict[str, dict[str, str]] = field(default_factory=dict)


@dataclass
class SiteFeatureFlags:
    enable_reviews: bool = True
    enable_wishlist: bool = True
    enable_guest_checkout: bool = False
    enable_ai_chat: bool = True


@dataclass
class SiteCurrencies:
    default: str = "USD"
    supported: list[str] = field(default_factory=lambda: ["USD"])
    exchange_rates: dict[str, float] = field(default_factory=lambda: {"USD": 1.0})


@dataclass
class SiteConfig:
    """站点配置聚合根"""

    brand: SiteBrand = field(default_factory=SiteBrand)
    theme: SiteTheme = field(default_factory=SiteTheme)
    navigation: SiteNavigation = field(default_factory=SiteNavigation)
    footer: SiteFooter = field(default_factory=SiteFooter)
    seo: SiteSEO = field(default_factory=SiteSEO)
    i18n: SiteI18n = field(default_factory=SiteI18n)
    feature_flags: SiteFeatureFlags = field(default_factory=SiteFeatureFlags)
    currencies: SiteCurrencies = field(default_factory=SiteCurrencies)

    @classmethod
    def from_dict(cls, data: dict | None) -> "SiteConfig":
        data = data or {}
        return cls(
            brand=SiteBrand(**{k: v for k, v in (data.get("brand") or {}).items() if k in SiteBrand.__dataclass_fields__}),
            theme=SiteTheme(**{k: v for k, v in (data.get("theme") or {}).items() if k in SiteTheme.__dataclass_fields__}),
            navigation=SiteNavigation(**{k: v for k, v in (data.get("navigation") or {}).items() if k in SiteNavigation.__dataclass_fields__}),
            footer=SiteFooter(**{k: v for k, v in (data.get("footer") or {}).items() if k in SiteFooter.__dataclass_fields__}),
            seo=SiteSEO(**{k: v for k, v in (data.get("seo") or {}).items() if k in SiteSEO.__dataclass_fields__}),
            i18n=SiteI18n(**{k: v for k, v in (data.get("i18n") or {}).items() if k in SiteI18n.__dataclass_fields__}),
            feature_flags=SiteFeatureFlags(**{k: v for k, v in (data.get("feature_flags") or {}).items() if k in SiteFeatureFlags.__dataclass_fields__}),
            currencies=SiteCurrencies(**{k: v for k, v in (data.get("currencies") or {}).items() if k in SiteCurrencies.__dataclass_fields__}),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
