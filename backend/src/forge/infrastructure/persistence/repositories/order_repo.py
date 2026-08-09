"""Order — SQLAlchemy Repository."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from forge.infrastructure.persistence.models import ORMOrder, ORMOrderItem


class SQLAlchemyOrderRepository:
    """订单数据库访问封装。"""

    @staticmethod
    async def list_orders(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        total_query = select(func.count(ORMOrder.id))
        total = (await db.execute(total_query)).scalar_one()

        query = (
            select(ORMOrder)
            .options(selectinload(ORMOrder.items))
            .order_by(ORMOrder.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(query)
        orders = result.scalars().all()

        return {
            "items": [
                {
                    "id": str(o.id),
                    "order_number": o.order_number,
                    "user_id": str(o.user_id),
                    "subtotal": float(o.subtotal),
                    "tax": float(o.tax),
                    "shipping_cost": float(o.shipping_cost),
                    "discount": float(o.discount),
                    "total": float(o.total),
                    "currency": o.currency,
                    "status": o.status,
                    "shipping_address": o.shipping_address,
                    "tracking_number": o.tracking_number,
                    "created_at": o.created_at.isoformat() if o.created_at else None,
                    "items": [
                        {
                            "id": str(i.id),
                            "product_id": str(i.product_id),
                            "name": i.name,
                            "sku": i.sku,
                            "price": float(i.price),
                            "quantity": i.quantity,
                            "image": i.image,
                        }
                        for i in o.items
                    ] if o.items else [],
                }
                for o in orders
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @staticmethod
    async def count(db: AsyncSession) -> int:
        result = await db.execute(select(func.count(ORMOrder.id)))
        return result.scalar_one()

    @staticmethod
    async def count_by_status(db: AsyncSession) -> dict:
        stmt = (
            select(ORMOrder.status, func.count(ORMOrder.id))
            .group_by(ORMOrder.status)
        )
        result = await db.execute(stmt)
        rows = result.all()
        return {row[0]: row[1] for row in rows}
