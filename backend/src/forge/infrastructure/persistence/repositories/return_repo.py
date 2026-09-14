"""退货/退款申请（RMA）仓储：C 端申请链路 + Admin 审批/收货/退款/关闭 + 超时关闭。

职责边界（与 order_repo 协作而非重复实现）：
- 本模块只承载「售后流程状态机」；资金动作与库存回补统一委托 order_repo
  （admin_refund_order / _restock_items），保证「退款」只有一处实现。
- 可退数量 = order_items.quantity - refunded_quantity - 在途退货单占用数量，
  避免同一订单行被重复申请退货。
- 金额口径复用 _refund_amount_breakdown（与执行退款同一实现），杜绝两处口径漂移。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from forge.api.errors import APIError, ErrorCode
from forge.infrastructure.persistence.models import (
    ORMOrder,
    ORMOrderItem,
    ORMReturnItem,
    ORMReturnRequest,
)
from forge.infrastructure.persistence.repositories.order_repo import (
    _CENTS,
    _REFUNDABLE_PAYMENT_STATUSES,
    SQLAlchemyCustomerOrderRepository,
    _item_refundable_quantity,
    _money,
    _order_refundable_amount,
    _refund_amount_breakdown,
)

# 退货单可申请的状态：已发货/已收货（未发货订单走取消退款，不产生退货单）
RETURNABLE_ORDER_STATUSES = {"shipped", "delivered"}
# 在途退货单状态：占用行可退数量，防超量申请
OPEN_RETURN_STATUSES = ("requested", "approved", "received")
# 终态
RETURN_TERMINAL_STATUSES = {"refunded", "rejected", "cancelled", "closed"}
# 审核通过后的寄回时限（天）
DEFAULT_DEADLINE_DAYS = 14


def _return_number() -> str:
    """退货单号：RT-YYYYMMDD-XXXXXX（与订单号 FG- 前缀区分，便于客服检索）。"""
    return f"RT-{datetime.now().strftime('%Y%m%d')}-{uuid4().hex[:6].upper()}"


class SQLAlchemyReturnRepository:
    """退货申请（RMA）仓储。"""

    @staticmethod
    def _now() -> datetime:
        return datetime.now()

    # ------------------------------------------------------------------
    # 读取
    # ------------------------------------------------------------------

    @staticmethod
    async def _load_order(db: AsyncSession, order_id: UUID, *, for_update: bool = False) -> ORMOrder:
        stmt = select(ORMOrder).where(ORMOrder.id == order_id).options(selectinload(ORMOrder.items))
        if for_update:
            # 资金动作前锁定订单行，配合幂等键防止并发重复退款
            stmt = stmt.with_for_update()
        order = await db.scalar(stmt)
        if order is None:
            raise APIError(ErrorCode.ORDER_NOT_FOUND, message="Order does not exist.")
        return order

    @staticmethod
    async def pending_return_quantity_map(db: AsyncSession, order_item_ids: list[UUID]) -> dict[str, int]:
        """各订单行被在途退货单占用的数量（requested/approved/received）。"""
        if not order_item_ids:
            return {}
        rows = await db.execute(
            select(ORMReturnItem.order_item_id, func.sum(ORMReturnItem.quantity))
            .join(ORMReturnRequest, ORMReturnRequest.id == ORMReturnItem.return_id)
            .where(
                ORMReturnItem.order_item_id.in_(order_item_ids),
                ORMReturnRequest.status.in_(OPEN_RETURN_STATUSES),
            )
            .group_by(ORMReturnItem.order_item_id)
        )
        return {str(item_id): int(total or 0) for item_id, total in rows.all()}

    @staticmethod
    def to_dict(rr: ORMReturnRequest, *, order_number: str | None = None) -> dict[str, Any]:
        return {
            "id": str(rr.id),
            "return_number": rr.return_number,
            "order_id": str(rr.order_id),
            "order_number": order_number or getattr(rr, "order_number", None),
            "user_id": str(rr.user_id),
            "status": rr.status,
            "reason": rr.reason,
            "note": rr.note,
            "refund_method": rr.refund_method,
            "refund_amount": float(_money(rr.refund_amount)),
            "refund_shipping": bool(rr.refund_shipping),
            "restock": bool(rr.restock),
            "requested_at": rr.requested_at.isoformat() if rr.requested_at else None,
            "deadline_at": rr.deadline_at.isoformat() if rr.deadline_at else None,
            "reviewed_at": rr.reviewed_at.isoformat() if rr.reviewed_at else None,
            "reviewed_by": rr.reviewed_by,
            "review_note": rr.review_note,
            "carrier": rr.carrier,
            "tracking_number": rr.tracking_number,
            "shipped_at": rr.shipped_at.isoformat() if rr.shipped_at else None,
            "received_at": rr.received_at.isoformat() if rr.received_at else None,
            "refunded_at": rr.refunded_at.isoformat() if rr.refunded_at else None,
            "refund_id": rr.refund_id,
            "cancelled_at": rr.cancelled_at.isoformat() if rr.cancelled_at else None,
            "closed_reason": rr.closed_reason,
            "created_at": rr.created_at.isoformat() if rr.created_at else None,
            "updated_at": rr.updated_at.isoformat() if rr.updated_at else None,
            "items": [
                {
                    "id": str(i.id),
                    "order_item_id": str(i.order_item_id),
                    "name": i.name,
                    "sku": i.sku,
                    "unit_price": float(_money(i.unit_price)),
                    "quantity": int(i.quantity or 0),
                }
                for i in (rr.items or [])
            ],
        }

    @staticmethod
    async def _order_number_map(db: AsyncSession, order_ids: list[Any]) -> dict[str, str]:
        """批量取订单号（return_requests 不冗余存订单号，列表查询时联表补齐）。"""
        ids = [oid for oid in order_ids if oid is not None]
        if not ids:
            return {}
        rows = await db.execute(select(ORMOrder.id, ORMOrder.order_number).where(ORMOrder.id.in_(ids)))
        return {str(oid): str(number) for oid, number in rows.all()}

    @staticmethod
    async def _attach_order_number(db: AsyncSession, rr: ORMReturnRequest) -> ORMReturnRequest:
        """详情场景单品补齐订单号。"""
        mapping = await SQLAlchemyReturnRepository._order_number_map(db, [rr.order_id])
        number = mapping.get(str(rr.order_id))
        if number:
            rr.order_number = number  # type: ignore[attr-defined]
        return rr

    @staticmethod
    async def list_by_order(db: AsyncSession, order_id: UUID) -> list[ORMReturnRequest]:
        """订单详情用：该订单下全部售后单（含明细），按创建时间倒序。"""
        rows = await db.scalars(
            select(ORMReturnRequest)
            .where(ORMReturnRequest.order_id == order_id)
            .options(selectinload(ORMReturnRequest.items))
            .order_by(ORMReturnRequest.created_at.desc())
        )
        return list(rows.all())

    @staticmethod
    async def summaries_by_order_ids(db: AsyncSession, order_ids: list[Any]) -> dict[str, dict[str, Any]]:
        """订单列表用：批量聚合各订单的售后摘要（总数 / 在途数 / 最近状态 / 已退金额）。

        一次查询覆盖整页订单，避免列表页 N+1。
        """
        ids = [oid for oid in order_ids if oid is not None]
        if not ids:
            return {}
        rows = (
            await db.scalars(
                select(ORMReturnRequest)
                .where(ORMReturnRequest.order_id.in_(ids))
                .order_by(ORMReturnRequest.created_at.desc())
            )
        ).all()
        summaries: dict[str, dict[str, Any]] = {}
        for rr in rows:
            key = str(rr.order_id)
            summary = summaries.get(key)
            if summary is None:
                # 倒序首条即最近一张售后单
                summary = {
                    "total": 0,
                    "open": 0,
                    "latest_status": rr.status,
                    "latest_return_number": rr.return_number,
                    "refunded_amount": 0.0,
                    "last_requested_at": rr.requested_at.isoformat() if rr.requested_at else None,
                }
                summaries[key] = summary
            summary["total"] = int(summary["total"]) + 1
            if rr.status in OPEN_RETURN_STATUSES:
                summary["open"] = int(summary["open"]) + 1
            if rr.status == "refunded":
                summary["refunded_amount"] = round(
                    float(summary["refunded_amount"]) + float(_money(rr.refund_amount)), 2
                )
        return summaries

    @staticmethod
    async def get_return_request(db: AsyncSession, return_number: str, *, for_update: bool = False) -> ORMReturnRequest:
        stmt = (
            select(ORMReturnRequest)
            .where(ORMReturnRequest.return_number == return_number)
            .options(selectinload(ORMReturnRequest.items))
        )
        if for_update:
            # 退款前锁行：两个并发请求只有一个能拿到 approved/received 状态
            stmt = stmt.with_for_update()
        rr = await db.scalar(stmt)
        if rr is None:
            raise APIError(ErrorCode.RETURN_NOT_FOUND, message="Return request does not exist.")
        return await SQLAlchemyReturnRepository._attach_order_number(db, rr)

    @staticmethod
    async def list_customer_returns(
        db: AsyncSession,
        *,
        user_id: UUID,
        status: str | None = None,
        order_number: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        conditions = [ORMReturnRequest.user_id == user_id]
        if status:
            conditions.append(ORMReturnRequest.status == status)
        if order_number:
            conditions.append(
                ORMReturnRequest.order_id.in_(select(ORMOrder.id).where(ORMOrder.order_number == order_number))
            )
        total = int(await db.scalar(select(func.count()).select_from(ORMReturnRequest).where(*conditions)) or 0)
        rows = (
            await db.scalars(
                select(ORMReturnRequest)
                .where(*conditions)
                .options(selectinload(ORMReturnRequest.items))
                .order_by(ORMReturnRequest.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
        numbers = await SQLAlchemyReturnRepository._order_number_map(db, [r.order_id for r in rows])
        return {
            "items": [SQLAlchemyReturnRepository.to_dict(r, order_number=numbers.get(str(r.order_id))) for r in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @staticmethod
    async def list_admin_returns(
        db: AsyncSession,
        *,
        status: str | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        conditions: list[Any] = []
        if status:
            conditions.append(ORMReturnRequest.status == status)
        if keyword:
            like = f"%{keyword.strip()}%"
            conditions.append(
                ORMReturnRequest.return_number.ilike(like)
                | ORMReturnRequest.reason.ilike(like)
                | ORMReturnRequest.order_id.in_(select(ORMOrder.id).where(ORMOrder.order_number.ilike(like)))
            )
        total = int(await db.scalar(select(func.count()).select_from(ORMReturnRequest).where(*conditions)) or 0)
        rows = (
            await db.scalars(
                select(ORMReturnRequest)
                .where(*conditions)
                .options(selectinload(ORMReturnRequest.items))
                .order_by(ORMReturnRequest.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
        numbers = await SQLAlchemyReturnRepository._order_number_map(db, [r.order_id for r in rows])
        return {
            "items": [SQLAlchemyReturnRepository.to_dict(r, order_number=numbers.get(str(r.order_id))) for r in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @staticmethod
    async def return_stats(db: AsyncSession) -> dict[str, Any]:
        """售后看板计数：待审 / 待收货 / 待退款 / 已完成 + 已退款金额合计。"""
        rows = await db.execute(select(ORMReturnRequest.status, func.count()).group_by(ORMReturnRequest.status))
        counts = {str(status): int(total or 0) for status, total in rows.all()}
        refunded_amount = await db.scalar(
            select(func.coalesce(func.sum(ORMReturnRequest.refund_amount), 0)).where(
                ORMReturnRequest.status == "refunded"
            )
        )
        return {
            "requested": counts.get("requested", 0),
            "approved": counts.get("approved", 0),
            "received": counts.get("received", 0),
            "refunded": counts.get("refunded", 0),
            "rejected": counts.get("rejected", 0),
            "cancelled": counts.get("cancelled", 0),
            "closed": counts.get("closed", 0),
            "refunded_amount": float(_money(refunded_amount or 0)),
            "total": sum(counts.values()),
        }

    @staticmethod
    async def return_eligibility(db: AsyncSession, order: ORMOrder) -> dict[str, Any]:
        """订单可退性：返回是否可申请 + 各行剩余可退数量（已扣在途退货占用）。"""
        item_ids = [cast(UUID, i.id) for i in (order.items or [])]
        pending = await SQLAlchemyReturnRepository.pending_return_quantity_map(db, item_ids)
        items: list[dict[str, Any]] = []
        for item in order.items or []:
            refundable = _item_refundable_quantity(item)
            in_flight = pending.get(str(item.id), 0)
            items.append(
                {
                    "order_item_id": str(item.id),
                    "name": item.name,
                    "sku": item.sku,
                    "unit_price": float(_money(item.price)),
                    "purchased_quantity": int(item.quantity or 0),
                    "refunded_quantity": int(item.refunded_quantity or 0),
                    "in_flight_quantity": in_flight,
                    "returnable_quantity": max(refundable - in_flight, 0),
                }
            )
        status_ok = order.status in RETURNABLE_ORDER_STATUSES
        paid_ok = order.payment_status in _REFUNDABLE_PAYMENT_STATUSES
        remaining = float(_order_refundable_amount(order))
        return {
            "order_number": order.order_number,
            "order_status": order.status,
            "payment_status": order.payment_status,
            "eligible": status_ok and paid_ok and remaining > 0,
            "reason": (None if status_ok and paid_ok else "Order is not eligible for return in its current state."),
            "refundable_amount": remaining,
            "days_after_delivery": 0,
            "items": items,
        }

    # ------------------------------------------------------------------
    # C 端写操作
    # ------------------------------------------------------------------

    @staticmethod
    async def create_return_request(
        db: AsyncSession,
        order: ORMOrder,
        *,
        user_id: UUID,
        items: list[dict[str, Any]],
        reason: str,
        note: str | None = None,
        refund_method: str = "original",
    ) -> ORMReturnRequest:
        """创建退货申请：校验订单可退性 + 行级剩余可退数量（扣在途占用）+ 可退余额。"""
        if order.status not in RETURNABLE_ORDER_STATUSES:
            raise APIError(
                ErrorCode.RETURN_NOT_ELIGIBLE,
                message=f"Order cannot be returned in state '{order.status}'.",
            )
        if order.payment_status not in _REFUNDABLE_PAYMENT_STATUSES:
            raise APIError(
                ErrorCode.RETURN_NOT_ELIGIBLE,
                message="Order has no paid amount to refund.",
            )

        by_id = {str(i.id): i for i in (order.items or [])}
        pending = await SQLAlchemyReturnRepository.pending_return_quantity_map(
            db, [cast(UUID, i.id) for i in (order.items or [])]
        )
        plan: list[tuple[ORMOrderItem, int]] = []
        for entry in items:
            item = by_id.get(str(entry.get("order_item_id")))
            if item is None:
                raise APIError(ErrorCode.VALIDATION_ERROR, message="Return item does not belong to this order.")
            quantity = int(entry.get("quantity") or 0)
            if quantity <= 0:
                raise APIError(ErrorCode.VALIDATION_ERROR, message="Return quantity must be positive.")
            available = _item_refundable_quantity(item) - pending.get(str(item.id), 0)
            if quantity > available:
                raise APIError(
                    ErrorCode.RETURN_QUANTITY_EXCEEDS,
                    message=(
                        f"Return quantity exceeds returnable quantity for '{item.name}' ({max(available, 0)} left)."
                    ),
                )
            plan.append((item, quantity))
        if not plan:
            raise APIError(ErrorCode.VALIDATION_ERROR, message="Return request must contain at least one item.")

        _, _, _, amount = _refund_amount_breakdown(order, plan, False)
        if amount > _order_refundable_amount(order):
            raise APIError(ErrorCode.VALIDATION_ERROR, message="Refund amount exceeds refundable balance.")

        now = SQLAlchemyReturnRepository._now()
        rr = ORMReturnRequest(
            return_number=_return_number(),
            order_id=cast(Any, order.id),
            user_id=cast(Any, user_id),
            status="requested",
            reason=reason,
            note=note,
            refund_method=refund_method or "original",
            refund_amount=cast(Any, Decimal("0")),
            refund_shipping=cast(Any, False),
            restock=cast(Any, True),
            requested_at=cast(Any, now),
            created_at=cast(Any, now),
            updated_at=cast(Any, now),
        )
        db.add(rr)
        await db.flush()
        for item, quantity in plan:
            db.add(
                ORMReturnItem(
                    return_id=cast(Any, rr.id),
                    order_item_id=cast(Any, item.id),
                    name=item.name,
                    sku=item.sku,
                    unit_price=item.price,
                    quantity=quantity,
                    created_at=cast(Any, now),
                )
            )
        await db.flush()
        await db.refresh(rr, attribute_names=["items"])
        return rr

    @staticmethod
    async def cancel_return_request(
        db: AsyncSession, rr: ORMReturnRequest, *, reason: str | None = None
    ) -> ORMReturnRequest:
        """客户撤销申请：仅未进入退款终态前允许（requested / approved / received）。"""
        if rr.status not in OPEN_RETURN_STATUSES:
            raise APIError(
                ErrorCode.RETURN_NOT_CANCELLABLE,
                message=f"Return request cannot be cancelled in state '{rr.status}'.",
            )
        now = SQLAlchemyReturnRepository._now()
        rr.status = cast(Any, "cancelled")
        rr.cancelled_at = cast(Any, now)
        rr.closed_reason = cast(Any, reason or "Cancelled by customer")
        rr.updated_at = cast(Any, now)
        await db.flush()
        return rr

    @staticmethod
    async def submit_return_shipment(
        db: AsyncSession,
        rr: ORMReturnRequest,
        *,
        carrier: str,
        tracking_number: str,
    ) -> ORMReturnRequest:
        """客户回填寄回物流：仅 approved（已授权、未收货、未超期）可提交，重复提交覆盖单号。

        仅记录物流信息、不改变状态机：是否到货由 Admin 收货确认（received）决定。
        """
        if rr.status != "approved":
            raise APIError(
                ErrorCode.RETURN_INVALID_STATE,
                message=(
                    f"Shipment info can only be submitted after the return is approved (current state '{rr.status}')."
                ),
            )
        now = SQLAlchemyReturnRepository._now()
        if rr.deadline_at is not None and rr.deadline_at < now:
            raise APIError(
                ErrorCode.RETURN_INVALID_STATE,
                message="The return shipment deadline has passed.",
            )
        rr.carrier = cast(Any, carrier)
        rr.tracking_number = cast(Any, tracking_number)
        if rr.shipped_at is None:
            # 首次寄出时间用于超期判断与时效统计，重复提交不覆盖
            rr.shipped_at = cast(Any, now)
        rr.updated_at = cast(Any, now)
        await db.flush()
        return rr

    # ------------------------------------------------------------------
    # Admin 写操作
    # ------------------------------------------------------------------

    @staticmethod
    async def review_return_request(
        db: AsyncSession,
        rr: ORMReturnRequest,
        *,
        approved: bool,
        reviewed_by: str = "admin",
        note: str | None = None,
        restock: bool | None = None,
        refund_shipping: bool | None = None,
        deadline_days: int = DEFAULT_DEADLINE_DAYS,
    ) -> ORMReturnRequest:
        """审核退货申请：通过则锁定应退金额与寄回截止时间；驳回则直接终结。"""
        if rr.status != "requested":
            raise APIError(
                ErrorCode.RETURN_INVALID_STATE,
                message=f"Return request cannot be reviewed in state '{rr.status}'.",
            )
        order = await SQLAlchemyReturnRepository._load_order(db, cast(UUID, rr.order_id))
        now = SQLAlchemyReturnRepository._now()
        rr.reviewed_at = cast(Any, now)
        rr.reviewed_by = cast(Any, reviewed_by)
        rr.review_note = cast(Any, note)
        if not approved:
            rr.status = cast(Any, "rejected")
            rr.updated_at = cast(Any, now)
            await db.flush()
            return rr

        plan = SQLAlchemyReturnRepository._plan_for_return(order, rr)
        if not plan:
            raise APIError(
                ErrorCode.RETURN_NOT_ELIGIBLE,
                message="Nothing left to refund for this return request.",
            )
        rr.refund_shipping = cast(Any, bool(refund_shipping))
        if restock is not None:
            rr.restock = cast(Any, bool(restock))
        _, _, _, amount = _refund_amount_breakdown(order, plan, bool(rr.refund_shipping))
        if amount <= 0 or amount > _order_refundable_amount(order):
            raise APIError(
                ErrorCode.RETURN_NOT_ELIGIBLE,
                message="Refund amount exceeds refundable balance.",
            )
        rr.refund_amount = cast(Any, amount)
        rr.status = cast(Any, "approved")
        rr.deadline_at = cast(Any, now + timedelta(days=max(int(deadline_days), 1)))
        rr.updated_at = cast(Any, now)
        await db.flush()
        return rr

    @staticmethod
    def _plan_for_return(order: ORMOrder, rr: ORMReturnRequest) -> list[tuple[ORMOrderItem, int]]:
        """退货单行 -> 当前订单行（按剩余可退数量截断，避免历史变更导致超额退款）。"""
        by_id = {str(i.id): i for i in (order.items or [])}
        plan: list[tuple[ORMOrderItem, int]] = []
        for line in rr.items or []:
            item = by_id.get(str(line.order_item_id))
            if item is None:
                continue
            quantity = min(int(line.quantity or 0), _item_refundable_quantity(item))
            if quantity > 0:
                plan.append((item, quantity))
        return plan

    @staticmethod
    async def mark_return_received(
        db: AsyncSession, rr: ORMReturnRequest, *, note: str | None = None
    ) -> ORMReturnRequest:
        """确认收到回寄商品：approved -> received（待退款）。"""
        if rr.status not in {"approved", "received"}:
            raise APIError(
                ErrorCode.RETURN_INVALID_STATE,
                message=f"Return request cannot be received in state '{rr.status}'.",
            )
        now = SQLAlchemyReturnRepository._now()
        rr.status = cast(Any, "received")
        rr.received_at = cast(Any, now)
        if note:
            rr.review_note = cast(Any, note)
        rr.updated_at = cast(Any, now)
        await db.flush()
        return rr

    @staticmethod
    async def execute_return_refund(
        db: AsyncSession,
        rr: ORMReturnRequest,
        *,
        refunded_by: str = "admin",
        note: str | None = None,
    ) -> ORMReturnRequest:
        """执行退货退款：委托 order_repo.admin_refund_order（唯一资金实现）并回写售后单。

        - 金额校验：实算金额须与审核锁定金额一致（容差 1 分），否则要求重新审核
        - restock=True 时按本次退款数量回补库存（委托 order_repo 实现）
        - 幂等：锁定订单行 + 售后单号作为幂等键，重复提交不产生二次扣款
        """
        if rr.status not in {"approved", "received"}:
            raise APIError(
                ErrorCode.RETURN_INVALID_STATE,
                message=f"Return request cannot be refunded in state '{rr.status}'.",
            )
        order = await SQLAlchemyReturnRepository._load_order(db, cast(UUID, rr.order_id), for_update=True)
        plan = SQLAlchemyReturnRepository._plan_for_return(order, rr)
        if not plan:
            raise APIError(
                ErrorCode.RETURN_NOT_ELIGIBLE,
                message="Nothing left to refund for this return request.",
            )
        _, _, _, amount = _refund_amount_breakdown(order, plan, bool(rr.refund_shipping))
        locked = _money(rr.refund_amount)
        if locked > 0 and abs(amount - locked) > _CENTS:
            raise APIError(
                ErrorCode.RETURN_INVALID_STATE,
                message="Refund amount changed after review; please re-review the return request.",
            )

        await SQLAlchemyCustomerOrderRepository.admin_refund_order(
            db,
            order,
            reason=f"Return {rr.return_number}: {rr.reason}",
            item_refunds=[{"order_item_id": str(item.id), "quantity": quantity} for item, quantity in plan],
            refund_shipping=bool(rr.refund_shipping),
            restock=bool(rr.restock),
            refunded_by=refunded_by,
            return_id=str(rr.id),
            idempotency_key=f"return:{rr.return_number}",
        )
        refunds = cast(list[Any], order.refunds or [])
        last = refunds[-1] if refunds and isinstance(refunds[-1], dict) else {}
        now = SQLAlchemyReturnRepository._now()
        rr.status = cast(Any, "refunded")
        rr.refunded_at = cast(Any, now)
        rr.refund_id = cast(Any, last.get("id"))
        rr.refund_amount = cast(Any, amount)
        if note:
            rr.review_note = cast(Any, note)
        rr.updated_at = cast(Any, now)
        await db.flush()
        return rr

    @staticmethod
    async def close_return_request(
        db: AsyncSession, rr: ORMReturnRequest, *, reason: str | None = None
    ) -> ORMReturnRequest:
        """关闭售后单（人工）：仅未退款成功的单据可关闭。"""
        if rr.status in {"refunded", "rejected"}:
            raise APIError(
                ErrorCode.RETURN_INVALID_STATE,
                message=f"Return request cannot be closed in state '{rr.status}'.",
            )
        now = SQLAlchemyReturnRepository._now()
        rr.status = cast(Any, "closed")
        rr.closed_reason = cast(Any, reason or "Closed by admin")
        rr.updated_at = cast(Any, now)
        await db.flush()
        return rr

    @staticmethod
    async def expire_overdue_returns(db: AsyncSession) -> int:
        """超时关闭：审核通过后超过寄回时限仍未收货的申请单 -> closed(expired)。"""
        now = SQLAlchemyReturnRepository._now()
        rows = (
            await db.scalars(
                select(ORMReturnRequest).where(
                    ORMReturnRequest.status == "approved",
                    ORMReturnRequest.deadline_at.is_not(None),
                    ORMReturnRequest.deadline_at < now,
                )
            )
        ).all()
        for rr in rows:
            rr.status = cast(Any, "closed")
            rr.closed_reason = cast(Any, "Expired: item not returned before the deadline")
            rr.updated_at = cast(Any, now)
        if rows:
            await db.flush()
        return len(rows)
