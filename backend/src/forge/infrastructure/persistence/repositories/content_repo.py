"""Content — SQLAlchemy Repository（轻量 CMS）。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from forge.infrastructure.persistence.models import ORMContent


def _now() -> datetime:
    return datetime.now()


class SQLAlchemyContentRepository:
    """CMS 内容数据库访问封装。"""

    @staticmethod
    async def list_contents(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        status: str | None = None,
        locale: str | None = None,
    ) -> dict[str, Any]:
        filters = []
        if search:
            pattern = f"%{search}%"
            filters.append(ORMContent.title.ilike(pattern) | ORMContent.slug.ilike(pattern))
        if status:
            filters.append(ORMContent.status == status)  # type: ignore[arg-type]
        if locale:
            filters.append(ORMContent.locale == locale)  # type: ignore[arg-type]

        total_query = select(func.count(ORMContent.id)).where(*filters)
        total = (await db.execute(total_query)).scalar_one()

        query = (
            select(ORMContent)
            .where(*filters)
            .order_by(ORMContent.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(query)
        items = result.scalars().all()

        return {
            "items": [c.to_dict() for c in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @staticmethod
    async def get_by_id(db: AsyncSession, content_id: str) -> ORMContent | None:
        result = await db.execute(select(ORMContent).where(ORMContent.id == content_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_slug_locale(db: AsyncSession, slug: str, locale: str = "en") -> ORMContent | None:
        result = await db.execute(
            select(ORMContent).where(ORMContent.slug == slug, ORMContent.locale == locale)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_published_by_slug_locale(db: AsyncSession, slug: str, locale: str = "en") -> ORMContent | None:
        result = await db.execute(
            select(ORMContent).where(
                ORMContent.slug == slug,
                ORMContent.locale == locale,
                ORMContent.status == "published",
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create(db: AsyncSession, data: dict[str, Any]) -> ORMContent:
        content = ORMContent(**data)
        db.add(content)
        await db.flush()
        await db.refresh(content)
        return content

    @staticmethod
    async def update(db: AsyncSession, content: ORMContent, data: dict[str, Any]) -> ORMContent:
        for key, value in data.items():
            if hasattr(content, key):
                setattr(content, key, value)
        content.updated_at = _now()  # type: ignore[assignment]
        await db.flush()
        await db.refresh(content)
        return content

    @staticmethod
    async def delete(db: AsyncSession, content: ORMContent) -> None:
        await db.delete(content)
        await db.flush()
