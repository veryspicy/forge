"""Seed Site Profiles for Forge — pet_supplies + industrial_supplies."""

import asyncio
import os
import sys

os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:postgres@localhost:5432/forge"
sys.path.insert(0, r"D:\codeRepo\forge\backend\src")

from forge.main.application import app
from forge.infrastructure.persistence.database import async_session_factory
from forge.infrastructure.persistence.models import ORMSiteProfile

PET_SUPPLIES_CONFIG = {
    "brand": {
        "name": "Forge",
        "tagline": "Smart Shopping for Your Pet",
        "logo": {
            "type": "svg",
            "data": """<svg width="28" height="28" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M14 18c-2.5 0-4.5-1.5-5.5-3.5-0.5-1-0.3-2 0.5-2.5 1-0.5 2.5 0 3 1 0.3 0.5 1 1 2 1s1.7-0.5 2-1c0.5-1 2-1.5 3-1 0.8 0.5 1 1.5 0.5 2.5C18.5 16.5 16.5 18 14 18z" fill="url(#pawGradient)"/>
  <ellipse cx="10" cy="11" rx="2.5" ry="3" transform="rotate(-20 10 11)" fill="url(#pawGradient)"/>
  <ellipse cx="18" cy="11" rx="2.5" ry="3" transform="rotate(20 18 11)" fill="url(#pawGradient)"/>
  <ellipse cx="7" cy="14" rx="2" ry="2.5" transform="rotate(-35 7 14)" fill="url(#pawGradient)"/>
  <ellipse cx="21" cy="14" rx="2" ry="2.5" transform="rotate(35 21 14)" fill="url(#pawGradient)"/>
  <defs><linearGradient id="pawGradient" x1="0" y1="0" x2="28" y2="28"><stop stop-color="var(--color-primary-500)"/><stop offset="1" stop-color="var(--color-secondary-400)"/></linearGradient></defs>
</svg>""",
        },
    },
    "theme": {
        "primaryColor": "#4f46e5",
        "primaryLight": "#818cf8",
        "primaryDark": "#3730a3",
        "secondaryColor": "#ec4899",
        "accentColor": "#f97316",
        "fontHeading": "Inter",
        "fontBody": "Inter",
    },
    "navigation": [
        {"key": "products", "to": "/products", "labelKey": "nav.products", "visible": True},
        {"key": "pets", "to": "/pets", "labelKey": "nav.myPets", "visible": True},
        {"key": "orders", "to": "/orders", "labelKey": "nav.orders", "visible": True},
        {"key": "chat", "to": "/chat", "labelKey": "nav.aiChat", "visible": True},
    ],
    "sections": [
        {
            "type": "hero",
            "visible": True,
            "config": {
                "titleKey": "home.heroTitle",
                "descKey": "home.heroDesc",
                "primaryButton": {"labelKey": "home.shopNow", "to": "/products"},
                "secondaryButton": {"labelKey": "home.addPet", "to": "/pets"},
            },
        },
        {"type": "tailored_pets", "visible": True, "config": {}},
        {"type": "categories", "visible": True, "config": {}},
        {"type": "featured_products", "visible": True, "config": {}},
        {
            "type": "ai_teaser",
            "visible": True,
            "config": {
                "titleKey": "home.aiTeaser",
                "descKey": "home.aiTeaserDesc",
                "button": {"labelKey": "home.startChat", "to": "/chat"},
            },
        },
    ],
    "categories": [
        {"slug": "food", "nameKey": "categories.food", "icon": "🍖"},
        {"slug": "toys", "nameKey": "categories.toys", "icon": "🎾"},
        {"slug": "health", "nameKey": "categories.health", "icon": "💊"},
        {"slug": "accessories", "nameKey": "categories.accessories", "icon": "🎀"},
        {"slug": "grooming", "nameKey": "categories.grooming", "icon": "✂️"},
        {"slug": "training", "nameKey": "categories.training", "icon": "🦮"},
        {"slug": "furniture", "nameKey": "categories.furniture", "icon": "🛏️"},
        {"slug": "litter", "nameKey": "categories.litter", "icon": "🧹"},
    ],
    "footer": {
        "newsletter": True,
        "columns": ["shop", "support", "about", "legal"],
    },
    "seo": {
        "titleTemplate": "%s | Forge Pet Supplies",
        "description": "AI-Powered Pet Supplies Store — personalized recommendations for food, toys, accessories.",
    },
    "feature_flags": {
        "show_pets_page": True,
        "show_ai_chat": True,
        "show_blog": False,
        "cookie_prefix": "forge_pet",
    },
    "regions": ["na", "eu"],
    "currencies": ["USD", "EUR", "GBP", "CNY"],
    "i18n": {
        "defaultLocale": "en",
        "locales": ["en", "zh", "ar", "de", "fr"],
    },
}

INDUSTRIAL_SUPPLIES_CONFIG = {
    "brand": {
        "name": "Forge Industrial",
        "tagline": "Professional Equipment & Supplies",
        "logo": {
            "type": "svg",
            "data": """<svg width="28" height="28" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect x="2" y="7" width="24" height="14" rx="2" fill="url(#gearGradient)"/>
  <circle cx="14" cy="14" r="3.5" fill="#fff"/>
  <defs><linearGradient id="gearGradient" x1="0" y1="0" x2="28" y2="28"><stop stop-color="var(--color-primary-500)"/><stop offset="1" stop-color="#1e293b"/></linearGradient></defs>
</svg>""",
        },
    },
    "theme": {
        "primaryColor": "#1e293b",
        "primaryLight": "#475569",
        "primaryDark": "#0f172a",
        "secondaryColor": "#f59e0b",
        "accentColor": "#ef4444",
        "fontHeading": "Inter",
        "fontBody": "Inter",
    },
    "navigation": [
        {"key": "products", "to": "/products", "labelKey": "nav.products", "visible": True},
        {"key": "suppliers", "to": "/suppliers", "labelKey": "nav.suppliers", "visible": True},
        {"key": "orders", "to": "/orders", "labelKey": "nav.orders", "visible": True},
        {"key": "quote", "to": "/quote", "labelKey": "nav.requestQuote", "visible": True},
    ],
    "sections": [
        {
            "type": "hero",
            "visible": True,
            "config": {
                "titleKey": "home.heroTitle",
                "descKey": "home.heroDesc",
                "primaryButton": {"labelKey": "home.browseCatalog", "to": "/products"},
                "secondaryButton": {"labelKey": "home.requestQuote", "to": "/quote"},
            },
        },
        {"type": "categories", "visible": True, "config": {}},
        {"type": "featured_products", "visible": True, "config": {}},
        {"type": "supplier_showcase", "visible": True, "config": {}},
    ],
    "categories": [
        {"slug": "power-tools", "nameKey": "categories.powerTools", "icon": "🔧"},
        {"slug": "safety", "nameKey": "categories.safety", "icon": "🪖"},
        {"slug": "fasteners", "nameKey": "categories.fasteners", "icon": "🔩"},
        {"slug": "hydraulics", "nameKey": "categories.hydraulics", "icon": "⚙️"},
        {"slug": "bearings", "nameKey": "categories.bearings", "icon": "🛞"},
        {"slug": "materials", "nameKey": "categories.materials", "icon": "🧱"},
    ],
    "footer": {
        "newsletter": False,
        "columns": ["shop", "support", "about", "legal"],
    },
    "seo": {
        "titleTemplate": "%s | Forge Industrial",
        "description": "Professional-grade industrial equipment, tools, and supplies for manufacturing.",
    },
    "feature_flags": {
        "show_pets_page": False,
        "show_ai_chat": False,
        "show_bulk_order": True,
        "show_supplier_portal": True,
        "cookie_prefix": "forge_industrial",
    },
    "regions": ["na", "eu", "me"],
    "currencies": ["USD", "EUR", "CNY"],
    "i18n": {
        "defaultLocale": "en",
        "locales": ["en", "zh", "de", "fr"],
    },
}


async def main():
    async with async_session_factory() as session:
        from sqlalchemy import select, func

        # Check if profiles already exist
        result = await session.execute(
            select(func.count()).select_from(ORMSiteProfile)
        )
        count = result.scalar()
        if count > 0:
            print(f"SKIP: {count} profiles already exist. Delete them first to re-seed.")
            return

        pet = ORMSiteProfile(
            name="pet_supplies",
            label="Pet Supplies",
            config=PET_SUPPLIES_CONFIG,
            is_active=True,
        )
        industrial = ORMSiteProfile(
            name="industrial_supplies",
            label="Industrial Supplies",
            config=INDUSTRIAL_SUPPLIES_CONFIG,
            is_active=False,
        )
        session.add_all([pet, industrial])
        await session.commit()
        print("OK: 2 profiles seeded — pet_supplies (active) + industrial_supplies")


if __name__ == "__main__":
    asyncio.run(main())
