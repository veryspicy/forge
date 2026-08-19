"""Supplier — SQLAlchemy Repository."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from forge.infrastructure.persistence.models import ORMSupplier


def _now() -> datetime:
    return datetime.now()


class SQLAlchemySupplierRepository:
    """供应商数据库访问封装。"""

    @staticmethod
    async def list_suppliers(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        is_active: bool | None = None,
    ) -> dict[str, Any]:
        filters = []
        if search:
            pattern = f"%{search}%"
            filters.append(ORMSupplier.name.ilike(pattern))
        if is_active is not None:
            filters.append(ORMSupplier.is_active == is_active)

        total_query = select(func.count(ORMSupplier.id)).where(*filters)
        total = (await db.execute(total_query)).scalar_one()

        query = (
            select(ORMSupplier)
            .where(*filters)
            .order_by(ORMSupplier.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(query)
        suppliers = result.scalars().all()

        return {
            "items": [s.to_dict() for s in suppliers],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @staticmethod
    async def get_by_id(db: AsyncSession, supplier_id: str) -> ORMSupplier | None:
        result = await db.execute(select(ORMSupplier).where(ORMSupplier.id == supplier_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_name(db: AsyncSession, name: str) -> ORMSupplier | None:
        result = await db.execute(select(ORMSupplier).where(ORMSupplier.name == name))
        return result.scalar_one_or_none()

    @staticmethod
    async def create(db: AsyncSession, data: dict[str, Any]) -> ORMSupplier:
        supplier = ORMSupplier(**data)
        db.add(supplier)
        await db.flush()
        await db.refresh(supplier)
        return supplier

    @staticmethod
    async def update(db: AsyncSession, supplier: ORMSupplier, data: dict[str, Any]) -> ORMSupplier:
        for key, value in data.items():
            if hasattr(supplier, key):
                setattr(supplier, key, value)
        supplier.updated_at = _now()
        await db.flush()
        await db.refresh(supplier)
        return supplier

    @staticmethod
    async def count(db: AsyncSession) -> int:
        result = await db.execute(select(func.count(ORMSupplier.id)))
        return result.scalar_one()
