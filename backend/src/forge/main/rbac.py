"""Admin RBAC 权限校验（DB 权威）。

角色定义（REQUIREMENT-ADMIN §7.1）：
- super_admin 管理员：全部功能
- operator 运营：商品 / 订单 / 定价 / AI 探针 / 资源
- support 客服：订单查询 / 退款 / 用户沟通

运行时权限判定完全以数据库为准（admin_user_roles → roles →
role_permissions → permissions）；super_admin 角色通配放行。
ROLE_PERMISSIONS 仅作为迁移种子定义（见 migration 0023），
不允许在运行时直接读取。
"""

from typing import Any

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from forge.infrastructure.persistence.models import ORMRole
from forge.main.dependencies import get_current_admin, get_db

# 种子定义：角色 → 资源 → 允许的动作。
# 仅用于 migration 0023 生成 permissions / role_permissions 种子数据。
ROLE_PERMISSIONS: dict[str, dict[str, list[str]]] = {
    "super_admin": {"*": ["*"]},
    "admin": {
        "dashboard": ["view"],
        "products": ["view", "create", "edit", "delete", "status"],
        "orders": ["view", "detail", "review", "procure", "logistics", "refund"],
        "pricing": ["view", "manage"],
        "ai_probe": ["view"],
        "chat_requests": ["view", "manage"],
        "resources": ["view", "upload"],
        "shipments": ["view", "manage"],
        "suppliers": ["view", "manage"],
        "supplier_sources": ["view", "manage"],
        "settings": ["view", "manage"],
        "site_config": ["view", "manage"],
        "site_profile": ["view", "manage"],
        "admin_roles": ["view", "manage"],
        "admin_users": ["view", "manage"],
        "users": ["view", "manage"],
        "mcp_keys": ["view", "manage"],
    },
    "operator": {
        "dashboard": ["view"],
        "products": ["view", "create", "edit", "delete", "status"],
        "orders": ["view", "detail", "review", "procure", "logistics", "refund"],
        "pricing": ["view", "manage"],
        "ai_probe": ["view"],
        "chat_requests": ["view", "manage"],
        "resources": ["view", "upload"],
        "shipments": ["view", "manage"],
    },
    "support": {
        "dashboard": ["view"],
        "orders": ["view", "detail", "refund"],
        "chat_requests": ["view"],
    },
}

MODULE_NAMES: dict[str, str] = {
    "dashboard": "数据看板",
    "products": "商品管理",
    "orders": "订单管理",
    "pricing": "定价管理",
    "ai_probe": "AI 探针",
    "chat_requests": "咨询请求",
    "resources": "资源管理",
    "shipments": "发货管理",
    "suppliers": "供应商管理",
    "supplier_sources": "货源管理",
    "settings": "系统设置",
    "site_config": "站点配置",
    "site_profile": "站点资料",
    "admin_roles": "角色管理",
    "admin_users": "管理员",
    "users": "用户管理",
    "mcp_keys": "MCP 密钥",
}

ACTION_NAMES: dict[str, str] = {
    "view": "查看",
    "detail": "查看详情",
    "create": "新建",
    "edit": "编辑",
    "delete": "删除",
    "status": "上下架",
    "review": "审核",
    "procure": "采购",
    "logistics": "物流",
    "refund": "退款",
    "manage": "管理",
    "upload": "上传",
}


def seed_permissions() -> list[dict[str, str]]:
    """从静态矩阵生成权限种子（module, code, display_name）。"""
    rows: list[dict[str, str]] = []
    for role, resources in ROLE_PERMISSIONS.items():
        if role == "super_admin":
            continue
        for resource, actions in resources.items():
            for action in actions:
                rows.append(
                    {
                        "module": resource,
                        "code": f"{resource}:{action}",
                        "display_name": f"{MODULE_NAMES.get(resource, resource)}-{ACTION_NAMES.get(action, action)}",
                    }
                )
    return rows


def seed_role_permissions(role: str) -> list[str]:
    """角色应拥有的权限码列表（super_admin 返回空，运行时通配）。"""
    if role == "super_admin":
        return []
    return [f"{res}:{act}" for res, acts in ROLE_PERMISSIONS.get(role, {}).items() for act in acts]


async def role_permission_codes(db: AsyncSession, roles: list[str]) -> set[str]:
    """查询角色集合拥有的权限码集合；super_admin 通配为 {"*"}。"""
    if "super_admin" in roles:
        return {"*"}
    if not roles:
        return set()
    role_rows = (await db.execute(select(ORMRole).where(ORMRole.name.in_(roles)))).scalars().all()
    codes: set[str] = set()
    for role in role_rows:
        codes.update(p.code for p in role.permissions)  # type: ignore[misc]
    return codes


async def permissions_for(db: AsyncSession, roles: list[str]) -> list[str]:
    """角色集合对应的权限码列表（/me 返回，前端 v-permission 使用）。"""
    codes = await role_permission_codes(db, roles)
    if "*" in codes:
        return ["*"]
    return sorted(codes)


def _has_permission(codes: set[str], resource: str, action: str) -> bool:
    if "*" in codes:
        return True
    return f"{resource}:{action}" in codes


def require_permission(resource: str, action: str) -> Any:
    """路由级权限校验依赖：角色无权限时返回 403。"""

    async def _checker(
        admin: dict[str, Any] = Depends(get_current_admin),  # noqa: B008 — FastAPI 依赖标准写法
        db: AsyncSession = Depends(get_db),  # noqa: B008 — FastAPI 依赖标准写法
    ) -> dict[str, Any]:
        roles: list[str] = admin.get("roles") or ([admin["role"]] if admin.get("role") else [])
        codes = await role_permission_codes(db, roles)
        if not _has_permission(codes, resource, action):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="FORBIDDEN",
            )
        return admin

    return _checker
