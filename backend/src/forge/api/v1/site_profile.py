"""C-end Site Profile API.

Returns the *same* merged+normalised profile.config shape as
``GET /api/admin/v1/site/config`` — so the C-end composable
``useSiteProfile`` and Admin editor see EXACTLY the same structure
from the same DB row (``site_profiles`` with ``is_active = True``).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from forge.infrastructure.persistence.repositories.site_profile_repo import SQLAlchemySiteProfileRepository
from forge.infrastructure.site_defaults import merge_for_response
from forge.main.dependencies import get_db

router = APIRouter(tags=["C-end Site Profile"])


@router.get("/site-profile")
async def get_site_profile(db: AsyncSession = Depends(get_db)):
    repo = SQLAlchemySiteProfileRepository()
    profile_raw = await repo.get_active_as_dict(db)
    if profile_raw is None:
        raise HTTPException(status_code=404, detail="没有启用的站点配置")
    # Merge + normalise config with canonical defaults (same helper as Admin)
    profile_raw["config"] = merge_for_response(profile_raw.get("config") or {})
    return {"data": profile_raw}
