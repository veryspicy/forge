"""Cart Repository - SQLAlchemy (C-end shopping cart).

- list_by_user: fetch cart rows for a user
- get_for_user: single cart item owned by user
- add_item: add / merge quantity for same product
- update_quantity / remove / clear_for_user
- naive UTC datetimes (table is TIMESTAMP WITHOUT TIME ZONE)
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from forge.infrastructure.persistence.models import ORMCartItem


class SQLAlchemyCartRepository:
    """购物车表访问封装（C 端按 user 隔离）。"""

    @staticmethod
    def _now() -> datetime:
        # Table columns are TIMESTAMP WITHOUT TIME ZONE; naive UTC avoids asyncpg aware/naive mixing.
        return datetime.now(UTC).replace(tzinfo=None)

    @staticmethod
    async def list_by_user(db: AsyncSession, user_id: UUID) -> list[ORMCartItem]:
        rows = (
            await db.execute(
                select(ORMCartItem)
                .where(ORMCartItem.user_id == user_id)
                .order_by(ORMCartItem.created_at.asc())
            )
        ).scalars().all()
        return list(rows)

    @staticmethod
    async def get_for_user(db: AsyncSession, user_id: UUID, item_id: UUID) -> ORMCartItem | None:
        return (
            await db.execute(
                select(ORMCartItem).where(
                    ORMCartItem.id == item_id, ORMCartItem.user_id == user_id
                )
            )
        ).scalar_one_or_none()

    @staticmethod
    async def add_item(
        db: AsyncSession,
        user_id: UUID,
        product: dict[str, Any],
        quantity: int,
    ) -> ORMCartItem:
        """Add a product snapshot; merge quantity when the same product already exists."""
        now = SQLAlchemyCartRepository._now()
        product_id = cast(int, product["id"])
        existing = (
            await db.execute(
                select(ORMCartItem).where(
                    ORMCartItem.user_id == user_id, ORMCartItem.product_id == product_id
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            existing.quantity = cast(Any, cast(int, existing.quantity) + quantity)
            existing.updated_at = cast(Any, now)
            await db.flush()
            return existing
        item = ORMCartItem(
            id=uuid4(),
            user_id=user_id,
            product_id=product_id,
            name=cast(str, product["name"]),
            price=cast(Any, product["price"]),
            quantity=quantity,
            image=product.get("image"),
            created_at=now,
            updated_at=now,
        )
        db.add(item)
        await db.flush()
        return item

    @staticmethod
    async def update_quantity(
        db: AsyncSession,
        user_id: UUID,
        item_id: UUID,
        quantity: int,
    ) -> ORMCartItem | None:
        item = await SQLAlchemyCartRepository.get_for_user(db, user_id, item_id)
        if item is None:
            return None
        item.quantity = cast(Any, quantity)
        item.updated_at = cast(Any, SQLAlchemyCartRepository._now())
        await db.flush()
        return item

    @staticmethod
    async def remove(db: AsyncSession, user_id: UUID, item_id: UUID) -> ORMCartItem | None:
        item = await SQLAlchemyCartRepository.get_for_user(db, user_id, item_id)
        if item is None:
            return None
        await db.delete(item)
        await db.flush()
        return item

    @staticmethod
    async def clear_for_user(db: AsyncSession, user_id: UUID) -> None:
        await db.execute(delete(ORMCartItem).where(ORMCartItem.user_id == user_id))
        await db.flush()
