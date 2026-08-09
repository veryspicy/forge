"""Site Profile — SQLAlchemy Repository."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from forge.infrastructure.persistence.models import ORMSiteProfile


class SQLAlchemySiteProfileRepository:
    """站点配置数据库访问封装。"""

    @staticmethod
    async def get_active(db: AsyncSession) -> Optional[ORMSiteProfile]:
        stmt = select(ORMSiteProfile).where(ORMSiteProfile.is_active == True)  # noqa: E712
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_active_as_dict(db: AsyncSession) -> Optional[dict]:
        profile = await SQLAlchemySiteProfileRepository.get_active(db)
        if profile is None:
            return None
        return {
            "id": str(profile.id),
            "name": profile.name,
            "label": profile.label,
            "is_active": profile.is_active,
            "config": profile.config or {},
            "created_at": profile.created_at.isoformat() if profile.created_at else None,
            "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
        }
