"""Seed RBAC + Site Profile data into the database.

Creates:
- 1 super admin user (admin@forge.dev / admin123)
- 4 roles (super_admin, admin, operator, support)
- 15 permissions
- Role-permission mappings
- Admin-role mapping for super_admin
- Casbin policies synced from role-permission mappings
- 1 default Site Profile (activated)

Usage: python seed_admin.py
  (run inside the backend container after init_db creates tables)
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from forge.infrastructure.persistence.database import async_session_factory, init_db
from forge.infrastructure.persistence.models import (
    ORMAdminUser,
    ORMAdminUserRole,
    ORMRole,
    ORMPermission,
    ORMRolePermission,
    ORMSiteProfile,
)
from forge.infrastructure.casbin_enforcer import create_enforcer, sync_role_permissions_to_casbin


import json

# ============================================================
# Config
# ============================================================

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@forge.dev")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
ADMIN_NAME = os.getenv("ADMIN_NAME", "Super Admin")

PERMISSIONS: dict[str, tuple[str, str]] = {
    # products (细粒度: view / create / edit)
    "products:view":     ("商品查看", "products"),
    "products:create":   ("商品新增", "products"),
    "products:edit":     ("商品编辑", "products"),
    # orders (细粒度: view / review / procure / refund)
    "orders:view":       ("订单查看", "orders"),
    "orders:review":     ("订单审核", "orders"),
    "orders:procure":    ("订单采购", "orders"),
    "orders:refund":     ("订单退款", "orders"),
    # pricing
    "pricing:manage":    ("定价管理", "pricing"),
    # shipments
    "shipments:manage":  ("物流管理", "shipments"),
    # suppliers
    "suppliers:manage":  ("供应商管理", "suppliers"),
    # users (细粒度: view / manage)
    "users:view":        ("用户查看", "users"),
    "users:manage":      ("用户管理", "users"),
    # settings
    "settings:manage":   ("设置管理", "settings"),
    # dashboard
    "dashboard:view":    ("仪表盘", "dashboard"),
    # chat / AI probe
    "chat:manage":       ("AI 探针", "chat"),
}

ROLES: list[tuple[str, str, str, bool]] = [
    ("super_admin", "超级管理员", "拥有全部权限", True),
    ("admin", "管理员", "日常运营管理（全部模块）", True),
    ("operator", "运营", "商品/订单/定价操作 + 仪表盘", True),
    ("support", "客服", "订单/仪表盘 + AI 探针", True),
]

DEFAULT_SITE_CONFIG = {
    "brand": {
        "name": "Forge",
        "tagline": "Smart Shopping for Your Pet",
        "logo": {"type": "svg", "data": ""},
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
        "columns": ["shop", "support", "about", "legal"],
        "newsletter": True,
    },
    "seo": {
        "titleTemplate": "%s | Forge Pet Supplies",
        "description": "AI-Powered Pet Supplies Store — personalized recommendations for food, toys, accessories.",
    },
    "i18n": {
        "defaultLocale": "en",
        "locales": ["en", "zh", "ar", "de", "fr"],
    },
    "feature_flags": {
        "show_pets_page": True,
        "show_ai_chat": True,
        "show_blog": False,
        "cookie_prefix": "forge_pet",
    },
    "currencies": ["USD", "EUR", "GBP", "CNY"],
    "regions": ["na", "eu"],
}

ROLE_PERMISSIONS_MAP: dict[str, list[str]] = {
    "super_admin": [
        "products:view", "products:create", "products:edit",
        "orders:view", "orders:review", "orders:procure", "orders:refund",
        "pricing:manage", "shipments:manage", "suppliers:manage",
        "users:view", "users:manage",
        "settings:manage", "dashboard:view", "chat:manage",
    ],
    "admin": [
        "products:view", "products:create", "products:edit",
        "orders:view", "orders:review", "orders:procure", "orders:refund",
        "pricing:manage", "shipments:manage", "suppliers:manage",
        "users:view", "users:manage",
        "settings:manage", "dashboard:view",
    ],
    "operator": [
        "products:view", "products:create", "products:edit",
        "orders:view", "orders:review", "orders:procure",
        "pricing:manage", "shipments:manage",
        "dashboard:view",
    ],
    "support": [
        "orders:view", "dashboard:view", "chat:manage",
    ],
}


# ============================================================
# Seed
# ============================================================

async def seed():
    print("[seed] Ensuring tables exist ...")
    await init_db()

    async with async_session_factory() as session:
        await _upsert_permissions(session)
        await _upsert_roles(session)
        await _upsert_role_permissions(session)
        await _upsert_super_admin(session)
        await _upsert_site_profile(session)
        await session.commit()

        print("[seed] Syncing Casbin policies ...")
        enforcer = await asyncio.to_thread(create_enforcer)
        for role_name, perm_codes in ROLE_PERMISSIONS_MAP.items():
            perms = [(c.split(":", 1)[0], c.split(":", 1)[1]) for c in perm_codes]
            sync_role_permissions_to_casbin(enforcer, role_name, perms)
        enforcer.add_role_for_user(ADMIN_EMAIL, "super_admin")
        enforcer.save_policy()
        print("[seed] Casbin policies synced.")

    print(f"\n[OK] Seed complete!")
    print(f"     Admin: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
    print(f"     Roles: {', '.join(r[0] for r in ROLES)}")
    print(f"     Permissions: {len(PERMISSIONS)}")


async def _upsert_permissions(session):
    for code, (display_name, module) in PERMISSIONS.items():
        r = await session.execute(select(ORMPermission).where(ORMPermission.code == code))
        if r.scalar_one_or_none() is None:
            session.add(ORMPermission(code=code, display_name=display_name, module=module))
    await session.flush()
    print(f"[seed] Permissions: {len(PERMISSIONS)} ready.")


async def _upsert_roles(session):
    for name, display_name, desc, is_sys in ROLES:
        r = await session.execute(select(ORMRole).where(ORMRole.name == name))
        if r.scalar_one_or_none() is None:
            session.add(ORMRole(name=name, display_name=display_name, description=desc, is_system=is_sys))
    await session.flush()
    print(f"[seed] Roles: {len(ROLES)} ready.")


async def _upsert_role_permissions(session):
    r = await session.execute(select(ORMRole))
    role_map = {x.name: x for x in r.scalars().all()}
    r = await session.execute(select(ORMPermission))
    perm_map = {x.code: x for x in r.scalars().all()}
    r = await session.execute(select(ORMRolePermission))
    existing = {(str(x.role_id), str(x.permission_id)) for x in r.scalars().all()}

    added = 0
    for role_name, codes in ROLE_PERMISSIONS_MAP.items():
        role = role_map.get(role_name)
        if not role:
            continue
        for code in codes:
            perm = perm_map.get(code)
            if not perm:
                continue
            if (str(role.id), str(perm.id)) not in existing:
                session.add(ORMRolePermission(role_id=role.id, permission_id=perm.id))
                added += 1
    await session.flush()
    print(f"[seed] Role-permission mappings: {added} new.")


async def _upsert_super_admin(session):
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    ph = pwd_context.hash(ADMIN_PASSWORD)

    r = await session.execute(
        select(ORMAdminUser).where(ORMAdminUser.email == ADMIN_EMAIL).options(selectinload(ORMAdminUser.roles))
    )
    user = r.scalar_one_or_none()
    if user is None:
        user = ORMAdminUser(email=ADMIN_EMAIL, password_hash=ph, display_name=ADMIN_NAME, is_active=True)
        session.add(user)
        await session.flush()
        print(f"[seed] Created admin user: {ADMIN_EMAIL}")
    else:
        user.password_hash = ph
        user.display_name = ADMIN_NAME
        user.is_active = True
        await session.flush()
        print(f"[seed] Updated admin user: {ADMIN_EMAIL}")

    r = await session.execute(select(ORMRole).where(ORMRole.name == "super_admin"))
    sa_role = r.scalar_one_or_none()
    if sa_role is None:
        return user

    r = await session.execute(
        select(ORMAdminUserRole).where(
            ORMAdminUserRole.admin_user_id == user.id,
            ORMAdminUserRole.role_id == sa_role.id,
        )
    )
    if r.scalar_one_or_none() is None:
        session.add(ORMAdminUserRole(admin_user_id=user.id, role_id=sa_role.id))
        await session.flush()
        print(f"[seed] Assigned role 'super_admin' to {ADMIN_EMAIL}")
    return user


async def _upsert_site_profile(session):
    """Create default SiteProfile if none exists."""
    r = await session.execute(select(ORMSiteProfile).limit(1))
    if r.scalar_one_or_none() is not None:
        print("[seed] SiteProfile already exists, skipping.")
        return

    profile = ORMSiteProfile(
        name="Default",
        config=DEFAULT_SITE_CONFIG,
        is_active=True,
    )
    session.add(profile)
    await session.flush()
    print("[seed] Default SiteProfile created.")


if __name__ == "__main__":
    asyncio.run(seed())
