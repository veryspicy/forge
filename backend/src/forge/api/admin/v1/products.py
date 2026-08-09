"""Admin Products API."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from forge.infrastructure.persistence.repositories.product_repo import SQLAlchemyProductRepository
from forge.main.dependencies import get_current_admin, get_db

router = APIRouter()


@router.get("/")
async def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    repo = SQLAlchemyProductRepository()
    return await repo.list_products(db, page=page, page_size=page_size)
