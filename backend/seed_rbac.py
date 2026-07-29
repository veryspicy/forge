"""Seed RBAC data: roles, permissions, default admin user, and Casbin policies.

Usage: python seed_rbac.py
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import casbin
from casbin_sqlalchemy_adapter import Adapter
from sqlalchemy import select
from passlib.context import CryptContext

from forge.infrastructure.persistence.database import async_session_factory, engine, DATABASE_URL
from forge.infrastructure.persistence.models import (
    ORMAdminUser,
    ORMRole,
    ORMPermission,
    ORMRolePermission,
    ORMAdminUserRole,
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# =============================================================================
# Preset Data
# =============================================================================

PERMISSIONS = [
    {"code": "products:view", "display_name": "查看商品", "module": "products"},
    {"code": "products:create", "display_name": "新建商品", "module": "products"},
    {"code": "products:edit", "display_name": "编辑商品", "module": "products"},
    {"code": "products:delete", "display_name": "删除商品", "module": "products"},
    {"code": "orders:view", "display_name": "查看订单", "module": "orders"},
    {"code": "orders:review", "display_name": "审核订单", "module": "orders"},
    {"code": "orders:procure", "display_name": "推送采购", "module": "orders"},
    {"code": "orders:refund", "display_name": "处理退款", "module": "orders"},
    {"code": "shipments:view", "display_name": "查看物流", "module": "shipments"},
    {"code": "shipments:manage", "display_name": "管理物流", "module": "shipments"},
    {"code": "pricing:view", "display_name": "查看定价", "module": "pricing"},
    {"code": "pricing:manage", "display_name": "配置定价", "module": "pricing"},
    {"code": "suppliers:view", "display_name": "查看供应商", "module": "suppliers"},
    {"code": "suppliers:manage", "display_name": "管理供应商", "module": "suppliers"},
    {"code": "ai_probe:view", "display_name": "查看 AI 探针", "module": "ai_probe"},
    {"code": "settings:manage", "display_name": "系统设置", "module": "settings"},
    {"code": "users:view", "display_name": "查看用户", "module": "users"},
    {"code": "users:manage", "display_name": "管理用户", "module": "users"},
    {"code": "roles:view", "display_name": "查看角色", "module": "roles"},
    {"code": "roles:manage", "display_name": "管理角色", "module": "roles"},
]

ROLES = [
    {
        "name": "super_admin",
        "display_name": "超级管理员",
        "description": "拥有所有权限",
        "is_system": True,
        "permissions": [p["code"] for p in PERMISSIONS],
    },
    {
        "name": "admin",
        "display_name": "管理员",
        "description": "日常运营管理",
        "is_system": True,
        "permissions": [p["code"] for p in PERMISSIONS if p["code"] not in (
            "roles:view", "roles:manage", "users:manage", "settings:manage"
        )],
    },
    {
        "name": "operator",
        "display_name": "运营专员",
        "description": "商品/订单/物流/定价管理",
        "is_system": True,
        "permissions": [
            "products:view", "products:create", "products:edit",
            "orders:view", "orders:review", "orders:procure",
            "shipments:view", "shipments:manage",
            "pricing:view", "pricing:manage",
        ],
    },
    {
        "name": "support",
        "display_name": "客服人员",
        "description": "查看商品订单、处理退款、查看 AI 探针",
        "is_system": True,
        "permissions": [
            "products:view",
            "orders:view", "orders:refund",
            "shipments:view",
            "ai_probe:view",
        ],
    },
]


def _sync_db_url() -> str:
    return DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")


async def seed_rbac():
    sync_url = _sync_db_url()

    async with async_session_factory() as session:
        # Step 1: Create tables
        async with engine.begin() as conn:
            await conn.run_sync(ORMAdminUser.metadata.create_all)

        # Step 2: Seed permissions
        print("[SEED] Creating permissions...")
        perm_map: dict[str, ORMPermission] = {}
        for pdata in PERMISSIONS:
            row = (await session.execute(
                select(ORMPermission).where(ORMPermission.code == pdata["code"])
            )).scalar_one_or_none()
            if row is None:
                row = ORMPermission(**pdata)
                session.add(row)
                await session.flush()
            perm_map[pdata["code"]] = row
        print(f"[SEED]   {len(PERMISSIONS)} permissions ready")

        # Step 3: Seed roles & associations
        print("[SEED] Creating roles...")
        role_map: dict[str, ORMRole] = {}
        for rdata in ROLES:
            perm_codes = rdata["permissions"]
            row = (await session.execute(
                select(ORMRole).where(ORMRole.name == rdata["name"])
            )).scalar_one_or_none()
            if row is None:
                row = ORMRole(
                    name=rdata["name"],
                    display_name=rdata["display_name"],
                    description=rdata["description"],
                    is_system=rdata["is_system"],
                )
                session.add(row)
                await session.flush()
            role_map[rdata["name"]] = row

            for code in perm_codes:
                perm = perm_map.get(code)
                if perm is None:
                    continue
                assoc = (await session.execute(
                    select(ORMRolePermission).where(
                        ORMRolePermission.role_id == row.id,
                        ORMRolePermission.permission_id == perm.id,
                    )
                )).scalar_one_or_none()
                if assoc is None:
                    session.add(ORMRolePermission(role_id=row.id, permission_id=perm.id))
        print(f"[SEED]   {len(ROLES)} roles ready")

        # Step 4: Sync Casbin policies (p rules: role -> resource + action)
        print("[SEED] Syncing Casbin policies...")
        adapter = Adapter(sync_url)
        enforcer = casbin.Enforcer(
            str(Path(__file__).resolve().parent / "casbin_model.conf"),
            adapter,
        )
        enforcer.clear_policy()

        for rdata in ROLES:
            role_name = rdata["name"]
            for code in rdata["permissions"]:
                parts = code.split(":", 1)
                if len(parts) == 2:
                    enforcer.add_policy(role_name, parts[0], parts[1])

        enforcer.save_policy()

        # Step 5: Create default admin user
        print("[SEED] Creating default admin user...")
        email = os.getenv("ADMIN_EMAIL", "admin@forge.com")
        password = os.getenv("ADMIN_PASSWORD", "admin123")

        user = (await session.execute(
            select(ORMAdminUser).where(ORMAdminUser.email == email)
        )).scalar_one_or_none()

        if user is None:
            user = ORMAdminUser(
                email=email,
                password_hash=pwd_context.hash(password),
                display_name="Admin",
                is_active=True,
            )
            session.add(user)
            await session.flush()

            super_role = role_map["super_admin"]
            session.add(ORMAdminUserRole(admin_user_id=user.id, role_id=super_role.id))
            print(f"[SEED]   Admin user created: {email} (role: super_admin)")
        else:
            print(f"[SEED]   Admin user already exists: {email}")

        await session.commit()

        # Step 6: Sync Casbin group rules (g rules: user -> role)
        print("[SEED] Syncing Casbin group rules...")
        enforcer.load_policy()

        rows = (await session.execute(
            select(ORMAdminUserRole)
        )).scalars().all()

        user_role_map: dict[str, list[str]] = {}
        for aur in rows:
            admin_user = (await session.execute(
                select(ORMAdminUser).where(ORMAdminUser.id == aur.admin_user_id)
            )).scalar_one()
            role = (await session.execute(
                select(ORMRole).where(ORMRole.id == aur.role_id)
            )).scalar_one()
            user_role_map.setdefault(admin_user.email, []).append(role.name)

        for user_email, role_names in user_role_map.items():
            for role_name in role_names:
                enforcer.add_grouping_policy(user_email, role_name)
                print(f"[SEED]   g: {user_email} -> {role_name}")

        enforcer.save_policy()

        policies = enforcer.get_policy()
        groups = enforcer.get_named_grouping_policy("g")
        print(f"[SEED]   Casbin sync complete: {len(policies)} p-rules, {len(groups)} g-rules")

        # Verify
        verify = (await session.execute(
            select(ORMAdminUser).where(ORMAdminUser.email == email)
        )).scalar_one()
        d = verify.to_dict()
        print(f"[SEED]   Verify: {d['email']} roles={[r['name'] for r in d['roles']]}")

        print(f"[SEED]   Casbin verify: admin+products+edit = {enforcer.enforce(email, 'products', 'edit')}")

    print("[SEED] Done!")


if __name__ == "__main__":
    asyncio.run(seed_rbac())
