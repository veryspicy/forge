"""Admin - Admin Users API."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from forge.infrastructure.persistence.repositories.user_repo import SQLAlchemyAdminUserRepository
from forge.main.dependencies import get_db
from forge.main.rbac import require_permission

router = APIRouter()


@router.get("/")
async def list_admin_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: dict = Depends(require_permission("admin_users", "manage")),
    db: AsyncSession = Depends(get_db),
):
    repo = SQLAlchemyAdminUserRepository()
    return await repo.list_admin_users(db, page=page, page_size=page_size)
