"""Order — SQLAlchemy Repository."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import String, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from forge.api.errors import APIError, ErrorCode
from forge.infrastructure.persistence.models import ORMOrder, ORMOrderItem, ORMProduct, ORMShipment, ORMUser


class SQLAlchemyOrderRepository:
    """订单数据库访问封装。"""

    @staticmethod
    async def list_orders(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        search: str | None = None,
    ) -> dict[str, object]:
        filters = _admin_order_filters(status=status, search=search)
        stmt = select(ORMOrder).options(selectinload(ORMOrder.items))
        count_stmt = select(func.count(ORMOrder.id))
        if filters:
            stmt = stmt.where(*filters)
            count_stmt = count_stmt.where(*filters)
        total = int((await db.execute(count_stmt)).scalar_one())
        query = stmt.order_by(ORMOrder.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(query)
        orders = result.scalars().all()

        # 批量带出客户邮箱，供后台列表"复制邮箱"等客服快捷操作使用
        user_ids = {cast(UUID, o.user_id) for o in orders if o.user_id is not None}
        email_by_user: dict[UUID, str] = {}
        if user_ids:
            user_rows = (await db.execute(select(ORMUser.id, ORMUser.email).where(ORMUser.id.in_(user_ids)))).all()
            email_by_user = {row.id: row.email for row in user_rows}

        return {
            "items": [
                {
                    "id": str(o.id),
                    "order_number": o.order_number,
                    "user_id": str(o.user_id),
                    "email": email_by_user.get(cast(UUID, o.user_id), "") if o.user_id is not None else "",
                    "subtotal": float(o.subtotal),
                    "tax": float(o.tax),
                    "shipping_cost": float(o.shipping_cost),
                    "discount": float(o.discount),
                    "total": float(o.total),
                    "currency": o.currency,
                    "status": o.status,
                    "payment_status": o.payment_status,
                    "refunded_amount": float(_money(o.refunded_amount)),
                    # 订单级履约模式聚合列：self / dropship / mixed（列表页展示用）
                    "fulfillment_mode": _order_fulfillment_mode(o),
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
                            "fulfillment_mode": i.fulfillment_mode or _FULFILLMENT_SELF,
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
    async def list_all_orders(
        db: AsyncSession,
        status: str | None = None,
        search: str | None = None,
    ) -> list[ORMOrder]:
        """导出用：返回全部匹配筛选条件的订单（不分页，含 items）。"""
        filters = _admin_order_filters(status=status, search=search)
        stmt = select(ORMOrder).options(selectinload(ORMOrder.items)).order_by(ORMOrder.created_at.desc())
        if filters:
            stmt = stmt.where(*filters)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def list_pending_purchases(db: AsyncSession, status: str | None = None) -> list[dict[str, Any]]:
        """采购作业清单原始行：未发货订单中的代发行，按行输出（分组在 API 层按供应商完成）。

        status: None/'pending' 仅未采购行；'requested'/'received' 按行级采购状态过滤；'all' 全部代发行。
        """
        stmt = (
            select(ORMOrder)
            .where(ORMOrder.deleted_at.is_(None), ORMOrder.status.in_(_PURCHASE_PENDING_ORDER_STATUSES))
            .options(selectinload(ORMOrder.items))
            .order_by(ORMOrder.created_at.desc())
        )
        orders = (await db.execute(stmt)).scalars().all()
        rows: list[dict[str, Any]] = []
        for order in orders:
            address = cast(dict[str, Any], order.shipping_address or {})
            destination = (
                ", ".join(str(x) for x in [address.get("line1"), address.get("city"), address.get("country")] if x)
                or "N/A"
            )
            for i in order.items:
                if (i.fulfillment_mode or _FULFILLMENT_SELF) != _FULFILLMENT_DROPSHIP:
                    continue
                row_status = i.procurement_status
                if status in {"requested", "received"} and row_status != status:
                    continue
                if status not in {"all", "requested", "received"} and row_status is not None:
                    continue
                rows.append(
                    {
                        "order_item_id": str(i.id),
                        "order_number": order.order_number,
                        "order_status": order.status,
                        "created_at": order.created_at.isoformat() if order.created_at else None,
                        "supplier_id": str(i.supplier_id) if i.supplier_id else None,
                        "supplier_sku": i.supplier_sku,
                        "product_id": int(i.product_id) if i.product_id is not None else None,
                        "name": i.name,
                        "sku": i.sku,
                        "quantity": i.quantity,
                        "image": i.image,
                        "destination": destination,
                        "procurement_status": row_status,
                        "procurement_requested_at": (
                            i.procurement_requested_at.isoformat() if i.procurement_requested_at else None
                        ),
                        "procurement_cost": float(i.procurement_cost) if i.procurement_cost is not None else None,
                    }
                )
        return rows

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

    @staticmethod
    async def dashboard_stats(db: AsyncSession, trend_days: int = 7) -> dict[str, Any]:
        """仪表盘订单域聚合：总量 / 今日 / 待处理 / 采购异常 / GMV / 近 N 日趋势。

        - 口径统一剔除软删除订单（deleted_at is null），与订单列表默认视图一致；
        - 日期基准取数据库 current_date，避免应用容器与数据库时区不一致导致跨日错位；
        - 待处理口径复用下单待处理集合（未进入发货环节的活跃订单）。
        """
        alive = ORMOrder.deleted_at.is_(None)
        today = await db.scalar(select(func.current_date()))
        if today is None:  # pragma: no cover - current_date 恒有值，仅作类型兜底
            today = datetime.now(UTC).date()

        paid = ORMOrder.payment_status == "paid"
        totals = (
            await db.execute(
                select(
                    func.count(ORMOrder.id),
                    func.coalesce(func.sum(ORMOrder.total).filter(paid), 0),
                    func.count(ORMOrder.id).filter(ORMOrder.created_at >= today),
                    func.coalesce(func.sum(ORMOrder.total).filter(paid, ORMOrder.created_at >= today), 0),
                    func.count(ORMOrder.id).filter(ORMOrder.status.in_(tuple(_PURCHASE_PENDING_ORDER_STATUSES))),
                    func.count(ORMOrder.id).filter(ORMOrder.status == "procure_failed"),
                ).where(alive)
            )
        ).one()
        total_orders, total_revenue, today_orders, today_gmv, pending_orders, procurement_errors = totals

        status_stmt = select(ORMOrder.status, func.count(ORMOrder.id)).where(alive).group_by(ORMOrder.status)
        status_counts = {row[0]: row[1] for row in (await db.execute(status_stmt)).all()}

        day = func.date(ORMOrder.created_at)
        start_day = today - timedelta(days=trend_days - 1)
        trend_stmt = select(day, func.count(ORMOrder.id)).where(alive, ORMOrder.created_at >= start_day).group_by(day)
        counts_by_day = {row[0]: int(row[1]) for row in (await db.execute(trend_stmt)).all()}

        dates: list[str] = []
        counts: list[int] = []
        for offset in range(trend_days - 1, -1, -1):
            current = today - timedelta(days=offset)
            dates.append(f"{current.month}/{current.day}")
            counts.append(counts_by_day.get(current, 0))

        return {
            "total_orders": int(total_orders),
            "total_revenue": float(total_revenue or 0),
            "today_orders": int(today_orders),
            "today_gmv": float(today_gmv or 0),
            "pending_orders": int(pending_orders),
            "procurement_errors": int(procurement_errors),
            "status_counts": status_counts,
            "order_trend": {"dates": dates, "counts": counts},
        }


# ---------------------------------------------------------------------------
# Admin order list filters (shared by list + count queries)
# ---------------------------------------------------------------------------


def _admin_order_filters(status: str | None, search: str | None) -> list[Any]:
    """Build WHERE conditions shared by the admin order list and its count query."""
    conditions: list[Any] = []
    if status:
        conditions.append(ORMOrder.status == status.lower())
    if search and search.strip():
        keyword = f"%{search.strip()}%"
        conditions.append(
            or_(
                ORMOrder.order_number.ilike(keyword),
                ORMOrder.user_id.cast(String).ilike(keyword),
                # 客服高频诉求：按客户邮箱反查订单
                ORMOrder.user_id.in_(select(ORMUser.id).where(ORMUser.email.ilike(keyword))),
            )
        )
    return conditions


# ---------------------------------------------------------------------------
# C-end commerce (customer orders)
# ---------------------------------------------------------------------------

_CANCELLABLE_STATUSES = {"pending", "confirmed", "processing"}
_PAYABLE_STATUSES = {"pending"}
_CONFIRMABLE_STATUSES = {"shipped"}
_DELETABLE_STATUSES = {"delivered", "cancelled"}
# 收货地址仅允许在发货前修改（行业对齐：pending/confirmed/processing 均未发货）
_EDITABLE_SHIPPING_STATUSES = {"pending", "confirmed", "processing"}
# Admin review flow guard (stored statuses are lowercase)
_ADMIN_REVIEWABLE_STATUSES = {"confirmed"}
_FREE_SHIPPING_THRESHOLD = 50
_FLAT_SHIPPING = 5
_DEFAULT_CURRENCY = "USD"
# 履约模式（PLAN-DUAL-FULFILLMENT）：self=自采购（占本地库存）；dropship=一件代发（不占本地库存）
_FULFILLMENT_SELF = "self"
_FULFILLMENT_DROPSHIP = "dropship"
# 后台取消（履约终止）适用状态：未发货即可取消（含历史 procuring / procure_failed 脏状态）
_ADMIN_CANCELLABLE_STATUSES = {"pending", "confirmed", "processing", "procuring", "procure_failed"}
# 退款（资金动作）：订单须有已收款项，且未处于取消/退款终态（已发货/已完成同样支持售后退款）
_REFUNDABLE_PAYMENT_STATUSES = {"paid", "partially_refunded"}
_REFUND_BLOCKED_ORDER_STATUSES = {"cancelled", "refunded"}
# 采购（行级旁支动作）适用状态：未发货订单；仅 dropship 行可采购
_PROCURE_ORDER_STATUSES = {"pending", "confirmed", "processing", "procuring", "procure_failed"}
# 待采购清单口径：未发货的订单状态（已发货/终态不列入采购）
_PURCHASE_PENDING_ORDER_STATUSES = {"pending", "confirmed", "processing", "procure_failed"}

_CENTS = Decimal("0.01")


def _money(value: Any) -> Decimal:
    """DB Numeric -> Decimal（None 视为 0），避免浮点误差。"""
    return Decimal(str(value)) if value is not None else Decimal("0")


def _item_line_total(item: ORMOrderItem) -> Decimal:
    return _money(item.price) * int(item.quantity or 0)


def _item_refundable_quantity(item: ORMOrderItem) -> int:
    """行剩余可退数量（部分退款不阻断同订单其他行发货）。"""
    return max(int(item.quantity or 0) - int(item.refunded_quantity or 0), 0)


def _order_refundable_amount(order: ORMOrder) -> Decimal:
    """订单剩余可退金额（商品 + 税 + 运费累计上限校验）。"""
    return max(_money(order.total) - _money(order.refunded_amount), Decimal("0"))


def _refunded_shipping_total(order: ORMOrder) -> Decimal:
    """累计已退运费（避免重复退运费）。"""
    total = Decimal("0")
    for entry in cast(list[Any], order.refunds or []):
        if isinstance(entry, dict):
            total += _money(entry.get("shipping_amount"))
    return total


def _refund_amount_breakdown(
    order: ORMOrder,
    plan: list[tuple[ORMOrderItem, int]],
    refund_shipping: bool,
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    """退款金额拆解（商品/税/运费/合计），供 admin_refund_order 与售后申请单预审复用。

    - 税按「退款行小计占订单商品小计」比例分摊（行业：退款同时退还对应税额）
    - 运费仅在 refund_shipping=True 时退还剩余未退部分（避免重复退运费）
    """
    goods_amount = sum((_money(i.price) * quantity for i, quantity in plan), Decimal("0"))
    tax_amount = Decimal("0")
    subtotal = _money(order.subtotal)
    if subtotal > 0 and _money(order.tax) > 0:
        refunded_base = sum((_item_line_total(i) for i, _ in plan), Decimal("0"))
        tax_amount = (_money(order.tax) * refunded_base / subtotal).quantize(_CENTS)
    shipping_amount = Decimal("0")
    if refund_shipping:
        shipping_amount = max(_money(order.shipping_cost) - _refunded_shipping_total(order), Decimal("0"))
    amount = (goods_amount + tax_amount + shipping_amount).quantize(_CENTS)
    return goods_amount, tax_amount, shipping_amount, amount


def _restocked_quantity_map(order: ORMOrder) -> dict[str, int]:
    """各行已通过退款 restock 回补过的数量，取消回补时据此去重。"""
    out: dict[str, int] = {}
    for entry in cast(list[Any], order.refunds or []):
        if not isinstance(entry, dict) or not entry.get("restock"):
            continue
        for line in cast(list[Any], entry.get("items") or []):
            if isinstance(line, dict):
                key = str(line.get("order_item_id"))
                out[key] = out.get(key, 0) + int(line.get("quantity") or 0)
    return out


def _order_fulfillment_mode(order: ORMOrder) -> str:
    """订单级履约模式聚合：全自采购 self / 全代发 dropship / 混合 mixed（历史行按 self 解释）。"""
    modes = {(i.fulfillment_mode or _FULFILLMENT_SELF) for i in (order.items or [])}
    if len(modes) > 1:
        return "mixed"
    return str(next(iter(modes))) if modes else _FULFILLMENT_SELF


def _procurement_summary(order: ORMOrder) -> dict[str, int]:
    """行级采购汇总：仅统计 dropship 行（self 行不参与采购）。"""
    total = requested = received = 0
    for i in order.items or []:
        if (i.fulfillment_mode or _FULFILLMENT_SELF) != _FULFILLMENT_DROPSHIP:
            continue
        total += 1
        if i.procurement_status == "received":
            received += 1
        elif i.procurement_status == "requested":
            requested += 1
    return {"total": total, "requested": requested, "received": received, "pending": total - requested - received}


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
        "payment_method": order.payment_method,
        "payment_status": order.payment_status,
        "payment_intent_id": order.payment_intent_id,
        "paid_at": order.paid_at.isoformat() if order.paid_at else None,
        "confirmed_at": order.confirmed_at.isoformat() if order.confirmed_at else None,
        "shipped_at": order.shipped_at.isoformat() if order.shipped_at else None,
        "delivered_at": order.delivered_at.isoformat() if order.delivered_at else None,
        "deleted_at": order.deleted_at.isoformat() if order.deleted_at else None,
        "tracking_number": order.tracking_number,
        "review_status": order.review_status,
        "procurement_info": order.procurement_info,
        # 采购汇总（行级采购派生）：待采 / 在途 / 已入库；订单级不再是采购载体
        "procurement_summary": _procurement_summary(order),
        # 资金：累计已退金额、剩余可退余额、退款流水（行级）
        "refunded_amount": float(_money(order.refunded_amount)),
        "refundable_amount": float(_order_refundable_amount(order)),
        "refunds": order.refunds or [],
        # 订单级履约模式聚合：self / dropship / mixed
        "fulfillment_mode": _order_fulfillment_mode(order),
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
                # 履约快照（历史行为空，读取侧按 self 解释）
                "fulfillment_mode": i.fulfillment_mode or _FULFILLMENT_SELF,
                "supplier_id": str(i.supplier_id) if i.supplier_id else None,
                "supplier_sku": i.supplier_sku,
                # 退款（行级）：已退数量 / 剩余可退数量
                "refunded_quantity": int(i.refunded_quantity or 0),
                "refundable_quantity": _item_refundable_quantity(i),
                # 采购（行级）：None=未采购 / requested=在途 / received=已入库
                "procurement_status": i.procurement_status,
                "procurement_requested_at": (
                    i.procurement_requested_at.isoformat() if i.procurement_requested_at else None
                ),
                "procurement_received_at": (
                    i.procurement_received_at.isoformat() if i.procurement_received_at else None
                ),
                "procurement_cost": float(i.procurement_cost) if i.procurement_cost is not None else None,
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
    async def _restock_items(db: AsyncSession, pairs: list[tuple[ORMOrderItem, int]]) -> None:
        """按 (行, 数量) 回补本地库存（取消 / 退款勾选 restock 时调用）。

        代发行（dropship）下单时未扣减本地库存，回补时同样跳过。
        """
        rows = [
            (item, int(qty))
            for item, qty in pairs
            if int(qty) > 0
            and item.product_id is not None
            and (item.fulfillment_mode or _FULFILLMENT_SELF) != _FULFILLMENT_DROPSHIP
        ]
        if not rows:
            return
        product_ids = [cast(int, item.product_id) for item, _ in rows]
        products = (
            (await db.execute(select(ORMProduct).where(ORMProduct.id.in_(product_ids)).with_for_update()))
            .scalars()
            .all()
        )
        product_map = {cast(int, p.id): p for p in products}
        for item, qty in rows:
            product = product_map.get(cast(int, item.product_id))
            if product is not None and product.inventory is not None:
                product.inventory = cast(Any, product.inventory + qty)
        await db.flush()

    @staticmethod
    async def _restore_inventory(db: AsyncSession, order: ORMOrder) -> None:
        """终止履约（取消 / 审核拒绝）时回补库存。

        按「行数量 - 退款流程中已 restock 回补的数量」回补，避免与退款重复入库；
        已退款但未回补的货在取消语义下同样退回仓库。
        """
        restocked = _restocked_quantity_map(order)
        pairs = [(i, max(int(i.quantity or 0) - restocked.get(str(i.id), 0), 0)) for i in (order.items or [])]
        await SQLAlchemyCustomerOrderRepository._restock_items(db, pairs)

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
            .where(ORMOrder.user_id == user_id, ORMOrder.deleted_at.is_(None))
            .options(selectinload(ORMOrder.items))
            .order_by(ORMOrder.created_at.desc())
        )
        count_stmt = (
            select(func.count()).select_from(ORMOrder).where(ORMOrder.user_id == user_id, ORMOrder.deleted_at.is_(None))
        )
        if status:
            stmt = stmt.where(ORMOrder.status == status)
            count_stmt = count_stmt.where(ORMOrder.status == status)
        total = int((await db.execute(count_stmt)).scalar_one())
        rows = (await db.execute(stmt.offset((page - 1) * page_size).limit(page_size))).scalars().all()
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
        payment_method: str | None = None,
    ) -> ORMOrder:
        """Create an order with server-side price snapshots and inventory deduction.

        Raises:
            APIError: PRODUCT_UNAVAILABLE / INSUFFICIENT_STOCK / ORDER_EMPTY on validation failure.
        """
        if not lines:
            raise APIError(ErrorCode.ORDER_EMPTY, message="Order has no items.")
        product_ids = [cast(int, line["product_id"]) for line in lines]
        products = (
            (await db.execute(select(ORMProduct).where(ORMProduct.id.in_(product_ids)).with_for_update()))
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
            # 一件代发商品不占本地库存：跳过库存校验（PLAN-DUAL-FULFILLMENT D3）
            if (product.fulfillment_mode or _FULFILLMENT_SELF) == _FULFILLMENT_DROPSHIP:
                continue
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
            payment_status="unpaid",
            payment_method=payment_method or None,
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
            item_mode = product.fulfillment_mode or _FULFILLMENT_SELF
            item = ORMOrderItem(
                id=uuid4(),
                order_id=order.id,
                product_id=product.id,
                name=product.name,
                sku=product.sku or "",
                price=unit_price,
                quantity=quantity,
                image=SQLAlchemyCustomerOrderRepository._first_image(product),
                # 履约快照：固化下单时的来源，商品后续改履约方式不影响历史订单
                fulfillment_mode=item_mode,
                supplier_id=product.supplier_id if item_mode == _FULFILLMENT_DROPSHIP else None,
                supplier_sku=product.supplier_sku if item_mode == _FULFILLMENT_DROPSHIP else None,
            )
            db.add(item)
            items.append(item)
            subtotal += unit_price * quantity
            # 只有自采购行扣减本地库存；代发行不扣
            if item_mode != _FULFILLMENT_DROPSHIP and product.inventory is not None:
                product.inventory = cast(Any, product.inventory - quantity)

        shipping_cost = Decimal("0") if subtotal > _FREE_SHIPPING_THRESHOLD else Decimal(str(_FLAT_SHIPPING))
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

        await SQLAlchemyCustomerOrderRepository._restore_inventory(db, order)
        return order

    @staticmethod
    async def mark_paid(
        db: AsyncSession,
        order: ORMOrder,
        payment_method: str,
        payment_intent_id: str | None = None,
    ) -> ORMOrder:
        """Mark an order paid and move pending -> confirmed (industry: paid=confirmed).

        Caller must hold the row lock (with_for_update) before invoking.
        """
        if order.payment_status == "paid":
            raise APIError(ErrorCode.ORDER_ALREADY_PAID, message="Order has already been paid.")
        if order.status not in _PAYABLE_STATUSES:
            raise APIError(
                ErrorCode.ORDER_NOT_PAYABLE,
                message=f"Order cannot be paid in state '{order.status}'.",
            )
        now = SQLAlchemyCustomerOrderRepository._now()
        order.payment_status = cast(Any, "paid")
        order.status = cast(Any, "confirmed")
        order.payment_method = cast(Any, payment_method)
        if payment_intent_id:
            order.payment_intent_id = cast(Any, payment_intent_id)
        order.paid_at = cast(Any, now)
        order.confirmed_at = cast(Any, now)
        order.updated_at = cast(Any, now)
        await db.flush()
        return order

    @staticmethod
    async def confirm_receipt(db: AsyncSession, order: ORMOrder) -> ORMOrder:
        """Customer confirms receipt: shipped -> delivered (order completed)."""
        if order.status not in _CONFIRMABLE_STATUSES:
            raise APIError(
                ErrorCode.ORDER_NOT_CONFIRMABLE,
                message=f"Order cannot be confirmed in state '{order.status}'.",
            )
        now = SQLAlchemyCustomerOrderRepository._now()
        order.status = cast(Any, "delivered")
        order.delivered_at = cast(Any, now)
        order.updated_at = cast(Any, now)
        await db.flush()
        return order

    @staticmethod
    async def mark_shipped(
        db: AsyncSession,
        order: ORMOrder,
        tracking_number: str | None = None,
        carrier: str | None = None,
    ) -> ORMOrder:
        """Admin ships an order: confirmed/processing -> shipped（pending 未付款不可发货）。"""
        if order.status not in {"confirmed", "processing"}:
            raise APIError(
                ErrorCode.ORDER_NOT_CANCELLABLE,
                message=f"Order cannot be shipped in state '{order.status}'.",
            )
        now = SQLAlchemyCustomerOrderRepository._now()
        order.status = cast(Any, "shipped")
        order.shipped_at = cast(Any, now)
        order.updated_at = cast(Any, now)
        if tracking_number:
            order.tracking_number = cast(Any, tracking_number)
        if carrier:
            review = dict(order.review_status or {})
            review["carrier"] = carrier
            order.review_status = cast(Any, review)
        await db.flush()
        return order

    @staticmethod
    async def admin_review_order(
        db: AsyncSession,
        order: ORMOrder,
        approved: bool,
        reason: str | None = None,
        reviewed_by: str | None = None,
        refund: bool | None = None,
    ) -> ORMOrder:
        """Admin review flow: confirmed -> processing (approved) / cancelled (rejected).

        拒绝即履约终止，与后台取消语义完全一致，因此复用 ``admin_cancel_order``
        这一唯一实现（终止 + 回补库存 + 按 refund 决定是否全额退款）；
        refund=None 表示「有可退余额即自动全额退款」，refund=False 保留款项（如违约扣款）。
        """
        if order.status not in _ADMIN_REVIEWABLE_STATUSES:
            raise APIError(
                ErrorCode.ORDER_INVALID_STATE,
                message=f"Order cannot be reviewed in state '{order.status}'.",
            )
        now = SQLAlchemyCustomerOrderRepository._now()
        # 先落审核审计字段：拒绝分支复用取消实现时会保留这里写入的 review 内容
        review = dict(order.review_status or {})
        review["reviewed_by"] = reviewed_by or "admin"
        review["approved"] = bool(approved)
        review["reason"] = reason or ""
        review["reviewed_at"] = now.isoformat()
        order.review_status = cast(Any, review)
        if not approved:
            # 拒绝 = 履约终止：复用「取消」唯一实现（终止 + 默认全额退款 + 回补库存）
            return await SQLAlchemyCustomerOrderRepository.admin_cancel_order(
                db,
                order,
                reason=reason,
                refund=refund,
                cancelled_by=reviewed_by or "admin",
            )
        order.status = cast(Any, "processing")
        order.updated_at = cast(Any, now)
        await db.flush()
        return order

    @staticmethod
    def _resolve_procure_targets(order: ORMOrder, item_ids: list[str] | None) -> list[ORMOrderItem]:
        """定位可采购行：仅 dropship 行；未指定 item_ids 时取全部未采购行。"""
        dropship_rows = [
            i for i in (order.items or []) if (i.fulfillment_mode or _FULFILLMENT_SELF) == _FULFILLMENT_DROPSHIP
        ]
        if not item_ids:
            return [i for i in dropship_rows if i.procurement_status is None]
        by_id = {str(i.id): i for i in dropship_rows}
        targets: list[ORMOrderItem] = []
        for raw in item_ids:
            item = by_id.get(str(raw))
            if item is None:
                raise APIError(
                    ErrorCode.VALIDATION_ERROR,
                    message="Procurement target must be an existing dropship order item.",
                )
            if item.procurement_status == "received":
                raise APIError(ErrorCode.ORDER_INVALID_STATE, message=f"Item '{item.name}' is already received.")
            targets.append(item)
        return targets

    @staticmethod
    async def admin_procure_order(
        db: AsyncSession,
        order: ORMOrder,
        item_ids: list[str] | None = None,
        supplier_id: str | None = None,
        supplier_sku: str | None = None,
        cost: float | None = None,
    ) -> ORMOrder:
        """行级推送采购（仅代发行）：写行级采购状态 requested，**不迁移订单主状态**。

        采购是订单的旁支履约动作（对齐 Shopify PO / 聚水潭采购单）：
        - 载体是商品行而非订单主状态，采购失败/在途都不影响订单发货；
        - 历史实现把主状态置为 procuring 导致订单卡死，仅保留复位兼容。
        """
        if order.status not in _PROCURE_ORDER_STATUSES:
            raise APIError(
                ErrorCode.ORDER_INVALID_STATE,
                message=f"Order cannot be pushed to procurement in state '{order.status}'.",
            )
        targets = SQLAlchemyCustomerOrderRepository._resolve_procure_targets(order, item_ids)
        if not targets:
            raise APIError(ErrorCode.VALIDATION_ERROR, message="No purchasable dropship item found.")

        parsed_supplier: UUID | None = None
        if supplier_id and supplier_id.strip():
            try:
                parsed_supplier = UUID(supplier_id.strip())
            except ValueError as exc:
                raise APIError(ErrorCode.VALIDATION_ERROR, message="Supplier ID must be a valid UUID.") from exc

        now = SQLAlchemyCustomerOrderRepository._now()
        for item in targets:
            if parsed_supplier is not None:
                item.supplier_id = cast(Any, parsed_supplier)
            if supplier_sku and supplier_sku.strip():
                item.supplier_sku = cast(Any, supplier_sku.strip())
            if cost is not None:
                item.procurement_cost = cast(Any, cost)
            item.procurement_status = cast(Any, "requested")
            item.procurement_requested_at = cast(Any, now)
        # 历史 procure_failed / procuring 订单复位到 processing，恢复其可发货能力
        if order.status in {"procure_failed", "procuring"}:
            order.status = cast(Any, "processing")
        order.updated_at = cast(Any, now)
        await db.flush()
        return order

    @staticmethod
    async def admin_receive_procurement(
        db: AsyncSession,
        order: ORMOrder,
        item_ids: list[str] | None = None,
    ) -> ORMOrder:
        """行级采购到货确认：requested -> received（仅代发行，不影响订单主状态）。"""
        targets = [i for i in (order.items or []) if i.procurement_status == "requested"]
        if item_ids:
            wanted = {str(x) for x in item_ids}
            targets = [i for i in targets if str(i.id) in wanted]
            if len(targets) != len(wanted):
                raise APIError(
                    ErrorCode.VALIDATION_ERROR, message="One or more items are not in requested procurement state."
                )
        if not targets:
            raise APIError(ErrorCode.VALIDATION_ERROR, message="No requested procurement item found.")

        now = SQLAlchemyCustomerOrderRepository._now()
        for item in targets:
            item.procurement_status = cast(Any, "received")
            item.procurement_received_at = cast(Any, now)
        order.updated_at = cast(Any, now)
        await db.flush()
        return order

    @staticmethod
    async def admin_refund_order(
        db: AsyncSession,
        order: ORMOrder,
        reason: str | None = None,
        item_refunds: list[dict[str, Any]] | None = None,
        refund_shipping: bool = False,
        restock: bool = False,
        refunded_by: str = "admin",
        return_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> ORMOrder:
        """行级 / 部分退款（行业对齐：Shopify refundCreate）——**只做资金动作，不改订单履约状态**。

        - item_refunds: [{"order_item_id": str, "quantity": int}]，为空表示退全部剩余可退数量
        - refund_shipping: 是否同时退还剩余未退运费（行业：运费可单独退）
        - restock: 是否把本次退款数量回补本地库存（默认否；未发货终止走取消入口统一回补）
        - return_id: 售后申请单（RMA）关联，写入退款流水便于回溯
        - idempotency_key: 幂等键，同一 key 重复提交直接返回订单，不重复扣款（防双发）
        - payment_status: 全退 -> refunded；未退完 -> partially_refunded；不新增订单终态
        """
        if idempotency_key:
            # 幂等短路：退款流水已记录该 key，视为重复提交
            existing_refunds = cast(list[Any], order.refunds or [])
            for existing in existing_refunds:
                if isinstance(existing, dict) and existing.get("idempotency_key") == idempotency_key:
                    return order
        if order.payment_status not in _REFUNDABLE_PAYMENT_STATUSES:
            raise APIError(ErrorCode.ORDER_INVALID_STATE, message="Order has no paid amount to refund.")
        if order.status in _REFUND_BLOCKED_ORDER_STATUSES:
            raise APIError(
                ErrorCode.ORDER_INVALID_STATE,
                message=f"Order cannot be refunded in state '{order.status}'.",
            )

        plan: list[tuple[ORMOrderItem, int]] = []
        if item_refunds:
            by_id = {str(i.id): i for i in (order.items or [])}
            for entry in item_refunds:
                item = by_id.get(str(entry.get("order_item_id")))
                if item is None:
                    raise APIError(ErrorCode.VALIDATION_ERROR, message="Refund item does not belong to this order.")
                quantity = int(entry.get("quantity") or 0)
                if quantity <= 0:
                    raise APIError(ErrorCode.VALIDATION_ERROR, message="Refund quantity must be positive.")
                if quantity > _item_refundable_quantity(item):
                    raise APIError(
                        ErrorCode.VALIDATION_ERROR,
                        message=f"Refund quantity exceeds refundable quantity for '{item.name}'.",
                    )
                plan.append((item, quantity))
        else:
            plan = [(i, _item_refundable_quantity(i)) for i in (order.items or []) if _item_refundable_quantity(i) > 0]
        if not plan:
            raise APIError(ErrorCode.VALIDATION_ERROR, message="Nothing left to refund.")

        goods_amount, tax_amount, shipping_amount, amount = _refund_amount_breakdown(order, plan, refund_shipping)
        if amount <= 0:
            raise APIError(ErrorCode.VALIDATION_ERROR, message="Refund amount must be positive.")
        if amount > _order_refundable_amount(order):
            raise APIError(ErrorCode.VALIDATION_ERROR, message="Refund amount exceeds refundable balance.")

        now = SQLAlchemyCustomerOrderRepository._now()
        for item, quantity in plan:
            item.refunded_quantity = cast(Any, int(item.refunded_quantity or 0) + quantity)
        entry = {
            "id": str(uuid4()),
            "amount": float(amount),
            "goods_amount": float(goods_amount),
            "tax_amount": float(tax_amount),
            "shipping_amount": float(shipping_amount),
            "items": [
                {
                    "order_item_id": str(i.id),
                    "name": i.name,
                    "quantity": quantity,
                    "amount": float(_money(i.price) * quantity),
                }
                for i, quantity in plan
            ],
            "reason": reason or "",
            "refunded_by": refunded_by,
            "return_id": return_id,
            "idempotency_key": idempotency_key,
            "refunded_at": now.isoformat(),
            "restock": bool(restock),
        }
        order.refunds = cast(Any, [*(order.refunds or []), entry])
        refunded_total = _money(order.refunded_amount) + amount
        order.refunded_amount = cast(Any, refunded_total)
        order.payment_status = cast(
            Any, "refunded" if refunded_total >= _money(order.total) - _CENTS else "partially_refunded"
        )
        review = dict(order.review_status or {})
        review["refunded_by"] = refunded_by
        review["refund_reason"] = reason or ""
        review["refunded_at"] = now.isoformat()
        order.review_status = cast(Any, review)
        order.updated_at = cast(Any, now)
        await db.flush()
        if restock:
            await SQLAlchemyCustomerOrderRepository._restock_items(db, plan)
        return order

    @staticmethod
    async def admin_cancel_order(
        db: AsyncSession,
        order: ORMOrder,
        reason: str | None = None,
        refund: bool | None = None,
        restock: bool = True,
        cancelled_by: str = "admin",
    ) -> ORMOrder:
        """后台取消订单（履约终止）：可选择同时退款，是「取消 / 退款」的合并入口。

        - 语义合并：取消不再自带一套独立的退款逻辑，需要退款时复用 admin_refund_order（同一实现），
          取消自身只保留履约终止 + 库存回补语义，消除与退款的重复实现。
        - refund=None：有已收款项且仍有可退余额时自动退款（行业：Refund and cancel）
        - 库存：按「行数量 - 已 restock 数量」回补，已退款未回补的货在取消语义下退回仓库
        """
        if order.status not in _ADMIN_CANCELLABLE_STATUSES:
            raise APIError(
                ErrorCode.ORDER_NOT_CANCELLABLE,
                message=f"Order cannot be cancelled in state '{order.status}'.",
            )
        has_refundable = order.payment_status in _REFUNDABLE_PAYMENT_STATUSES and _order_refundable_amount(order) > 0
        should_refund = has_refundable if refund is None else bool(refund)
        now = SQLAlchemyCustomerOrderRepository._now()
        if should_refund and has_refundable:
            await SQLAlchemyCustomerOrderRepository.admin_refund_order(
                db,
                order,
                reason=reason,
                item_refunds=None,
                refund_shipping=True,
                restock=False,
                refunded_by=cancelled_by,
            )
        order.status = cast(Any, "cancelled")
        review = dict(order.review_status or {})
        review["cancelled_by"] = cancelled_by
        review["cancelled_reason"] = reason or ""
        review["refund_skipped"] = bool(has_refundable and not should_refund)
        order.review_status = cast(Any, review)
        order.updated_at = cast(Any, now)
        await db.flush()
        if restock:
            await SQLAlchemyCustomerOrderRepository._restore_inventory(db, order)
        return order

    @staticmethod
    async def update_shipping_address(
        db: AsyncSession,
        order: ORMOrder,
        shipping_address: dict[str, object],
    ) -> ORMOrder:
        """Update the shipping address of an unshipped order.

        Raises:
            APIError: ORDER_NOT_EDITABLE when the order is already shipped / cancelled.
        """
        if order.status not in _EDITABLE_SHIPPING_STATUSES:
            raise APIError(
                ErrorCode.ORDER_NOT_EDITABLE,
                message=f"Order cannot be edited in state '{order.status}'.",
            )
        if not shipping_address:
            raise APIError(ErrorCode.VALIDATION_ERROR, message="Shipping address cannot be empty.")
        order.shipping_address = cast(Any, dict(shipping_address))
        order.updated_at = cast(Any, SQLAlchemyCustomerOrderRepository._now())
        await db.flush()
        return order

    @staticmethod
    async def soft_delete_order(db: AsyncSession, order: ORMOrder) -> ORMOrder:
        """Soft-delete (archive) an order visible to the customer.

        Industry-aligned rule: only completed (delivered) or cancelled orders
        may be deleted from the customer's order list.
        """
        if order.status not in _DELETABLE_STATUSES:
            raise APIError(
                ErrorCode.ORDER_NOT_DELETABLE,
                message="Only completed or cancelled orders can be deleted.",
            )
        now = SQLAlchemyCustomerOrderRepository._now()
        order.deleted_at = cast(Any, now)
        order.updated_at = cast(Any, now)
        await db.flush()
        return order

    @staticmethod
    async def list_shipments(db: AsyncSession, order_id: UUID) -> list[ORMShipment]:
        rows = (
            (
                await db.execute(
                    select(ORMShipment).where(ORMShipment.order_id == order_id).order_by(ORMShipment.created_at.asc())
                )
            )
            .scalars()
            .all()
        )
        return list(rows)

    @staticmethod
    def _generate_order_number() -> str:
        stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        return f"FG{stamp}{secrets.token_hex(3).upper()}"
