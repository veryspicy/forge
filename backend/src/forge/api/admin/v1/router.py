"""Admin API v1 路由聚合器。

所有管理后台接口统一挂载在 /api/admin/v1 下，
与面向消费者的 /api/v1 隔离。

各子模块导入采用 try/except 容错，任一模块缺失不影响其余路由注册。
"""

import logging
from fastapi import APIRouter

logger = logging.getLogger(__name__)

admin_router = APIRouter(prefix="/api/admin/v1")

# --- Helper to safely include a submodule ---
def _safe_include(module_name: str, prefix: str = "", tags: list = None):
    try:
        mod = __import__(f"forge.api.admin.v1.{module_name}", fromlist=[module_name])
        router = getattr(mod, "router", None)
        if router is None:
            logger.warning(f"Module '{module_name}' has no 'router' attribute, skipping")
            return
        kwargs = {}
        if prefix:
            kwargs["prefix"] = prefix
        if tags:
            kwargs["tags"] = tags
        admin_router.include_router(router, **kwargs)
    except ImportError as e:
        logger.warning(f"Module '{module_name}' not available, skipping: {e}")

# --- Auth (independent from C-end) ---
_safe_include("auth", prefix="/auth", tags=["Admin - Auth"])

# --- Dynamic Routes (role-based menu filtering) ---
_safe_include("routes", prefix="/route", tags=["Admin - Routes"])

# Dashboard
_safe_include("dashboard", prefix="/dashboard", tags=["Admin - Dashboard"])

# Products
_safe_include("products", prefix="/products", tags=["Admin - Products"])

# Orders
_safe_include("orders", prefix="/orders", tags=["Admin - Orders"])

# Suppliers
_safe_include("suppliers", prefix="/suppliers", tags=["Admin - Suppliers"])

# Pricing
_safe_include("pricing", prefix="/pricing", tags=["Admin - Pricing"])

# Shipments
_safe_include("shipments", prefix="/shipments", tags=["Admin - Shipments"])

# Chat Requests
_safe_include("chat_requests", prefix="/chat-requests", tags=["Admin - Probe"])

# Users
_safe_include("users", prefix="/users", tags=["Admin - Users"])

# Settings
_safe_include("settings", prefix="/settings", tags=["Admin - Settings"])

# Admin Users & Roles
_safe_include("admin_users", prefix="/admin-users", tags=["Admin - Admin Users"])
_safe_include("admin_roles", prefix="/roles", tags=["Admin - Roles"])

# Site Profiles
_safe_include("site_profile", prefix="/site-profiles", tags=["Admin - Site Profiles"])

# Convenience site endpoint (site_router on site_profile module)
try:
    import forge.api.admin.v1.site_profile as _sp
    if hasattr(_sp, "site_router"):
        admin_router.include_router(_sp.site_router, tags=["Admin - Site Profiles"])
except ImportError:
    pass

# Site decoration & config
_safe_include("site_config", prefix="/site", tags=["Admin - Site Config"])
