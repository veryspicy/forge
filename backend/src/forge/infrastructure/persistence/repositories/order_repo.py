"""Order — SQLAlchemy Repository."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from forge.api.errors import APIError, ErrorCode
from forge.infrastructure.persistence.models import ORMOrder, ORMOrderItem, ORMProduct, ORMShipment


class SQLAlchemyOrderRepository:
    """订单数据库访问封装。"""

    @staticmethod
    async def list_orders(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, object]:
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
                    ]
                    if o.items
                    else [],
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
    async def count_by_status(db: AsyncSession) -> dict[str, object]:
        stmt = select(ORMOrder.status, func.count(ORMOrder.id)).group_by(ORMOrder.status)
        result = await db.execute(stmt)
        rows = result.all()
        return {row[0]: row[1] for row in rows}


# ---------------------------------------------------------------------------
# C-end commerce (customer orders)
# ---------------------------------------------------------------------------

_CANCELLABLE_STATUSES = {"pending", "confirmed", "processing"}
_FREE_SHIPPING_THRESHOLD = 50
_FLAT_SHIPPING = 5
_DEFAULT_CURRENCY = "USD"


def _order_to_dict(order: ORMOrder) -> dict[str, object]:
    return {
        "id": str(order.id),
        "order_number": order.order_number,
        "user_id": str(order.user_id),
        "subtotal": float(order.subtotal),
        "tax": float(order.tax),
        "shipping_cost": float(order.shipping_cost),
        "discount": float(order.discount),
        "total": float(order.total),
        "currency": order.currency,
        "status": order.status,
        "payment_intent_id": order.payment_intent_id,
        "tracking_number": order.tracking_number,
        "shipping_address": order.shipping_address,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "updated_at": order.updated_at.isoformat() if order.updated_at else None,
        "items": [
            {
                "id": str(i.id),
                "product_id": int(i.product_id) if i.product_id is not None else None,
                "name": i.name,
                "sku": i.sku,
                "price": float(i.price),
                "quantity": i.quantity,
                "image": i.image,
            }
            for i in order.items
        ],
    }


class SQLAlchemyCustomerOrderRepository:
    """Customer-scoped order operations (list / detail / create / cancel)."""

    @staticmethod
    def _now() -> datetime:
        # Table columns are TIMESTAMP WITHOUT TIME ZONE; naive UTC avoids asyncpg aware/naive mixing.
        return datetime.now(UTC).replace(tzinfo=None)

    @staticmethod
    def _first_image(product: ORMProduct) -> str | None:
        images: list[Any] = cast(list[Any], product.images or [])
        if not images:
            return None
        first = images[0]
        if isinstance(first, dict):
            url = first.get("key") or first.get("url")
            return str(url) if url else None
        return str(first) if isinstance(first, str) else None

    @staticmethod
    async def list_by_user(
        db: AsyncSession,
        user_id: UUID,
        page: int = 1,
        page_size: int = 10,
        status: str | None = None,
    ) -> dict[str, object]:
        stmt = (
            select(ORMOrder)
            .where(ORMOrder.user_id == user_id)
            .options(selectinload(ORMOrder.items))
            .order_by(ORMOrder.created_at.desc())
        )
        count_stmt = select(func.count()).select_from(ORMOrder).where(ORMOrder.user_id == user_id)
        if status:
            stmt = stmt.where(ORMOrder.status == status)
            count_stmt = count_stmt.where(ORMOrder.status == status)
        total = int((await db.execute(count_stmt)).scalar_one())
        rows = (
            (await db.execute(stmt.offset((page - 1) * page_size).limit(page_size)))
            .scalars()
            .all()
        )
        return {
            "items": [_order_to_dict(o) for o in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @staticmethod
    async def get_by_user_and_number(
        db: AsyncSession,
        user_id: UUID,
        order_number: str,
    ) -> ORMOrder | None:
        return (
            await db.execute(
                select(ORMOrder)
                .where(ORMOrder.user_id == user_id, ORMOrder.order_number == order_number)
                .options(selectinload(ORMOrder.items))
            )
        ).scalar_one_or_none()

    @staticmethod
    async def create_order(
        db: AsyncSession,
        user_id: UUID,
        lines: list[dict[str, object]],
        shipping_address: dict[str, object] | None,
    ) -> ORMOrder:
        """Create an order with server-side price snapshots and inventory deduction.

        Raises:
            APIError: PRODUCT_UNAVAILABLE / INSUFFICIENT_STOCK / ORDER_EMPTY on validation failure.
        """
        if not lines:
            raise APIError(ErrorCode.ORDER_EMPTY, message="Order has no items.")
        product_ids = [cast(int, line["product_id"]) for line in lines]
        products = (
            (
                await db.execute(
                    select(ORMProduct).where(ORMProduct.id.in_(product_ids)).with_for_update()
                )
            )
            .scalars()
            .all()
        )
        product_map: dict[int, ORMProduct] = {cast(int, p.id): p for p in products}
        quantity_map: dict[int, int] = {}
        for line in lines:
            pid = cast(int, line["product_id"])
            quantity = cast(int, line["quantity"])
            if quantity <= 0:
                raise APIError(ErrorCode.VALIDATION_ERROR, message="Item quantity must be positive.")
            quantity_map[pid] = quantity_map.get(pid, 0) + quantity

        for pid, quantity in quantity_map.items():
            product = product_map.get(pid)
            if product is None or (product.status or "").lower() != "active":
                raise APIError(
                    ErrorCode.PRODUCT_UNAVAILABLE,
                    message=f"Product {pid} is not available for purchase.",
                )
            if product.inventory is not None and product.inventory < quantity:
                raise APIError(
                    ErrorCode.INSUFFICIENT_STOCK,
                    message=f"Product '{product.name}' has insufficient stock.",
                )

        now = SQLAlchemyCustomerOrderRepository._now()
        order_number = SQLAlchemyCustomerOrderRepository._generate_order_number()
        subtotal = Decimal("0")
        order = ORMOrder(
            id=uuid4(),
            order_number=order_number,
            user_id=user_id,
            subtotal=Decimal("0"),
            tax=Decimal("0"),
            shipping_cost=Decimal("0"),
            discount=Decimal("0"),
            total=Decimal("0"),
            currency=_DEFAULT_CURRENCY,
            status="pending",
            shipping_address=shipping_address,
            created_at=now,
            updated_at=now,
        )
        db.add(order)
        await db.flush()

        items: list[ORMOrderItem] = []
        for pid in quantity_map:
            product = product_map[pid]
            quantity = quantity_map[pid]
            unit_price = Decimal(str(product.price))
            item = ORMOrderItem(
                id=uuid4(),
                order_id=order.id,
                product_id=product.id,
                name=product.name,
                sku=product.sku or "",
                price=unit_price,
                quantity=quantity,
                image=SQLAlchemyCustomerOrderRepository._first_image(product),
            )
            db.add(item)
            items.append(item)
            subtotal += unit_price * quantity
            if product.inventory is not None:
                product.inventory = cast(Any, product.inventory - quantity)

        shipping_cost = (
            Decimal("0")
            if subtotal > _FREE_SHIPPING_THRESHOLD
            else Decimal(str(_FLAT_SHIPPING))
        )
        order.subtotal = cast(Any, subtotal)
        order.shipping_cost = cast(Any, shipping_cost)
        order.total = cast(Any, subtotal + shipping_cost)
        await db.flush()
        return order

    @staticmethod
    async def cancel_order(db: AsyncSession, order: ORMOrder, reason: str | None = None) -> ORMOrder:
        """Cancel a customer order and restore inventory. Cancellable before shipment."""
        if order.status not in _CANCELLABLE_STATUSES:
            raise APIError(
                ErrorCode.ORDER_NOT_CANCELLABLE,
                message=f"Order cannot be cancelled in state '{order.status}'.",
            )
        order.status = cast(Any, "cancelled")
        order.updated_at = cast(Any, SQLAlchemyCustomerOrderRepository._now())
        review = dict(order.review_status or {})
        review["cancelled_by"] = "customer"
        review["cancelled_reason"] = reason or ""
        order.review_status = cast(Any, review)
        await db.flush()

        item_rows = order.items
        if item_rows:
            product_ids = [cast(int, i.product_id) for i in item_rows if i.product_id is not None]
            if product_ids:
                products = (
                    (
                        await db.execute(
                            select(ORMProduct).where(ORMProduct.id.in_(product_ids)).with_for_update()
                        )
                    )
                    .scalars()
                    .all()
                )
                product_map = {cast(int, p.id): p for p in products}
                for i in item_rows:
                    product = product_map.get(cast(int, i.product_id)) if i.product_id is not None else None
                    if product is not None and product.inventory is not None:
                        product.inventory = cast(Any, product.inventory + i.quantity)
                await db.flush()
        return order

    @staticmethod
    async def list_shipments(db: AsyncSession, order_id: UUID) -> list[ORMShipment]:
        rows = (
            await db.execute(
                select(ORMShipment)
                .where(ORMShipment.order_id == order_id)
                .order_by(ORMShipment.created_at.asc())
            )
        ).scalars().all()
        return list(rows)

    @staticmethod
    def _generate_order_number() -> str:
        stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        return f"FG{stamp}{secrets.token_hex(3).upper()}"
