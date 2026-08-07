"""Admin API v1 路由聚合器。

所有管理后台接口统一挂载在 /api/admin/v1 下，
与面向消费者的 /api/v1 隔离。
"""

from fastapi import APIRouter

from forge.api.admin.v1 import (
    admin_roles,
    admin_users,
    auth,
    dashboard,
    orders,
    pricing,
    products,
    routes,
    shipments,
    suppliers,
    chat_requests,
    users,
    settings,
    site_profile,
    site_config,
    diy,
)

admin_router = APIRouter(prefix="/api/admin/v1")

# --- Auth (independent from C-end) ---
admin_router.include_router(auth.router, prefix="/auth", tags=["Admin - Auth"])

# --- Dynamic Routes (role-based menu filtering) ---
admin_router.include_router(routes.router, prefix="/route", tags=["Admin - Routes"])

# --- 注册子路由 ---

# Dashboard (admin / operator / support 均可)
admin_router.include_router(dashboard.router, tags=["Admin - Dashboard"])

# Products (admin / operator)
admin_router.include_router(products.router, prefix="/products", tags=["Admin - Products"])

# Orders (admin / operator / support)
admin_router.include_router(orders.router, prefix="/orders", tags=["Admin - Orders"])

# Suppliers (admin only)
admin_router.include_router(suppliers.router, prefix="/suppliers", tags=["Admin - Suppliers"])

# Pricing (admin / operator)
admin_router.include_router(pricing.router, prefix="/pricing", tags=["Admin - Pricing"])

# Shipments (admin / operator / support for reads)
admin_router.include_router(shipments.router, prefix="/shipments", tags=["Admin - Shipments"])

# Chat Requests / AI Probe (admin / operator)
admin_router.include_router(chat_requests.router, prefix="/chat-requests", tags=["Admin - Probe"])

# Users (admin only)
admin_router.include_router(users.router, prefix="/users", tags=["Admin - Users"])

# Settings (admin / operator for reads, admin only for writes)
admin_router.include_router(settings.router, prefix="/settings", tags=["Admin - Settings"])

# Admin Users & Roles (super_admin / admin)
admin_router.include_router(admin_users.router, prefix="/admin-users", tags=["Admin - Admin Users"])
admin_router.include_router(admin_roles.router, prefix="/roles", tags=["Admin - Roles"])

# Site Profiles (admin only)
admin_router.include_router(site_profile.router, prefix="/site-profiles", tags=["Admin - Site Profiles"])

# Convenience: /api/admin/v1/site (admin SPA 直调路径)
admin_router.include_router(site_profile.site_router, tags=["Admin - Site Profiles"])

# 站点可视化装修 v2.0 (settings:manage) — /api/admin/v1/site/{pages,components,templates,...}
admin_router.include_router(diy.router, prefix="/site", tags=["Admin - Site Decoration"])
admin_router.include_router(site_config.router, prefix="/site", tags=["Admin - Site Config"])
