"""Admin RBAC 权限矩阵与校验。

角色定义（REQUIREMENT-ADMIN §7.1）：
- super_admin 管理员：全部功能
- operator 运营：商品 / 订单 / 定价 / AI 探针 / 资源
- support 客服：订单查询 / 退款 / 用户沟通

权限矩阵（§7.2）。super_admin 通配放行；其余按 资源:动作 白名单。
"""

from typing import Any

from fastapi import Depends, HTTPException, status

from forge.main.dependencies import get_current_admin

# 角色 → 资源 → 允许的动作
ROLE_PERMISSIONS: dict[str, dict[str, list[str]]] = {
    "super_admin": {"*": ["*"]},
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


def permissions_for(role: str) -> list[str]:
    """角色对应的权限码列表（/me 返回，前端 v-permission 使用）。"""
    if role == "super_admin":
        return ["*"]
    matrix = ROLE_PERMISSIONS.get(role, {})
    return [f"{res}:{act}" for res, acts in matrix.items() for act in acts]


def _check_permission(role: str, resource: str, action: str) -> bool:
    if role == "super_admin":
        return True
    acts = ROLE_PERMISSIONS.get(role, {}).get(resource)
    return acts is not None and action in acts


def require_permission(resource: str, action: str):
    """路由级权限校验依赖：角色无权限时返回 403。"""

    async def _checker(admin: dict[str, Any] = Depends(get_current_admin)) -> dict[str, Any]:  # noqa: B008 — FastAPI 依赖标准写法
        role = admin.get("role", "")
        if not _check_permission(role, resource, action):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="FORBIDDEN",
            )
        return admin

    return _checker
