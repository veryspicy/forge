"""C-end Site Profile API."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from forge.infrastructure.persistence.repositories.site_profile_repo import SQLAlchemySiteProfileRepository
from forge.main.dependencies import get_db

router = APIRouter(tags=["C-end Site Profile"])


@router.get("/site-profile")
async def get_site_profile(db: AsyncSession = Depends(get_db)):
    repo = SQLAlchemySiteProfileRepository()
    profile = await repo.get_active_as_dict(db)
    if profile is None:
        raise HTTPException(status_code=404, detail="没有启用的站点配置")
    return {"data": profile}
