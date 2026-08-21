"""Admin - Site Profiles API."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from forge.infrastructure.persistence.models import ORMSiteProfile
from forge.infrastructure.persistence.repositories.site_profile_repo import SQLAlchemySiteProfileRepository
from forge.main.dependencies import get_db
from forge.main.rbac import require_permission

router = APIRouter()
site_router = APIRouter()


@router.get("/")
async def list_site_profiles(
    admin: dict[str, object] = Depends(require_permission("site_profile", "manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict[str, object]:
    total_query = select(func.count(ORMSiteProfile.id))
    total = (await db.execute(total_query)).scalar_one()

    query = select(ORMSiteProfile).order_by(ORMSiteProfile.created_at.desc())
    result = await db.execute(query)
    profiles = result.scalars().all()

    return {
        "items": [
            {
                "id": str(p.id),
                "name": p.name,
                "label": p.label,
                "is_active": p.is_active,
                "config": p.config or {},
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in profiles
        ],
        "total": total,
    }


@site_router.get("/site")
async def get_site(
    admin: dict[str, object] = Depends(require_permission("site_profile", "view")),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict[str, object]:
    repo = SQLAlchemySiteProfileRepository()
    profile: dict[str, object] | None = await repo.get_active_as_dict(db)
    if profile is None:
        return {}
    return profile
