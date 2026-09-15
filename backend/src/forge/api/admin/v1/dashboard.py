"""Admin Dashboard API."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from forge.infrastructure.persistence.repositories.order_repo import SQLAlchemyOrderRepository
from forge.infrastructure.persistence.repositories.product_repo import SQLAlchemyProductRepository
from forge.infrastructure.persistence.repositories.supplier_repo import SQLAlchemySupplierRepository
from forge.infrastructure.persistence.repositories.user_repo import SQLAlchemyUserRepository
from forge.main.dependencies import get_db
from forge.main.rbac import require_permission

router = APIRouter()


@router.get("/")
async def get_dashboard(
    admin: dict[str, object] = Depends(require_permission("dashboard", "view")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    """首页聚合统计（字段名即 admin 前端 dashboard 视图契约）。

    - 统计卡：today_orders / pending_orders / today_gmv / active_products /
      probe_adoption_rate / procurement_errors / total_suppliers / today_probe_requests
    - 图表：order_trend（近 7 日）/ product_categories（分类分布）
    - 兼容字段：total_orders / total_revenue / total_users / total_products / order_status
    """
    user_repo = SQLAlchemyUserRepository()
    product_repo = SQLAlchemyProductRepository()
    order_repo = SQLAlchemyOrderRepository()
    supplier_repo = SQLAlchemySupplierRepository()

    order_stats = await order_repo.dashboard_stats(db)
    total_users = await user_repo.count(db)
    total_products = await product_repo.count(db)
    active_products = await product_repo.count_active(db)
    product_categories = await product_repo.category_distribution(db)
    total_suppliers = await supplier_repo.count(db)

    return {
        # ---- 统计卡（前端 dashboard 视图字段契约）----
        "today_orders": order_stats["today_orders"],
        "pending_orders": order_stats["pending_orders"],
        "today_gmv": order_stats["today_gmv"],
        "active_products": active_products,
        # AI 探测域暂无落库数据源（无探测请求表），先置 0，待 ai-service 埋点后替换
        "probe_adoption_rate": 0,
        "procurement_errors": order_stats["procurement_errors"],
        "total_suppliers": total_suppliers,
        "today_probe_requests": 0,
        # ---- 图表 ----
        "order_trend": order_stats["order_trend"],
        "product_categories": product_categories,
        # ---- 兼容旧字段 ----
        "total_orders": order_stats["total_orders"],
        "total_revenue": order_stats["total_revenue"],
        "total_users": total_users,
        "total_products": total_products,
        "order_status": order_stats["status_counts"],
        "recent_orders": [],
    }
