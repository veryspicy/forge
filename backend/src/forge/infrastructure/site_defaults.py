"""Shared default site profile config & helpers.

Both Admin (/api/admin/v1/site/config) and Public (/api/v1/site-profile)
endpoints MUST use the same defaults so C-end and Admin Editor see exactly
the same structure from the same DB row.

Key principle (backward-compatible with existing stored profile.config):
  * DEFAULT_CONFIG keys are ALWAYS camelCase (matches existing stored data).
  * Legacy aliases (snake_case / nav / diy_page_slug) are normalised ON WRITE
    via :func:`merge_for_save` so we never double-store conflicting keys.
  * :func:`merge_for_response` fills in any missing keys for clients.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def deep_merge(base: dict[str, object], override: dict[str, object]) -> dict[str, object]:
    """Recursively merge ``override`` into ``base`` (mutation-free)."""
    result = deepcopy(base)
    for key, value in (override or {}).items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)  # type: ignore[arg-type]
        else:
            result[key] = deepcopy(value)
    return result


# ---------------------------------------------------------------------------
# Canonical defaults (camelCase throughout, matching frontends + stored data)
# ---------------------------------------------------------------------------
DEFAULT_CONFIG: dict[str, Any] = {
    "brand": {
        "name": "Forge",
        "tagline": "",
        "nameColor": "auto",
        "logo": {"type": "text", "data": ""},
    },
    "theme": {
        "preset": "forge",
        "primaryColor": "#18a058",
        "primaryLight": "#36ad6a",
        "primaryDark": "#0c7a43",
        "secondaryColor": "#f0a020",
        "accentColor": "#2080f0",
        "fontHeading": "Inter",
        "fontBody": "Inter",
    },
    "navigation": [
        {"key": "home", "to": "/", "labelKey": "nav.home", "label": "首页", "visible": True, "order": 0},
        {
            "key": "products",
            "to": "/products",
            "labelKey": "nav.products",
            "label": "商品",
            "visible": True,
            "order": 1,
        },
        {"key": "pets", "to": "/pets", "labelKey": "nav.pets", "label": "我的宠物", "visible": True, "order": 2},
        {"key": "orders", "to": "/orders", "labelKey": "nav.orders", "label": "订单", "visible": True, "order": 3},
        {"key": "chat", "to": "/chat", "labelKey": "nav.chat", "label": "AI客服", "visible": True, "order": 4},
    ],
    "categories": [
        {
            "slug": "cat-food",
            "nameKey": "footer.petFood",
            "name": "宠物食品",
            "icon": "🍖",
            "image": "",
            "visible": True,
            "order": 0,
        },
        {
            "slug": "toys",
            "nameKey": "footer.toys",
            "name": "玩具",
            "icon": "🎾",
            "image": "",
            "visible": True,
            "order": 1,
        },
        {
            "slug": "health-wellness",
            "nameKey": "footer.healthWellness",
            "name": "健康护理",
            "icon": "💊",
            "image": "",
            "visible": True,
            "order": 2,
        },
        {
            "slug": "accessories",
            "nameKey": "footer.accessories",
            "name": "配件",
            "icon": "🎀",
            "image": "",
            "visible": True,
            "order": 3,
        },
    ],
    "footer": {
        "copyright": "© 2026 Forge. 版权所有。",
        "newsletter": True,
        "social": [
            {"platform": "facebook", "enabled": False, "url": ""},
            {"platform": "x", "enabled": False, "url": ""},
            {"platform": "instagram", "enabled": False, "url": ""},
            {"platform": "youtube", "enabled": False, "url": ""},
            {"platform": "tiktok", "enabled": False, "url": ""},
            {"platform": "linkedin", "enabled": False, "url": ""},
        ],
        "columns": ["shop", "support", "about", "legal"],
        "linkGroups": [
            {
                "key": "shop",
                "titleKey": "footer.shop",
                "title": "购物",
                "visible": True,
                "order": 0,
                "links": [
                    {
                        "labelKey": "footer.petFood",
                        "label": "宠物食品",
                        "to": "/products?category=pet-food",
                        "visible": True,
                    },
                    {"labelKey": "footer.toys", "label": "玩具", "to": "/products?category=toys", "visible": True},
                    {
                        "labelKey": "footer.healthWellness",
                        "label": "健康护理",
                        "to": "/products?category=health-wellness",
                        "visible": True,
                    },
                    {
                        "labelKey": "footer.accessories",
                        "label": "配件",
                        "to": "/products?category=accessories",
                        "visible": True,
                    },
                ],
            },
            {
                "key": "support",
                "titleKey": "footer.support",
                "title": "帮助",
                "visible": True,
                "order": 1,
                "links": [
                    {"labelKey": "footer.faqs", "label": "常见问题", "to": "/faqs", "visible": True},
                    {"labelKey": "footer.shippingInfo", "label": "配送说明", "to": "/shipping", "visible": True},
                    {"labelKey": "footer.returns", "label": "退换政策", "to": "/returns", "visible": True},
                    {"labelKey": "footer.contactUs", "label": "联系我们", "to": "/contact", "visible": True},
                ],
            },
            {
                "key": "about",
                "titleKey": "footer.about",
                "title": "关于",
                "visible": True,
                "order": 2,
                "links": [
                    {"labelKey": "footer.ourStory", "label": "我们的故事", "to": "/story", "visible": True},
                    {
                        "labelKey": "footer.sustainability",
                        "label": "可持续发展",
                        "to": "/sustainability",
                        "visible": True,
                    },
                    {"labelKey": "footer.blog", "label": "博客", "to": "/blog", "visible": True},
                    {"labelKey": "footer.careers", "label": "加入我们", "to": "/careers", "visible": True},
                ],
            },
            {
                "key": "legal",
                "titleKey": "footer.legal",
                "title": "法律",
                "visible": True,
                "order": 3,
                "links": [
                    {"labelKey": "footer.privacyPolicy", "label": "隐私政策", "to": "/privacy", "visible": True},
                    {"labelKey": "footer.termsOfService", "label": "服务条款", "to": "/terms", "visible": True},
                    {"labelKey": "footer.cookies", "label": "Cookie政策", "to": "/cookies", "visible": True},
                ],
            },
        ],
    },
    "seo": {
        "titleTemplate": "%s | Forge",
        "homeTitle": "Forge - 专业宠物用品商店",
        "description": "",
        "metaKeywords": "",
        "metaDescription": "",
    },
    "i18n": {
        "defaultLocale": "en",
        "locales": ["en", "zh", "ar", "de", "fr"],
        "translations": {
            "en": {},
            "zh": {},
            "ar": {},
            "de": {},
            "fr": {},
        },
    },
    "featureFlags": {
        "show_pets_page": True,
        "show_ai_chat": True,
        "show_categories_section": True,
        "show_featured_products": True,
        "show_tailored_pets": True,
        "show_ai_teaser": True,
        "show_newsletter": True,
        "enable_reviews": True,
        "enable_wishlist": False,
        "enable_live_chat": True,
        "liveChat": True,
        "reviews": True,
        "wishlist": False,
        "cookie_prefix": "forge",
    },
    "products": {
        "default_sort": "default",
    },
    "currencies": ["USD"],
    "regions": [],
    "sections": [
        {"type": "hero", "visible": True, "order": 0, "config": {}},
        {"type": "categories", "visible": True, "order": 1, "config": {}},
        {"type": "featured_products", "visible": True, "order": 2, "config": {}},
        {"type": "ai_teaser", "visible": True, "order": 3, "config": {}},
    ],
    "homeHero": {
        "useCarousel": False,
        "hero": {
            "titleKey": "hero.title",
            "title": "Smart Shopping for Your Pet",
            "subtitleKey": "hero.subtitle",
            "subtitle": "AI-powered product recommendations tailored to your pet's breed, age, and health needs.",
            "cta1LabelKey": "hero.cta1Label",
            "cta1Label": "Shop Now",
            "cta1To": "/products",
            "cta2LabelKey": "hero.cta2Label",
            "cta2Label": "Add Your Pet",
            "cta2To": "/pets",
            "backgroundImage": "",
        },
        "carousel": {"images": [], "autoplay": True, "interval": 4000},
    },
    "diyPageSlug": "",
}


def _normalize_aliases(payload: dict[str, object]) -> dict[str, object]:
    """Rewrite known legacy aliases into canonical camelCase keys (in-place).

    Only touches keys that exist; always returns the *same* dict reference
    so callers can chain.
    """
    if not isinstance(payload, dict):
        return payload

    # feature_flags (snake) -> featureFlags (camel)
    if "feature_flags" in payload:
        if "featureFlags" not in payload:
            payload["featureFlags"] = payload.pop("feature_flags")
        else:
            # Merge snake into camel (camel wins conflicts) then drop snake
            payload["featureFlags"] = {**payload.pop("feature_flags"), **payload["featureFlags"]}  # type: ignore[dict-item]
    # features (old alias from early forms) -> featureFlags
    if "features" in payload:
        flags = payload.pop("features") or {}
        existing = payload.setdefault("featureFlags", {}) or {}
        payload["featureFlags"] = {**existing, **flags}  # type: ignore[dict-item]

    # nav (short) -> navigation (canonical)
    if "nav" in payload and "navigation" not in payload:
        payload["navigation"] = payload.pop("nav")

    # diy_page_slug (snake) -> diyPageSlug (camel)
    if "diy_page_slug" in payload and "diyPageSlug" not in payload:
        payload["diyPageSlug"] = payload.pop("diy_page_slug")

    # Ensure each nav entry has order/visible defaults (list index becomes order)
    nav = payload.get("navigation")
    if isinstance(nav, list):
        for i, item in enumerate(nav):
            if isinstance(item, dict):
                item.setdefault("order", i)
                item.setdefault("visible", True)
                item.setdefault("labelKey", f"nav.{item.get('key', '')}")
                item.setdefault("to", "/")

    # footer linkGroups: ensure order/visible defaults on group + inner links
    footer = payload.get("footer") or {}
    if isinstance(footer, dict):
        groups = footer.get("linkGroups")
        if isinstance(groups, list):
            for gi, g in enumerate(groups):
                if isinstance(g, dict):
                    g.setdefault("order", gi)
                    g.setdefault("visible", True)
                    g.setdefault("titleKey", f"footer.{g.get('key', '')}")
                    links = g.get("links")
                    if isinstance(links, list):
                        for li, link in enumerate(links):
                            if isinstance(link, dict):
                                link.setdefault("order", li)
                                link.setdefault("visible", True)
                                link.setdefault("labelKey", "footer.link")
                                link.setdefault("to", "/")
        footer.setdefault("copyright", DEFAULT_CONFIG["footer"]["copyright"])
        footer.setdefault("newsletter", True)
        footer.setdefault("columns", list(DEFAULT_CONFIG["footer"]["columns"]))

    # homeHero.hero legacy i18n keys: home.* -> hero.* (canonical)
    home_hero = payload.get("homeHero") or {}
    hero_cfg = home_hero.get("hero")  # type: ignore[attr-defined]
    if isinstance(hero_cfg, dict):
        hero_legacy_key_map = {
            "home.heroTitle": "hero.title",
            "home.heroDesc": "hero.subtitle",
            "home.shopNow": "hero.cta1Label",
            "home.addPet": "hero.cta2Label",
        }
        for f in ("titleKey", "subtitleKey", "cta1LabelKey", "cta2LabelKey"):
            v = hero_cfg.get(f)
            if isinstance(v, str) and v:
                v = v.strip()
                if v in hero_legacy_key_map:
                    hero_cfg[f] = hero_legacy_key_map[v]
                elif v.startswith("home.") and not v.startswith("hero."):
                    hero_cfg[f] = f"hero.{v[len('home.') :]}"

    return payload


def merge_for_save(user_payload_config: dict[str, object]) -> dict[str, object]:
    """Given Admin PUT payload.config, produce final dict to persist in DB.

    1. Normalise legacy aliases (snake_case -> camelCase)
    2. Deep-merge into canonical DEFAULT_CONFIG
    3. Return final camelCase dict to store as profile.config JSONB
    """
    normalized = _normalize_aliases(dict(user_payload_config or {}))
    return deep_merge(DEFAULT_CONFIG, normalized)


def merge_for_response(stored_config: dict[str, object] | None) -> dict[str, object]:
    """Given raw DB JSON (profile.config), produce frontend-safe response.

    Guarantees every canonical key exists with a sensible default.
    """
    merged = deep_merge(DEFAULT_CONFIG, stored_config or {})
    return _normalize_aliases(merged)
