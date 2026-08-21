"""Admin Orders API."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from forge.infrastructure.persistence.repositories.order_repo import SQLAlchemyOrderRepository
from forge.main.dependencies import get_db
from forge.main.rbac import require_permission

router = APIRouter()


@router.get("/")
async def list_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: dict = Depends(require_permission("orders", "view")),
    db: AsyncSession = Depends(get_db),
):
    repo = SQLAlchemyOrderRepository()
    return await repo.list_orders(db, page=page, page_size=page_size)
