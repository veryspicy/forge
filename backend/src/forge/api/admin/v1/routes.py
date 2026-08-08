"""Admin 动态路由接口。

根据当前登录 admin 用户的角色，返回对应的菜单路由配置和首页路由名称。
"""

from fastapi import APIRouter, Depends

from forge.main.dependencies import get_current_admin

router = APIRouter()

# ---------------------------------------------------------------------------
# 前端路由配置（与 admin/src/router/routes/index.ts 同步维护）
# 每个路由节点包含:
#   id         - 唯一标识
#   name       - 路由名称，必须与前端 LastLevelRouteKey 一致
#   path       - URL 路径
#   component  - 组件映射字符串（layout.base$view.xxx 或 layout.blank$view.xxx）
#   redirect   - 父路由的重定向目标
#   meta       - 元信息：title, i18nKey, icon, order, roles, hideInMenu 等
#   children   - 子路由列表
# ---------------------------------------------------------------------------

AUTH_ROUTE_TREE = [
    {
        "id": "dashboard",
        "name": "dashboard",
        "path": "/dashboard",
        "component": "layout.base$view.dashboard",
        "meta": {
            "title": "Dashboard",
            "i18nKey": "route.dashboard",
            "icon": "mdi:monitor-dashboard",
            "order": 1,
            "roles": ["super_admin", "admin", "operator", "support"],
        },
    },
    {
        "id": "merchandise",
        "name": "merchandise",
        "path": "/merchandise",
        "redirect": "/products",
        "meta": {
            "title": "Merchandise",
            "i18nKey": "route.merchandise",
            "icon": "mdi:store",
            "order": 2,
            "roles": ["super_admin", "admin", "operator"],
        },
        "children": [
            {
                "id": "products",
                "name": "products",
                "path": "/products",
                "component": "layout.base$view.products",
                "meta": {
                    "title": "Products",
                    "i18nKey": "route.products",
                    "icon": "mdi:package-variant",
                    "order": 1,
                    "roles": ["super_admin", "admin", "operator"],
                },
            },
            {
                "id": "products-new",
                "name": "products-new",
                "path": "/products/new",
                "component": "layout.base$view.products-new",
                "meta": {
                    "title": "New Product",
                    "i18nKey": "route.products-new",
                    "hideInMenu": True,
                    "activeMenu": "products",
                    "roles": ["super_admin", "admin", "operator"],
                },
            },
            {
                "id": "products-detail",
                "name": "products-detail",
                "path": "/products/:id",
                "component": "layout.base$view.products-detail",
                "meta": {
                    "title": "Edit Product",
                    "i18nKey": "route.products-detail",
                    "hideInMenu": True,
                    "activeMenu": "products",
                    "roles": ["super_admin", "admin", "operator"],
                },
            },
            {
                "id": "suppliers",
                "name": "suppliers",
                "path": "/suppliers",
                "component": "layout.base$view.suppliers",
                "meta": {
                    "title": "Suppliers",
                    "i18nKey": "route.suppliers",
                    "icon": "mdi:truck-delivery",
                    "order": 2,
                    "roles": ["super_admin", "admin"],
                },
            },
            {
                "id": "pricing",
                "name": "pricing",
                "path": "/pricing",
                "component": "layout.base$view.pricing",
                "meta": {
                    "title": "Pricing",
                    "i18nKey": "route.pricing",
                    "icon": "mdi:cash-multiple",
                    "order": 3,
                    "roles": ["super_admin", "admin"],
                },
            },
        ],
    },
    {
        "id": "sales",
        "name": "sales",
        "path": "/sales",
        "redirect": "/orders",
        "meta": {
            "title": "Sales",
            "i18nKey": "route.sales",
            "icon": "mdi:shopping",
            "order": 3,
            "roles": ["super_admin", "admin", "operator", "support"],
        },
        "children": [
            {
                "id": "orders",
                "name": "orders",
                "path": "/orders",
                "component": "layout.base$view.orders",
                "meta": {
                    "title": "Orders",
                    "i18nKey": "route.orders",
                    "icon": "mdi:cart",
                    "order": 1,
                    "roles": ["super_admin", "admin", "operator", "support"],
                },
            },
            {
                "id": "orders-detail",
                "name": "orders-detail",
                "path": "/orders/:id",
                "component": "layout.base$view.orders-detail",
                "meta": {
                    "title": "Order Detail",
                    "i18nKey": "route.orders-detail",
                    "hideInMenu": True,
                    "activeMenu": "orders",
                    "roles": ["super_admin", "admin", "operator", "support"],
                },
            },
            {
                "id": "shipments",
                "name": "shipments",
                "path": "/shipments",
                "component": "layout.base$view.shipments",
                "meta": {
                    "title": "Shipments",
                    "i18nKey": "route.shipments",
                    "icon": "mdi:package-variant-closed",
                    "order": 2,
                    "roles": ["super_admin", "admin", "operator"],
                },
            },
        ],
    },
    {
        "id": "customers",
        "name": "customers",
        "path": "/customers",
        "component": "layout.base$view.users",
        "meta": {
            "title": "Customers",
            "i18nKey": "route.customers",
            "icon": "mdi:account-group",
            "order": 4,
            "roles": ["super_admin", "admin", "operator"],
        },
    },
    {
        "id": "ai-probe",
        "name": "ai-probe",
        "path": "/ai-probe",
        "component": "layout.base$view.ai-probe",
        "meta": {
            "title": "AI Probe",
            "i18nKey": "route.ai-probe",
            "icon": "mdi:robot",
            "order": 5,
            "roles": ["super_admin", "admin", "support"],
        },
    },
    {
        "id": "site",
        "name": "site",
        "path": "/site",
        "redirect": "/site/decoration",
        "meta": {
            "title": "站点",
            "i18nKey": "route.site",
            "icon": "mdi:web",
            "order": 6,
            "roles": ["super_admin", "admin", "operator"],
        },
        "children": [
            {
                "id": "site-decoration",
                "name": "site-decoration",
                "path": "/site/decoration",
                "component": "layout.base$view.diy",
                "meta": {
                    "title": "页面装修",
                    "i18nKey": "route.site-decoration",
                    "roles": ["super_admin", "admin", "operator"],
                },
            },
            {
                "id": "site-decoration-editor",
                "name": "site-decoration-editor",
                "path": "/site/decoration/editor/:id",
                "component": "layout.base$view.diy-editor",
                "meta": {
                    "title": "页面编辑器",
                    "i18nKey": "route.site-decoration-editor",
                    "hideInMenu": True,
                    "activeMenu": "site-decoration",
                    "roles": ["super_admin", "admin", "operator"],
                },
            },
        ],
    },
    {
        "id": "system",
        "name": "system",
        "path": "/system",
        "redirect": "/admin-users",
        "meta": {
            "title": "System",
            "i18nKey": "route.system",
            "icon": "mdi:cog",
            "order": 8,
            "roles": ["super_admin", "admin"],
        },
        "children": [
            {
                "id": "admin-users",
                "name": "admin-users",
                "path": "/admin-users",
                "component": "layout.base$view.admin-users",
                "meta": {
                    "title": "Admin Users",
                    "i18nKey": "route.admin-users",
                    "icon": "mdi:account-cog",
                    "order": 1,
                    "roles": ["super_admin", "admin"],
                },
            },
            {
                "id": "roles",
                "name": "roles",
                "path": "/roles",
                "component": "layout.base$view.roles",
                "meta": {
                    "title": "Roles",
                    "i18nKey": "route.roles",
                    "icon": "mdi:shield-key",
                    "order": 2,
                    "roles": ["super_admin", "admin"],
                },
            },
            {
                "id": "settings",
                "name": "settings",
                "path": "/settings",
                "component": "layout.base$view.settings",
                "meta": {
                    "title": "Settings",
                    "i18nKey": "route.settings",
                    "icon": "mdi:cog",
                    "order": 3,
                    "roles": ["super_admin", "admin"],
                },
            },
        ],
    },
]


def _filter_routes_by_roles(routes: list[dict], user_roles: list[str]) -> list[dict]:
    """按用户角色过滤路由树，递归移除无权限的节点。"""
    filtered = []
    for node in routes:
        node_roles = node.get("meta", {}).get("roles", [])
        if node_roles and not any(r in node_roles for r in user_roles):
            continue  # 该节点用户角色无权限，跳过

        # 深拷贝节点避免污染原始数据
        node_copy = dict(node)
        if "children" in node_copy:
            node_copy["children"] = _filter_routes_by_roles(
                node_copy["children"], user_roles
            )
            # 过滤后无子节点且自身无 component → 空的父菜单，移除
            if not node_copy["children"] and "component" not in node_copy:
                continue

        # 移除 meta.roles（仅后端使用，前端不需要）
        if "meta" in node_copy and "roles" in node_copy["meta"]:
            del node_copy["meta"]["roles"]

        filtered.append(node_copy)
    return filtered


@router.get("/getUserRoutes", include_in_schema=False)
async def get_user_routes(admin: dict = Depends(get_current_admin)):
    """返回当前 admin 用户有权访问的动态路由和首页路由名。

    - routes: 按用户 roles 过滤后的路由树
    - home: 固定返回 "dashboard"
    """
    role = admin.get("role", "")
    user_roles: list[str] = [role] if role else admin.get("roles", [])
    filtered = _filter_routes_by_roles(AUTH_ROUTE_TREE, user_roles)
    return {
        "routes": filtered,
        "home": "dashboard",
    }
