"""Admin Orders API - 订单列表 / 详情 / 发货（订单置 shipped 并登记运单）。

- GET   /api/admin/v1/orders           分页列表（含软删订单亦可见，便于运营）
- GET   /api/admin/v1/orders/{order_number}  详情（含 items / 支付字段）
- POST  /api/admin/v1/orders/{order_number}/ship  发货：confirmed/processing/pending -> shipped
- POST  /api/admin/v1/orders/{order_number}/cancel  后台取消（未发货订单，回补库存）
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

from fastapi import APIRouter, Depends, Query
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


class AdminShipRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    carrier: str = Field(min_length=1, max_length=100)
    tracking_number: str = Field(min_length=1, max_length=500)


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


@router.get("/{order_number}")
async def get_order_detail(
    order_number: str,
    admin: dict[str, object] = Depends(require_permission("orders", "view")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    order = await _admin_order_or_404(db, order_number)
    return _order_to_dict(order)


@router.post("/{order_number}/ship")
async def ship_order(
    order_number: str,
    payload: AdminShipRequest,
    admin: dict[str, object] = Depends(require_permission("orders", "manage")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """发货：订单置 shipped，同时登记 shipment 运单记录。"""
    order = await _admin_order_or_404(db, order_number)
    shipped = await SQLAlchemyCustomerOrderRepository.mark_shipped(
        db, order, tracking_number=payload.tracking_number, carrier=payload.carrier
    )
    # 登记运单记录（mock tracking url，后续接入真实物流商可替换）
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
    shipment = ORMShipment(
        id=__import__("uuid").uuid4(),
        order_id=order.id,
        supplier_id="MANUAL",
        tracking_number=payload.tracking_number,
        carrier=payload.carrier,
        tracking_url=f"https://mock-track.example/{payload.tracking_number}",
        status="shipped",
        origin="CN Warehouse",
        destination=destination or "N/A",
        events=[
            {
                "status": "shipped",
                "label": "Order shipped",
                "time": datetime.now(UTC).isoformat(),
            }
        ],
    )
    db.add(shipment)
    await db.commit()
    await db.refresh(shipped, attribute_names=["items"])
    return _order_to_dict(shipped)


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
