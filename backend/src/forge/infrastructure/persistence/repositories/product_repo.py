"""Product — SQLAlchemy Repository."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from forge.infrastructure.persistence.models import ORMProduct


class SQLAlchemyProductRepository:
    """商品数据库访问封装。"""

    @staticmethod
    async def list_products(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        category: Optional[str] = None,
    ) -> dict:
        filters = []
        if category:
            filters.append(ORMProduct.category == category)

        total_query = select(func.count(ORMProduct.id)).where(*filters)
        total = (await db.execute(total_query)).scalar_one()

        query = (
            select(ORMProduct)
            .where(*filters)
            .order_by(ORMProduct.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(query)
        products = result.scalars().all()

        return {
            "items": [p.to_dict() for p in products],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @staticmethod
    async def count(db: AsyncSession) -> int:
        result = await db.execute(select(func.count(ORMProduct.id)))
        return result.scalar_one()
