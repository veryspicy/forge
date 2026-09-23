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
from forge.infrastructure.persistence.models import ORMOrder, ORMShipment, ORMSupplier
from forge.infrastructure.persistence.repositories.order_repo import (
    SQLAlchemyCustomerOrderRepository,
    SQLAlchemyOrderRepository,
    _order_fulfillment_mode,
    _order_to_dict,
)
from forge.infrastructure.persistence.repositories.return_repo import SQLAlchemyReturnRepository
from forge.infrastructure.persistence.repositories.site_profile_repo import SQLAlchemySiteProfileRepository
from forge.main.dependencies import get_db
from forge.main.rbac import require_permission

router = APIRouter()


class AdminShipPackage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    carrier: str = Field(min_length=1, max_length=100)
    tracking_number: str = Field(min_length=1, max_length=500)
    # 代发包裹可指定供应商（不传则回落 "MANUAL"）
    supplier_id: str | None = Field(default=None, max_length=255)


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
        supplier_id=(pkg.supplier_id or "").strip() or "MANUAL",
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
    """取消订单（履约终止）：refund=None 表示有可退余额时自动同时退款。"""

    model_config = ConfigDict(extra="ignore")

    reason: str | None = Field(default=None, max_length=2000)
    refund: bool | None = None


class AdminReviewRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    approved: bool
    reason: str | None = Field(default=None, max_length=2000)
    reviewed_by: str | None = Field(default=None, max_length=100)
    # 拒绝订单时是否退款：None=有可退余额即自动全额退（默认），False=不退（如违约扣款）
    refund: bool | None = Field(default=None)


class AdminProcureItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    order_item_id: str = Field(min_length=1, max_length=64)
    supplier_id: str | None = Field(default=None, max_length=255)
    supplier_sku: str | None = Field(default=None, max_length=255)
    cost: float | None = Field(default=None, ge=0)


class AdminProcureRequest(BaseModel):
    """行级推送采购（仅代发行）：items 为空时对全部未采购代发行执行。"""

    model_config = ConfigDict(extra="ignore")

    items: list[AdminProcureItem] = Field(default_factory=list, max_length=100)
    # 未在行级指定时使用的默认值
    supplier_id: str | None = Field(default=None, max_length=255)
    supplier_sku: str | None = Field(default=None, max_length=255)
    cost: float | None = Field(default=None, ge=0)


class AdminProcureReceiveRequest(BaseModel):
    """采购入库确认：order_item_ids 为空时对全部在途（requested）行执行。"""

    model_config = ConfigDict(extra="ignore")

    order_item_ids: list[str] = Field(default_factory=list, max_length=100)


class AdminRefundItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    order_item_id: str = Field(min_length=1, max_length=64)
    quantity: int = Field(ge=1)


class AdminRefundRequest(BaseModel):
    """行级 / 部分退款：items 为空表示退全部剩余可退数量；不迁移订单履约状态。"""

    model_config = ConfigDict(extra="ignore")

    reason: str | None = Field(default=None, max_length=2000)
    items: list[AdminRefundItem] = Field(default_factory=list, max_length=100)
    # 是否同时退还剩余未退运费
    refund_shipping: bool = False
    # 是否把本次退款数量回补本地库存（未发货终止走取消入口，由取消统一回补）
    restock: bool = False
    # 幂等键：前端每次确认退款生成一次，重复提交不会二次扣款
    idempotency_key: str | None = Field(default=None, max_length=128)


class AdminOrderArchiveRequest(BaseModel):
    """批量归档（软删除）订单入参；单次上限 200，避免一次性误操作过大范围。"""

    model_config = ConfigDict(extra="forbid")

    order_numbers: list[str] = Field(default_factory=list, max_length=200)


async def _admin_order_or_404(db: AsyncSession, order_number: str, *, for_update: bool = False) -> ORMOrder:
    stmt = select(ORMOrder).where(ORMOrder.order_number == order_number).options(selectinload(ORMOrder.items))
    if for_update:
        # 资金动作前锁定订单行，配合幂等键防并发重复退款
        stmt = stmt.with_for_update()
    order = (await db.execute(stmt)).scalar_one_or_none()
    if order is None:
        raise APIError(ErrorCode.ORDER_NOT_FOUND, message="Order does not exist.")
    return order


async def _require_review_before_ship(db: AsyncSession) -> bool:
    """站点功能开关：发货前是否必须先审核通过（featureFlags.require_review_before_ship）。"""
    profile = await SQLAlchemySiteProfileRepository.get_active(db)
    config = profile.config if profile is not None else None
    if not isinstance(config, dict):
        return False
    flags = config.get("featureFlags") or config.get("feature_flags") or {}
    if not isinstance(flags, dict):
        return False
    return bool(flags.get("require_review_before_ship"))


def _review_approved(order: ORMOrder) -> bool:
    """订单是否已审核通过（review_status.approved）。"""
    review: dict[str, Any] = order.review_status if isinstance(order.review_status, dict) else {}
    return bool(review.get("approved"))


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
    archived: bool = Query(default=False),
    admin: dict[str, object] = Depends(require_permission("orders", "view")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    repo = SQLAlchemyOrderRepository()
    normalized_status = status.strip().lower() if status and status.strip() else None
    normalized_search = search.strip() if search and search.strip() else None
    data = await repo.list_orders(
        db,
        page=page,
        page_size=page_size,
        status=normalized_status,
        search=normalized_search,
        archived=archived,
    )
    # 售后角标：批量补齐本页订单的售后摘要，运营无需切页即可看到售后进展
    items = cast(list[dict[str, Any]], data.get("items") or [])
    summaries = await SQLAlchemyReturnRepository.summaries_by_order_ids(db, [item.get("id") for item in items])
    for item in items:
        item["returns_summary"] = summaries.get(str(item.get("id")))
    return data


@router.post("/archive")
async def archive_orders(
    payload: AdminOrderArchiveRequest,
    admin: dict[str, object] = Depends(require_permission("orders", "archive")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    """批量归档（软删除）订单：从后台列表 / 看板 / 导出中隐去，不物理删除，可逆。"""
    numbers = [n.strip() for n in payload.order_numbers if n and n.strip()]
    if not numbers:
        raise APIError(ErrorCode.VALIDATION_ERROR, message="order_numbers cannot be empty.")
    repo = SQLAlchemyOrderRepository()
    return await repo.archive_orders(db, numbers)


@router.delete("/{order_number}")
async def archive_order(
    order_number: str,
    admin: dict[str, object] = Depends(require_permission("orders", "archive")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    """单条归档（软删除）订单；订单不存在时返回 404，已归档时幂等返回。"""
    repo = SQLAlchemyOrderRepository()
    result = await repo.archive_orders(db, [order_number])
    if result["archived"] == 0 and result["missing"]:
        raise APIError(ErrorCode.ORDER_NOT_FOUND)
    return result


@router.post("/unarchive")
async def unarchive_orders(
    payload: AdminOrderArchiveRequest,
    admin: dict[str, object] = Depends(require_permission("orders", "archive")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    """批量取消归档（恢复）：把已归档订单重新纳入后台列表 / 看板 / 导出；单条与批量同口径。"""
    numbers = [n.strip() for n in payload.order_numbers if n and n.strip()]
    if not numbers:
        raise APIError(ErrorCode.VALIDATION_ERROR, message="order_numbers cannot be empty.")
    repo = SQLAlchemyOrderRepository()
    return await repo.unarchive_orders(db, numbers)


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
        "payment_status",
        "fulfillment_mode",
        "currency",
        "subtotal",
        "tax",
        "shipping_cost",
        "discount",
        "total",
        "refunded_amount",
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
                "payment_status": o.payment_status,
                "fulfillment_mode": _order_fulfillment_mode(o),
                "currency": o.currency,
                "subtotal": float(o.subtotal),
                "tax": float(o.tax),
                "shipping_cost": float(o.shipping_cost),
                "discount": float(o.discount),
                "total": float(o.total),
                "refunded_amount": float(o.refunded_amount or 0),
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


@router.get("/purchase-list")
async def list_purchase_list(
    status: str | None = Query(default=None, alias="status"),
    admin: dict[str, object] = Depends(require_permission("orders", "view")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """采购作业清单：未发货订单中的代发行，按供应商聚合。

    status: 缺省/`pending` 仅未采购行；`requested` 在途；`received` 已入库；`all` 全部代发行。
    不建 PO 实体（PLAN-DUAL-FULFILLMENT D4）；采购状态落在商品行，不写订单主状态。
    """
    repo = SQLAlchemyOrderRepository()
    normalized = status.strip().lower() if status and status.strip() else None
    rows = await repo.list_pending_purchases(db, status=normalized)
    supplier_rows = (await db.execute(select(ORMSupplier))).scalars().all()
    name_map = {str(s.id): s.name for s in supplier_rows}

    groups: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = str(row["supplier_id"] or "UNASSIGNED")
        group = groups.get(key)
        if group is None:
            group = {
                "supplier_id": row["supplier_id"],
                "supplier_name": name_map.get(key, "未指定供应商"),
                "item_count": 0,
                "total_quantity": 0,
                "items": [],
            }
            groups[key] = group
        group["items"].append(row)
        group["item_count"] = int(group["item_count"]) + 1
        group["total_quantity"] = int(group["total_quantity"]) + int(row["quantity"] or 0)

    return {"groups": list(groups.values()), "row_count": len(rows)}


@router.get("/purchase-list/export")
async def export_purchase_list(
    status: str | None = Query(default=None, alias="status"),
    admin: dict[str, object] = Depends(require_permission("orders", "view")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """采购作业清单 CSV 导出（UTF-8 BOM，Excel 友好）。"""
    repo = SQLAlchemyOrderRepository()
    normalized = status.strip().lower() if status and status.strip() else None
    rows = await repo.list_pending_purchases(db, status=normalized)
    supplier_rows = (await db.execute(select(ORMSupplier))).scalars().all()
    name_map = {str(s.id): s.name for s in supplier_rows}

    columns = [
        "supplier_id",
        "supplier_name",
        "order_number",
        "order_status",
        "product_id",
        "name",
        "sku",
        "supplier_sku",
        "quantity",
        "procurement_status",
        "procurement_requested_at",
        "procurement_cost",
        "destination",
        "created_at",
    ]
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                **row,
                "supplier_id": row["supplier_id"] or "",
                "supplier_name": name_map.get(str(row["supplier_id"] or "UNASSIGNED"), "未指定供应商"),
            }
        )
    content = "\ufeff" + buffer.getvalue()
    filename = f"purchase_list_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.csv"
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
    # 售后区块：订单详情内嵌该订单全部 RMA（C 端发起），无需切到售后模块再查一遍
    return_requests = await SQLAlchemyReturnRepository.list_by_order(db, cast(UUID, order.id))
    data["return_requests"] = [SQLAlchemyReturnRepository.to_dict(rr) for rr in return_requests]
    data["review_approved"] = _review_approved(order)
    # 站点的发货门禁开关下发给前端，用于提前禁用发货按钮
    data["require_review_before_ship"] = await _require_review_before_ship(db)
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
    # 站点门禁：开启「发货前需审核通过」时，未审核订单不予发货
    if await _require_review_before_ship(db) and not _review_approved(order):
        raise APIError(
            ErrorCode.ORDER_INVALID_STATE,
            message="Order must be approved before shipping (site requires review).",
        )
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
    """后台取消（履约终止）：未发货订单可取消；已收款订单默认同时全额退款并回补库存。

    取消 = 履约终止（订单 -> cancelled），退款 = 资金动作（payment_status），二者共用同一退款实现。
    """
    order = await _admin_order_or_404(db, order_number)
    cancelled = await SQLAlchemyCustomerOrderRepository.admin_cancel_order(
        db, order, reason=payload.reason, refund=payload.refund
    )
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
    """审核：confirmed -> processing（通过）；confirmed -> cancelled（拒绝，回补库存并默认全额退款）。"""
    order = await _admin_order_or_404(db, order_number)
    if not payload.approved and not (payload.reason or "").strip():
        raise APIError(ErrorCode.VALIDATION_ERROR, message="Rejecting an order requires a reason.")
    reviewed = await SQLAlchemyCustomerOrderRepository.admin_review_order(
        db,
        order,
        approved=payload.approved,
        reason=payload.reason,
        reviewed_by=payload.reviewed_by,
        refund=payload.refund,
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
    """行级推送采购（仅代发行）：只写行级采购状态，不迁移订单主状态（订单可随时发货）。"""
    order = await _admin_order_or_404(db, order_number)
    repo = SQLAlchemyCustomerOrderRepository
    if payload.items:
        for entry in payload.items:
            await repo.admin_procure_order(
                db,
                order,
                item_ids=[entry.order_item_id],
                supplier_id=entry.supplier_id or payload.supplier_id,
                supplier_sku=entry.supplier_sku or payload.supplier_sku,
                cost=entry.cost if entry.cost is not None else payload.cost,
            )
    else:
        await repo.admin_procure_order(
            db,
            order,
            item_ids=None,
            supplier_id=payload.supplier_id,
            supplier_sku=payload.supplier_sku,
            cost=payload.cost,
        )
    await db.commit()
    await db.refresh(order, attribute_names=["items"])
    return _order_to_dict(order)


@router.post("/{order_number}/procure/receive")
async def receive_procurement(
    order_number: str,
    payload: AdminProcureReceiveRequest,
    admin: dict[str, object] = Depends(require_permission("orders", "manage")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """采购到货确认（行级）：requested -> received，不影响订单主状态。"""
    order = await _admin_order_or_404(db, order_number)
    received = await SQLAlchemyCustomerOrderRepository.admin_receive_procurement(
        db, order, item_ids=payload.order_item_ids or None
    )
    await db.commit()
    await db.refresh(received, attribute_names=["items"])
    return _order_to_dict(received)


@router.post("/{order_number}/refund")
async def refund_order(
    order_number: str,
    payload: AdminRefundRequest,
    admin: dict[str, object] = Depends(require_permission("orders", "manage")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """行级 / 部分退款（行业对齐 Shopify）：items 为空=退全部剩余可退数量。

    只做资金动作（refunded_amount / payment_status），不改订单履约状态；
    无论是否发货，只要有已收款项且仍有可退余额即可退款。
    """
    # 锁定订单行，配合幂等键防并发/重复提交造成二次扣款
    order = await _admin_order_or_404(db, order_number, for_update=True)
    refunded = await SQLAlchemyCustomerOrderRepository.admin_refund_order(
        db,
        order,
        reason=payload.reason,
        item_refunds=(
            [{"order_item_id": i.order_item_id, "quantity": i.quantity} for i in payload.items]
            if payload.items
            else None
        ),
        refund_shipping=payload.refund_shipping,
        restock=payload.restock,
        idempotency_key=payload.idempotency_key,
    )
    await db.commit()
    await db.refresh(refunded, attribute_names=["items"])
    return _order_to_dict(refunded)
