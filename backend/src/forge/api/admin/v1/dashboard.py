"""Admin Dashboard API."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from forge.infrastructure.persistence.repositories.user_repo import SQLAlchemyUserRepository
from forge.infrastructure.persistence.repositories.product_repo import SQLAlchemyProductRepository
from forge.infrastructure.persistence.repositories.order_repo import SQLAlchemyOrderRepository
from forge.main.dependencies import get_current_admin, get_db

router = APIRouter()


@router.get("/")
async def get_dashboard(
    admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    user_repo = SQLAlchemyUserRepository()
    product_repo = SQLAlchemyProductRepository()
    order_repo = SQLAlchemyOrderRepository()

    total_users = await user_repo.count(db)
    total_products = await product_repo.count(db)
    total_orders = await order_repo.count(db)
    status_counts = await order_repo.count_by_status(db)

    return {
        "total_orders": total_orders,
        "total_revenue": 0.0,
        "total_users": total_users,
        "total_products": total_products,
        "order_status": status_counts,
        "recent_orders": [],
        "order_trend": [],
    }
