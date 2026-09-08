"""Admin Orders API - 订单列表 / 详情 / 发货（订单置 shipped 并登记运单）。

- GET   /api/admin/v1/orders           分页列表（含软删订单亦可见，便于运营）
- GET   /api/admin/v1/orders/{order_number}  详情（含 items / 支付字段）
- POST  /api/admin/v1/orders/{order_number}/ship  发货：confirmed/processing/pending -> shipped
- POST  /api/admin/v1/orders/{order_number}/cancel  后台取消（未发货订单，回补库存）
"""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from forge.api.errors import APIError, ErrorCode
from forge.infrastructure.persistence.models import ORMOrder, ORMShipment
from forge.infrastructure.persistence.repositories.order_repo import (
    SQLAlchemyCustomerOrderRepository,
    SQLAlchemyOrderRepository,
    _order_to_dict,
)
from forge.main.dependencies import get_db
from forge.main.rbac import require_permission

router = APIRouter()


class AdminShipPackage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    carrier: str = Field(min_length=1, max_length=100)
    tracking_number: str = Field(min_length=1, max_length=500)


class AdminShipRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    packages: list[AdminShipPackage] = Field(min_length=1, max_length=20)


def _new_shipment(order: ORMOrder, pkg: AdminShipPackage) -> ORMShipment:
    """为订单登记一个运单包裹（mock tracking url，后续接入真实物流商可替换）。"""
    # ORMShipment 时间列均为 DateTime(timezone=False)，须传 naive UTC
    now = datetime.now(UTC).replace(tzinfo=None)
    address = cast(dict[str, Any], order.shipping_address or {})
    destination = ", ".join(
        str(x)
        for x in [
            address.get("line1"),
            address.get("city"),
            address.get("country"),
        ]
        if x
    )
    return ORMShipment(
        id=uuid4(),
        order_id=order.id,
        supplier_id="MANUAL",
        tracking_number=pkg.tracking_number,
        carrier=pkg.carrier,
        tracking_url=f"https://mock-track.example/{pkg.tracking_number}",
        status="shipped",
        origin="CN Warehouse",
        destination=destination or "N/A",
        events=[
            {
                "status": "shipped",
                "label": "Order shipped",
                "time": now.isoformat(),
            }
        ],
        created_at=now,
        updated_at=now,
    )


class AdminCancelRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    reason: str | None = Field(default=None, max_length=2000)


class AdminReviewRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    approved: bool
    reason: str | None = Field(default=None, max_length=2000)
    reviewed_by: str | None = Field(default=None, max_length=100)


class AdminProcureRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    supplier_id: str = Field(min_length=1, max_length=255)
    supplier_sku: str | None = Field(default=None, max_length=255)
    cost: float | None = Field(default=None, ge=0)


class AdminRefundRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    reason: str | None = Field(default=None, max_length=2000)


async def _admin_order_or_404(db: AsyncSession, order_number: str) -> ORMOrder:
    order = (
        await db.execute(
            select(ORMOrder).where(ORMOrder.order_number == order_number).options(selectinload(ORMOrder.items))
        )
    ).scalar_one_or_none()
    if order is None:
        raise APIError(ErrorCode.ORDER_NOT_FOUND, message="Order does not exist.")
    return order


def _shipment_dict(s: ORMShipment) -> dict[str, Any]:
    """Admin 视图所需的运单字段（一单多包时每包一条）。"""
    return {
        "id": str(s.id),
        "tracking_number": s.tracking_number,
        "carrier": s.carrier,
        "tracking_url": s.tracking_url,
        "status": s.status,
        "origin": s.origin,
        "destination": s.destination,
        "events": s.events or [],
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


def _admin_timeline(order: ORMOrder) -> list[dict[str, Any]]:
    """订单时间轴：由时间线字段推导关键节点（created/paid/confirmed/shipped/delivered/cancelled/refunded）。

    review / procure 无独立时间戳字段，不作为时间轴节点（状态卡片已展示）。
    """
    events: list[dict[str, Any]] = [
        {
            "status": "pending",
            "label": "Order placed",
            "time": order.created_at.isoformat() if order.created_at else None,
        }
    ]
    if order.paid_at:
        events.append({"status": "paid", "label": "Payment confirmed", "time": order.paid_at.isoformat()})
    if order.confirmed_at:
        events.append({"status": "confirmed", "label": "Order confirmed", "time": order.confirmed_at.isoformat()})
    if order.shipped_at:
        events.append({"status": "shipped", "label": "Order shipped", "time": order.shipped_at.isoformat()})
    if order.delivered_at:
        events.append({"status": "delivered", "label": "Delivered", "time": order.delivered_at.isoformat()})
    if order.status == "cancelled":
        cancelled_time = order.updated_at.isoformat() if order.updated_at else None
        events.append({"status": "cancelled", "label": "Order cancelled", "time": cancelled_time})
    if order.status == "refunded":
        refunded_time = order.updated_at.isoformat() if order.updated_at else None
        events.append({"status": "refunded", "label": "Refunded", "time": refunded_time})
    return events


@router.get("/")
async def list_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None, max_length=200),
    admin: dict[str, object] = Depends(require_permission("orders", "view")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    repo = SQLAlchemyOrderRepository()
    normalized_status = status.strip().lower() if status and status.strip() else None
    normalized_search = search.strip() if search and search.strip() else None
    return await repo.list_orders(
        db,
        page=page,
        page_size=page_size,
        status=normalized_status,
        search=normalized_search,
    )


@router.get("/export")
async def export_orders(
    status: str | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None, max_length=200),
    admin: dict[str, object] = Depends(require_permission("orders", "view")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """导出当前筛选条件下的订单 CSV（UTF-8 BOM，Excel 友好）。"""
    repo = SQLAlchemyOrderRepository()
    normalized_status = status.strip().lower() if status and status.strip() else None
    normalized_search = search.strip() if search and search.strip() else None
    orders = await repo.list_all_orders(db, status=normalized_status, search=normalized_search)

    columns = [
        "order_number",
        "user_id",
        "status",
        "currency",
        "subtotal",
        "tax",
        "shipping_cost",
        "discount",
        "total",
        "tracking_number",
        "item_count",
        "created_at",
    ]
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for o in orders:
        writer.writerow(
            {
                "order_number": o.order_number,
                "user_id": str(o.user_id),
                "status": o.status,
                "currency": o.currency,
                "subtotal": float(o.subtotal),
                "tax": float(o.tax),
                "shipping_cost": float(o.shipping_cost),
                "discount": float(o.discount),
                "total": float(o.total),
                "tracking_number": o.tracking_number or "",
                "item_count": len(o.items or []),
                "created_at": o.created_at.isoformat() if o.created_at else "",
            }
        )
    content = "\ufeff" + buffer.getvalue()
    filename = f"orders_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        content=content.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{order_number}")
async def get_order_detail(
    order_number: str,
    admin: dict[str, object] = Depends(require_permission("orders", "view")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    order = await _admin_order_or_404(db, order_number)
    data = _order_to_dict(order)
    shipments = await SQLAlchemyCustomerOrderRepository.list_shipments(db, cast(UUID, order.id))
    data["shipments"] = [_shipment_dict(s) for s in shipments]
    data["timeline"] = _admin_timeline(order)
    return data


@router.post("/{order_number}/ship")
async def ship_order(
    order_number: str,
    payload: AdminShipRequest,
    admin: dict[str, object] = Depends(require_permission("orders", "manage")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """发货（支持一单多包裹）：为每个包裹登记一条 shipment，订单置 shipped。

    - 未发货订单（pending/confirmed/processing）：置 shipped 并登记全部包裹
    - 已 shipped 订单：仅追加登记新包裹（分批补发场景），不重复改变订单状态
    """
    order = await _admin_order_or_404(db, order_number)
    was_shipped = order.status in {"shipped", "delivered"}
    if not was_shipped:
        order = await SQLAlchemyCustomerOrderRepository.mark_shipped(
            db, order, tracking_number=payload.packages[0].tracking_number, carrier=payload.packages[0].carrier
        )
    for pkg in payload.packages:
        db.add(_new_shipment(order, pkg))
    await db.commit()
    await db.refresh(order, attribute_names=["items"])
    return _order_to_dict(order)


@router.post("/{order_number}/cancel")
async def admin_cancel_order(
    order_number: str,
    payload: AdminCancelRequest,
    admin: dict[str, object] = Depends(require_permission("orders", "manage")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    order = await _admin_order_or_404(db, order_number)
    cancelled = await SQLAlchemyCustomerOrderRepository.cancel_order(db, order, payload.reason)
    await db.commit()
    await db.refresh(cancelled, attribute_names=["items"])
    return _order_to_dict(cancelled)


@router.post("/{order_number}/review")
async def review_order(
    order_number: str,
    payload: AdminReviewRequest,
    admin: dict[str, object] = Depends(require_permission("orders", "manage")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """审核：confirmed -> processing（通过）；confirmed -> cancelled（拒绝，回补库存）。"""
    order = await _admin_order_or_404(db, order_number)
    reviewed = await SQLAlchemyCustomerOrderRepository.admin_review_order(
        db,
        order,
        approved=payload.approved,
        reason=payload.reason,
        reviewed_by=payload.reviewed_by,
    )
    await db.commit()
    await db.refresh(reviewed, attribute_names=["items"])
    return _order_to_dict(reviewed)


@router.post("/{order_number}/procure")
async def procure_order(
    order_number: str,
    payload: AdminProcureRequest,
    admin: dict[str, object] = Depends(require_permission("orders", "manage")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """推送采购：processing/procure_failed -> procuring，登记采购信息。"""
    order = await _admin_order_or_404(db, order_number)
    procured = await SQLAlchemyCustomerOrderRepository.admin_procure_order(
        db,
        order,
        supplier_id=payload.supplier_id,
        supplier_sku=payload.supplier_sku,
        cost=payload.cost,
    )
    await db.commit()
    await db.refresh(procured, attribute_names=["items"])
    return _order_to_dict(procured)


@router.post("/{order_number}/refund")
async def refund_order(
    order_number: str,
    payload: AdminRefundRequest,
    admin: dict[str, object] = Depends(require_permission("orders", "manage")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """整单退款（仅未发货订单）：-> refunded，回补库存。

    已发货/已完成订单的退款（原路退回、退款单）属后续迭代范围。
    """
    order = await _admin_order_or_404(db, order_number)
    refunded = await SQLAlchemyCustomerOrderRepository.admin_refund_order(db, order, payload.reason)
    await db.commit()
    await db.refresh(refunded, attribute_names=["items"])
    return _order_to_dict(refunded)
