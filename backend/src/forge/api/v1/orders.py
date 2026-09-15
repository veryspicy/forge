"""C-end Orders API - 客户订单（创建/列表/详情/取消/支付/确认收货/删除/评价）。

- 依赖 C 端 JWT（auth.get_current_user），订单严格按当前用户隔离
- 前端契约（portal-web useApi / stores/order）：
  GET    /orders                    -> {items, total, page, page_size}（?status= 过滤，软删不可见）
  POST   /orders                    -> order（body: {items:[{product_id,quantity}], shipping_address, payment_method}）
  GET    /orders/{order_number}     -> order detail（含 items 与支付/状态时间线字段）
  POST   /orders/{order_number}/cancel -> order
  POST   /orders/{order_number}/pay -> order（body: {payment_method, card{...}?, save_card?}；mock 网关确认）
  POST   /orders/{order_number}/confirm-receipt -> order（shipped -> delivered，订单完结）
  POST   /orders/{order_number}/shipping-address -> order（仅未发货可修改收货地址）
  DELETE /orders/{order_number}     -> {deleted: true}（仅 delivered/cancelled 可软删归档）
  GET    /orders/{order_number}/tracking  -> {order_number, status, events}
  GET    /orders/{order_number}/shipments -> [shipment, ...]
- 支付状态机：pending(unpaid) -> pay -> confirmed(paid) -> shipped -> delivered(客户确认收货完结)
- 删除规则（行业对齐）：仅已完结 delivered 或已取消 cancelled 的订单允许从列表归档
"""

from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from forge.api.errors import APIError, ErrorCode
from forge.api.v1.auth import get_current_user
from forge.application.services.payment_gateway import get_payment_gateway
from forge.infrastructure.persistence.models import ORMOrder, ORMShipment
from forge.infrastructure.persistence.repositories.order_repo import (
    SQLAlchemyCustomerOrderRepository,
    _order_to_dict,
)
from forge.infrastructure.persistence.repositories.user_repo import SQLAlchemyUserRepository
from forge.main.dependencies import get_db

router = APIRouter(prefix="/orders", tags=["C-end Orders"])

VALID_ORDER_STATUSES = {
    "pending",
    "confirmed",
    "processing",
    "procuring",
    "procure_failed",
    "shipped",
    "delivered",
    "cancelled",
    "refunded",
}
VALID_PAYMENT_METHODS = {"card", "paypal"}


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


class CardPay(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str | None = Field(default=None, max_length=200)
    number: str | None = Field(default=None, max_length=32)
    expiry: str | None = Field(default=None, max_length=10)
    cvv: str | None = Field(default=None, max_length=10)


class OrderPay(BaseModel):
    model_config = ConfigDict(extra="ignore")

    payment_method: str = Field(min_length=1, max_length=50)
    card: CardPay | None = None


class OrderShippingAddress(BaseModel):
    model_config = ConfigDict(extra="ignore")

    shipping_address: dict[str, Any] = Field(min_length=1)


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
    """由订单状态与时间线字段推导 events；发货后以 shipments 事件为准。"""
    events: list[dict[str, Any]] = [
        {
            "status": "pending",
            "label": "Order placed",
            "time": order.created_at.isoformat() if order.created_at else None,
        },
    ]
    if order.paid_at or order.confirmed_at:
        events.append(
            {
                "status": "paid",
                "label": "Payment confirmed",
                "time": (order.paid_at or order.confirmed_at).isoformat()
                if (order.paid_at or order.confirmed_at)
                else None,
            }
        )
    if order.status in {"confirmed", "processing", "shipped", "delivered"} and not order.paid_at:
        events.append(
            {
                "status": "confirmed",
                "label": "Order confirmed",
                "time": order.confirmed_at.isoformat() if order.confirmed_at else None,
            }
        )
    if order.status in {"shipped", "delivered"}:
        events.append(
            {
                "status": "shipped",
                "label": "Order shipped",
                "time": order.shipped_at.isoformat() if order.shipped_at else None,
            }
        )
    if order.status == "delivered":
        events.append(
            {
                "status": "delivered",
                "label": "Delivered",
                "time": order.delivered_at.isoformat() if order.delivered_at else None,
            }
        )
    if order.status == "cancelled":
        cancelled_time = order.updated_at.isoformat() if order.updated_at else None
        events.append({"status": "cancelled", "label": "Order cancelled", "time": cancelled_time})
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
    """创建订单：服务端计价快照 + 扣减库存；状态 pending(unpaid)，随后经 pay 接口支付。"""
    owner_id = await _current_owner_id(user_claims, db)
    lines: list[dict[str, object]] = [{"product_id": it.product_id, "quantity": it.quantity} for it in payload.items]
    order = await SQLAlchemyCustomerOrderRepository.create_order(
        db,
        owner_id,
        lines,
        payload.shipping_address,
        payment_method=payload.payment_method,
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


async def _lock_order_by_number(db: AsyncSession, order_number: str) -> ORMOrder:
    """行锁重取订单，防止支付/状态流转并发竞态。"""
    row = (
        await db.execute(select(ORMOrder).where(ORMOrder.order_number == order_number).with_for_update())
    ).scalar_one_or_none()
    if row is None:
        raise APIError(ErrorCode.ORDER_NOT_FOUND, message="Order does not exist.")
    return row


@router.post("/{order_number}/pay")
async def pay_order(
    order_number: str,
    payload: OrderPay,
    user_claims: dict[str, object] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """支付订单：mock 网关模拟收单成功后订单置 paid/confirmed。

    - 仅 pending 且未支付订单可支付；幂等：已支付订单直接返回现状
    - 测试卡：4242 4242 4242 4242 成功；4000 0000 0000 0002 拒绝
    """
    owner_id = await _current_owner_id(user_claims, db)
    order = await _owned_order_or_404(db, owner_id, order_number)
    if order.payment_status == "paid":
        return _order_to_dict(order)
    method = (payload.payment_method or "").lower()
    if method not in VALID_PAYMENT_METHODS:
        raise APIError(
            ErrorCode.PAYMENT_METHOD_UNSUPPORTED,
            message=f"Payment method '{method}' is not supported.",
        )
    gateway = get_payment_gateway()
    intent = await gateway.create_payment_intent(
        cast(str, order.order_number),
        cast(Any, order.total),
        cast(str, order.currency or "USD"),
        method,
    )
    card = payload.card.model_dump(exclude_none=True) if payload.card else None
    result = await gateway.confirm(intent.id, card=card)
    if not result.success:
        raise APIError(
            ErrorCode.PAYMENT_DECLINED,
            message=result.error_message or "Payment was declined.",
        )
    locked = await _lock_order_by_number(db, order_number)
    if locked.user_id != owner_id:
        raise APIError(ErrorCode.ORDER_NOT_FOUND, message="Order does not exist.")
    paid = await SQLAlchemyCustomerOrderRepository.mark_paid(db, locked, method, payment_intent_id=intent.id)
    await db.commit()
    await db.refresh(paid, attribute_names=["items"])
    return _order_to_dict(paid)


@router.post("/{order_number}/confirm-receipt")
async def confirm_receipt(
    order_number: str,
    user_claims: dict[str, object] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """确认收货：shipped -> delivered，订单完结，此后可评价商品。"""
    owner_id = await _current_owner_id(user_claims, db)
    order = await _owned_order_or_404(db, owner_id, order_number)
    confirmed = await SQLAlchemyCustomerOrderRepository.confirm_receipt(db, order)
    await db.commit()
    await db.refresh(confirmed, attribute_names=["items"])
    return _order_to_dict(confirmed)


@router.post("/{order_number}/shipping-address")
async def update_order_shipping_address(
    order_number: str,
    payload: OrderShippingAddress,
    user_claims: dict[str, object] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """修改收货地址：仅未发货订单（pending/confirmed/processing）允许。"""
    owner_id = await _current_owner_id(user_claims, db)
    order = await _owned_order_or_404(db, owner_id, order_number)
    updated = await SQLAlchemyCustomerOrderRepository.update_shipping_address(db, order, payload.shipping_address)
    await db.commit()
    await db.refresh(updated, attribute_names=["items"])
    return _order_to_dict(updated)


@router.delete("/{order_number}")
async def delete_order(
    order_number: str,
    user_claims: dict[str, object] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """删除（归档）订单：仅 delivered/cancelled 允许，软删后客户列表不可见。"""
    owner_id = await _current_owner_id(user_claims, db)
    order = await _owned_order_or_404(db, owner_id, order_number)
    await SQLAlchemyCustomerOrderRepository.soft_delete_order(db, order)
    await db.commit()
    return {"deleted": "true", "order_number": order_number}


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
