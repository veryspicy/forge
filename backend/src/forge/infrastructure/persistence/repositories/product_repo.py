"""Product — SQLAlchemy Repository."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from forge.infrastructure.persistence.models import ORMProduct, ORMProductVariant


def _now() -> datetime:
    return datetime.now(UTC)


class SQLAlchemyProductRepository:
    """商品数据库访问封装。"""

    @staticmethod
    async def list_products(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        category: str | None = None,
        search: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        filters = []
        if category:
            filters.append(ORMProduct.category == category)
        if status:
            filters.append(ORMProduct.status == status)
        if search:
            pattern = f"%{search}%"
            filters.append(
                or_(
                    ORMProduct.name.ilike(pattern),
                    ORMProduct.sku.ilike(pattern),
                )
            )

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
    async def list_all(db: AsyncSession) -> list[ORMProduct]:
        """导出用：按创建时间升序返回全量商品。"""
        result = await db.execute(select(ORMProduct).order_by(ORMProduct.created_at.asc()))
        return list(result.scalars().all())

    @staticmethod
    async def get_by_id(db: AsyncSession, product_id: str) -> ORMProduct | None:
        result = await db.execute(select(ORMProduct).where(ORMProduct.id == product_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_sku(db: AsyncSession, sku: str) -> ORMProduct | None:
        result = await db.execute(select(ORMProduct).where(ORMProduct.sku == sku))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_slug(db: AsyncSession, slug: str) -> ORMProduct | None:
        result = await db.execute(select(ORMProduct).where(ORMProduct.slug == slug))
        return result.scalar_one_or_none()

    @staticmethod
    async def create(db: AsyncSession, data: dict[str, Any]) -> ORMProduct:
        product = ORMProduct(**data)
        db.add(product)
        await db.flush()
        await db.refresh(product)
        return product

    @staticmethod
    async def update(db: AsyncSession, product: ORMProduct, data: dict[str, Any]) -> ORMProduct:
        for key, value in data.items():
            if hasattr(product, key):
                setattr(product, key, value)
        product.updated_at = _now()  # type: ignore[assignment]
        await db.flush()
        await db.refresh(product)
        return product

    @staticmethod
    async def set_status(db: AsyncSession, product: ORMProduct, status: str) -> ORMProduct:
        product.status = status  # type: ignore[assignment]
        product.updated_at = _now()  # type: ignore[assignment]
        await db.flush()
        await db.refresh(product)
        return product

    @staticmethod
    async def update_images(db: AsyncSession, product: ORMProduct, images: list[dict[str, Any]]) -> ORMProduct:
        product.images = images  # type: ignore[assignment]
        product.updated_at = _now()  # type: ignore[assignment]
        await db.flush()
        await db.refresh(product)
        return product

    @staticmethod
    async def count(db: AsyncSession) -> int:
        result = await db.execute(select(func.count(ORMProduct.id)))
        return result.scalar_one()

    # ------------------------------------------------------------------
    # 变体（P2-1）
    # ------------------------------------------------------------------
    @staticmethod
    async def list_variants(db: AsyncSession, product_id: str) -> list[ORMProductVariant]:
        result = await db.execute(
            select(ORMProductVariant)
            .where(ORMProductVariant.product_id == product_id)
            .order_by(ORMProductVariant.created_at.asc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_variant_by_id(db: AsyncSession, variant_id: str) -> ORMProductVariant | None:
        result = await db.execute(select(ORMProductVariant).where(ORMProductVariant.id == variant_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_variant_by_sku(db: AsyncSession, sku: str) -> ORMProductVariant | None:
        result = await db.execute(select(ORMProductVariant).where(ORMProductVariant.sku == sku))
        return result.scalar_one_or_none()

    @staticmethod
    async def create_variant(db: AsyncSession, data: dict[str, Any]) -> ORMProductVariant:
        variant = ORMProductVariant(**data)
        db.add(variant)
        await db.flush()
        await db.refresh(variant)
        return variant

    @staticmethod
    async def update_variant(
        db: AsyncSession,
        variant: ORMProductVariant,
        data: dict[str, Any],
    ) -> ORMProductVariant:
        for key, value in data.items():
            if hasattr(variant, key):
                setattr(variant, key, value)
        variant.updated_at = _now()  # type: ignore[assignment]
        await db.flush()
        await db.refresh(variant)
        return variant

    @staticmethod
    async def delete_variant(db: AsyncSession, variant: ORMProductVariant) -> None:
        await db.delete(variant)
        await db.flush()
