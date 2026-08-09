"""Admin - Roles API."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from forge.infrastructure.persistence.models import ORMRole
from forge.main.dependencies import get_current_admin, get_db

router = APIRouter()


@router.get("/")
async def list_roles(
    admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    total_query = select(func.count(ORMRole.id))
    total = (await db.execute(total_query)).scalar_one()

    query = select(ORMRole).order_by(ORMRole.created_at.desc())
    result = await db.execute(query)
    roles = result.scalars().all()

    return {
        "items": [
            {
                "id": str(r.id),
                "name": r.name,
                "display_name": r.display_name,
                "description": r.description,
                "is_system": r.is_system,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in roles
        ],
        "total": total,
    }
