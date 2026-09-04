"""C-end Orders API - 客户订单（创建/列表/详情/取消/物流占位）。

- 依赖 C 端 JWT（auth.get_current_user），订单严格按当前用户隔离
- 前端契约（portal-web useApi / stores/order）：
  GET    /orders                    -> {items, total, page, page_size}（?status= 过滤）
  POST   /orders                    -> order（body: {items:[{product_id,quantity}], shipping_address, payment_method?}）
  GET    /orders/{order_number}     -> order detail（含 items）
  POST   /orders/{order_number}/cancel -> order
  GET    /orders/{order_number}/tracking  -> {order_number, status, events}
  GET    /orders/{order_number}/shipments -> [shipment, ...]
- 支付本期占位：创建订单即 status=pending，真实网关另开阶段
"""

from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from forge.api.errors import APIError, ErrorCode
from forge.api.v1.auth import get_current_user
from forge.infrastructure.persistence.models import ORMOrder, ORMShipment
from forge.infrastructure.persistence.repositories.order_repo import (
    SQLAlchemyCustomerOrderRepository,
    _order_to_dict,
)
from forge.infrastructure.persistence.repositories.user_repo import SQLAlchemyUserRepository
from forge.main.dependencies import get_db

router = APIRouter(prefix="/orders", tags=["C-end Orders"])

VALID_ORDER_STATUSES = {"pending", "confirmed", "processing", "shipped", "delivered", "cancelled"}


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class OrderCreateItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0)


class OrderCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    items: list[OrderCreateItem] = Field(min_length=1)
    shipping_address: dict[str, Any] | None = None
    payment_method: str | None = Field(default=None, max_length=50)


class OrderCancel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    reason: str | None = Field(default=None, max_length=2000)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _current_owner_id(
    claims: dict[str, object],
    db: AsyncSession,
) -> UUID:
    """按 token email 反查 users.id；用户不存在视为未授权。"""
    email = str(claims.get("sub") or "")
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="UNAUTHORIZED")
    user = await SQLAlchemyUserRepository.get_by_email(db, email)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="UNAUTHORIZED")
    return cast(UUID, user.id)


async def _owned_order_or_404(db: AsyncSession, owner_id: UUID, order_number: str) -> ORMOrder:
    """按单号取当前用户订单，不存在统一 404（不泄露他人订单是否存在）。"""
    order = await SQLAlchemyCustomerOrderRepository.get_by_user_and_number(db, owner_id, order_number)
    if order is None:
        raise APIError(ErrorCode.ORDER_NOT_FOUND, message="Order does not exist.")
    return order


def _shipment_dict(shipment: ORMShipment) -> dict[str, Any]:
    return {
        "id": str(shipment.id),
        "order_id": str(shipment.order_id),
        "supplier_id": shipment.supplier_id,
        "tracking_number": shipment.tracking_number,
        "carrier": shipment.carrier,
        "tracking_url": shipment.tracking_url,
        "status": shipment.status,
        "estimated_delivery": shipment.estimated_delivery.isoformat() if shipment.estimated_delivery else None,
        "actual_delivery": shipment.actual_delivery.isoformat() if shipment.actual_delivery else None,
        "origin": shipment.origin,
        "destination": shipment.destination,
        "events": shipment.events or [],
        "notes": shipment.notes,
        "created_at": shipment.created_at.isoformat() if shipment.created_at else None,
        "updated_at": shipment.updated_at.isoformat() if shipment.updated_at else None,
    }


def _tracking_events(order: ORMOrder) -> list[dict[str, Any]]:
    """本期由订单状态推导 timeline；发货后以 shipments 事件为准。"""
    created_at = order.created_at.isoformat() if order.created_at else None
    updated_at = order.updated_at.isoformat() if order.updated_at else None
    events = [
        {"status": "pending", "label": "Order placed", "time": created_at},
    ]
    if order.status in {"confirmed", "processing", "shipped", "delivered"}:
        events.append(
            {"status": "confirmed", "label": "Order confirmed", "time": updated_at}
        )
    if order.status in {"shipped", "delivered"}:
        events.append({"status": "shipped", "label": "Order shipped", "time": None})
    if order.status == "delivered":
        events.append({"status": "delivered", "label": "Delivered", "time": None})
    if order.status == "cancelled":
        events.append(
            {"status": "cancelled", "label": "Order cancelled", "time": updated_at}
        )
    return events


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("")
async def list_orders(
    user_claims: dict[str, object] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
) -> dict[str, Any]:
    """当前用户订单分页列表；?status= 可选过滤。"""
    owner_id = await _current_owner_id(user_claims, db)
    if status_filter and status_filter not in VALID_ORDER_STATUSES:
        raise APIError(ErrorCode.VALIDATION_ERROR, message=f"Invalid order status: {status_filter}")
    result = await SQLAlchemyCustomerOrderRepository.list_by_user(
        db, owner_id, page=page, page_size=page_size, status=status_filter
    )
    return cast(dict[str, Any], result)


@router.post("")
async def create_order(
    payload: OrderCreate,
    user_claims: dict[str, object] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """创建订单：服务端计价快照 + 扣减库存；支付本期占位。"""
    owner_id = await _current_owner_id(user_claims, db)
    lines: list[dict[str, object]] = [{"product_id": it.product_id, "quantity": it.quantity} for it in payload.items]
    order = await SQLAlchemyCustomerOrderRepository.create_order(
        db,
        owner_id,
        lines,
        payload.shipping_address,
    )
    await db.commit()
    await db.refresh(order, attribute_names=["items"])
    return _order_to_dict(order)


@router.get("/{order_number}")
async def get_order_detail(
    order_number: str,
    user_claims: dict[str, object] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    owner_id = await _current_owner_id(user_claims, db)
    order = await _owned_order_or_404(db, owner_id, order_number)
    return _order_to_dict(order)


@router.post("/{order_number}/cancel")
async def cancel_order(
    order_number: str,
    payload: OrderCancel,
    user_claims: dict[str, object] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """取消未发货订单并回补库存。"""
    owner_id = await _current_owner_id(user_claims, db)
    order = await _owned_order_or_404(db, owner_id, order_number)
    cancelled = await SQLAlchemyCustomerOrderRepository.cancel_order(db, order, payload.reason)
    await db.commit()
    await db.refresh(cancelled, attribute_names=["items"])
    return _order_to_dict(cancelled)


@router.get("/{order_number}/tracking")
async def get_order_tracking(
    order_number: str,
    user_claims: dict[str, object] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    owner_id = await _current_owner_id(user_claims, db)
    order = await _owned_order_or_404(db, owner_id, order_number)
    return {
        "order_number": order.order_number,
        "status": order.status,
        "tracking_number": order.tracking_number,
        "events": _tracking_events(order),
    }


@router.get("/{order_number}/shipments")
async def list_order_shipments(
    order_number: str,
    user_claims: dict[str, object] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """订单物流列表；order_number 兼容订单号与订单 UUID。"""
    owner_id = await _current_owner_id(user_claims, db)
    order = await _owned_order_or_404(db, owner_id, order_number)
    shipments = await SQLAlchemyCustomerOrderRepository.list_shipments(db, cast(UUID, order.id))
    return [_shipment_dict(s) for s in shipments]
