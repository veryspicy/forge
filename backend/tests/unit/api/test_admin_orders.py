# mypy: ignore-errors
"""Unit tests for Admin Orders API (list / review / procure / refund)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

from forge.main import dependencies


class _FakeItem:
    """Minimal in-memory order line consumed by repo helpers + _order_to_dict.

    Default to a dropship line so procurement / refund flows (both line-level) have
    something to operate on.
    """

    def __init__(self, *, fulfillment_mode: str = "dropship") -> None:
        self.id = UUID("a1b2c3d4-0000-4000-8000-000000000001")
        self.product_id = 1
        self.name = "Test Product"
        self.sku = "SKU-1"
        self.price = Decimal("10.00")
        self.quantity = 1
        self.image = None
        self.fulfillment_mode = fulfillment_mode
        self.supplier_id = None
        self.supplier_sku = None
        self.refunded_quantity = 0
        self.procurement_status = None
        self.procurement_requested_at = None
        self.procurement_received_at = None
        self.procurement_cost = None


class _FakeOrder:
    """Minimal in-memory order object consumed by repo methods + _order_to_dict."""

    def __init__(self, status: str = "confirmed", items: list[object] | None = None) -> None:
        self.id = UUID("d290f1ee-6c54-4b01-90e6-d701748f0851")
        self.order_number = "FG-TEST-0001"
        self.user_id = UUID("d290f1ee-6c54-4b01-90e6-d701748f0851")
        self.subtotal = Decimal("10.00")
        self.tax = Decimal("0.00")
        self.shipping_cost = Decimal("0.00")
        self.discount = Decimal("0.00")
        self.total = Decimal("10.00")
        self.currency = "USD"
        self.status = status
        self.payment_status = "paid"
        self.payment_method = "card"
        self.payment_intent_id = None
        self.paid_at = datetime.now()
        self.refunded_amount = Decimal("0.00")
        self.refunds: list[object] = []
        self.confirmed_at = datetime.now()
        self.shipped_at = None
        self.delivered_at = None
        self.deleted_at = None
        self.tracking_number = None
        self.review_status: dict[str, object] = {}
        self.procurement_info: dict[str, object] = {}
        self.shipping_address: dict[str, object] = {}
        self.items: list[object] = items if items is not None else []
        self.created_at = datetime.now()
        self.updated_at = datetime.now()


def _setup_auth(test_client, role: str = "super_admin"):
    async def _fake_get_db():
        yield AsyncMock()

    async def _fake_admin():
        return {"id": UUID("d290f1ee-6c54-4b01-90e6-d701748f0851"), "role": role, "roles": [role]}

    test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
    test_client.app.dependency_overrides[dependencies.get_current_admin] = _fake_admin


def _fake_db_for_order(order: _FakeOrder) -> AsyncMock:
    """AsyncMock db whose execute resolves to the given order (404 path returns None)."""
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = order
    db.execute.return_value = result
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.flush = AsyncMock()
    return db


class TestAdminOrdersAPI:
    """Test /api/admin/v1/orders endpoints (simplified: list only)."""

    def test_list_orders_success(self, test_client):
        from forge.infrastructure.persistence.repositories.order_repo import SQLAlchemyOrderRepository
        from forge.infrastructure.persistence.repositories.return_repo import SQLAlchemyReturnRepository

        _setup_auth(test_client)
        try:
            with (
                patch.object(
                    SQLAlchemyOrderRepository,
                    "list_orders",
                    new_callable=AsyncMock,
                    return_value={"items": [{"id": "o1", "status": "PENDING"}], "total": 1},
                ),
                # 列表接口新增售后摘要聚合，单测以空摘要替身隔离 DB 依赖
                patch.object(
                    SQLAlchemyReturnRepository,
                    "summaries_by_order_ids",
                    new_callable=AsyncMock,
                    return_value={},
                ),
            ):
                resp = test_client.get("/api/admin/v1/orders/")
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_orders_unauthorized(self, test_client):
        resp = test_client.get("/api/admin/v1/orders/")
        assert resp.status_code == 401

    def test_orders_forbidden_no_role(self, test_client):
        """普通用户无后台角色访问 Orders 接口 → 403"""
        from fastapi import HTTPException

        async def _fake_admin_403():
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        test_client.app.dependency_overrides[dependencies.get_current_admin] = _fake_admin_403
        try:
            response = test_client.get("/api/admin/v1/orders/")
        finally:
            test_client.app.dependency_overrides.clear()
        assert response.status_code == 403

    def test_list_orders_passes_status_and_search(self, test_client):
        from forge.infrastructure.persistence.repositories.order_repo import SQLAlchemyOrderRepository

        _setup_auth(test_client)
        with patch.object(
            SQLAlchemyOrderRepository,
            "list_orders",
            new_callable=AsyncMock,
            return_value={"items": [], "total": 0},
        ) as mocked:
            resp = test_client.get("/api/admin/v1/orders/?status=CONFIRMED&search=abc")
        test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert mocked.await_args.kwargs["status"] == "confirmed"
        assert mocked.await_args.kwargs["search"] == "abc"

    def test_export_orders_returns_csv_with_filter(self, test_client):
        from forge.infrastructure.persistence.repositories.order_repo import SQLAlchemyOrderRepository

        _setup_auth(test_client)
        with patch.object(
            SQLAlchemyOrderRepository,
            "list_all_orders",
            new_callable=AsyncMock,
            return_value=[_FakeOrder(status="shipped")],
        ) as mocked:
            resp = test_client.get("/api/admin/v1/orders/export?status=SHIPPED")
        test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/csv")
        assert 'attachment; filename="orders_' in resp.headers["content-disposition"]
        body = resp.content.decode("utf-8")
        assert body.startswith("\ufeff")
        assert "order_number" in body
        assert "FG-TEST-0001" in body
        assert mocked.await_args.kwargs["status"] == "shipped"

    def test_review_approve_moves_confirmed_to_processing(self, test_client):
        order = _FakeOrder(status="confirmed")

        async def _fake_get_db():
            yield _fake_db_for_order(order)

        _setup_auth(test_client)
        test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
        try:
            resp = test_client.post("/api/admin/v1/orders/FG-TEST-0001/review", json={"approved": True})
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "processing"
        assert body["review_status"]["approved"] is True

    def test_review_reject_moves_to_cancelled(self, test_client):
        order = _FakeOrder(status="confirmed", items=[_FakeItem()])

        async def _fake_get_db():
            yield _fake_db_for_order(order)

        _setup_auth(test_client)
        test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
        try:
            resp = test_client.post(
                "/api/admin/v1/orders/FG-TEST-0001/review",
                json={"approved": False, "reason": "fraud flag"},
            )
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "cancelled"
        assert body["review_status"]["approved"] is False
        assert body["review_status"]["reason"] == "fraud flag"

    def test_review_reject_requires_reason(self, test_client):
        from forge.infrastructure.persistence.repositories.order_repo import SQLAlchemyCustomerOrderRepository

        order = _FakeOrder(status="confirmed")

        async def _fake_get_db():
            yield _fake_db_for_order(order)

        _setup_auth(test_client)
        test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
        try:
            with patch.object(
                SQLAlchemyCustomerOrderRepository,
                "admin_review_order",
                new_callable=AsyncMock,
            ) as review_mock:
                resp = test_client.post(
                    "/api/admin/v1/orders/FG-TEST-0001/review",
                    json={"approved": False, "reason": "   "},
                )
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 422, resp.text
        assert order.status == "confirmed"
        review_mock.assert_not_awaited()

    def test_review_invalid_state_returns_409(self, test_client):
        order = _FakeOrder(status="shipped")

        async def _fake_get_db():
            yield _fake_db_for_order(order)

        _setup_auth(test_client)
        test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
        try:
            resp = test_client.post("/api/admin/v1/orders/FG-TEST-0001/review", json={"approved": True})
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 409

    def test_procure_marks_dropship_item_requested(self, test_client):
        order = _FakeOrder(status="processing", items=[_FakeItem()])

        async def _fake_get_db():
            yield _fake_db_for_order(order)

        _setup_auth(test_client)
        test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
        try:
            resp = test_client.post(
                "/api/admin/v1/orders/FG-TEST-0001/procure",
                json={
                    "supplier_id": "3f2504e0-4f89-11d3-9a0c-0305e82c3301",
                    "supplier_sku": "SKU-A",
                    "cost": 12.5,
                },
            )
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200
        body = resp.json()
        # 采购是行级旁支动作：只写行状态，不迁移订单主状态
        assert body["status"] == "processing"
        item = body["items"][0]
        assert item["procurement_status"] == "requested"
        assert item["supplier_sku"] == "SKU-A"
        assert item["procurement_cost"] == 12.5

    def test_procure_retry_allowed_from_procure_failed(self, test_client):
        order = _FakeOrder(status="procure_failed", items=[_FakeItem()])

        async def _fake_get_db():
            yield _fake_db_for_order(order)

        _setup_auth(test_client)
        test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
        try:
            resp = test_client.post(
                "/api/admin/v1/orders/FG-TEST-0001/procure",
                json={"supplier_id": "3f2504e0-4f89-11d3-9a0c-0305e82c3301"},
            )
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"][0]["procurement_status"] == "requested"
        # 历史脏状态复位，订单恢复可发货
        assert body["status"] == "processing"

    def test_procure_requires_supplier_id(self, test_client):
        order = _FakeOrder(status="processing")

        async def _fake_get_db():
            yield _fake_db_for_order(order)

        _setup_auth(test_client)
        test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
        try:
            resp = test_client.post("/api/admin/v1/orders/FG-TEST-0001/procure", json={})
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 422

    def test_procure_invalid_state_returns_409(self, test_client):
        order = _FakeOrder(status="shipped")

        async def _fake_get_db():
            yield _fake_db_for_order(order)

        _setup_auth(test_client)
        test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
        try:
            resp = test_client.post("/api/admin/v1/orders/FG-TEST-0001/procure", json={"supplier_id": "SUP-1"})
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 409

    def test_refund_full_amount_marks_payment_refunded(self, test_client):
        order = _FakeOrder(status="procuring", items=[_FakeItem()])

        async def _fake_get_db():
            yield _fake_db_for_order(order)

        _setup_auth(test_client)
        test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
        try:
            resp = test_client.post("/api/admin/v1/orders/FG-TEST-0001/refund", json={"reason": "user request"})
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200
        body = resp.json()
        # 退款只做资金动作：支付态变化，订单履约状态不变
        assert body["payment_status"] == "refunded"
        assert body["refunded_amount"] == 10.0
        assert body["status"] == "procuring"
        assert body["review_status"]["refund_reason"] == "user request"

    def test_refund_shipped_order_allowed_after_sales(self, test_client):
        order = _FakeOrder(status="shipped", items=[_FakeItem()])

        async def _fake_get_db():
            yield _fake_db_for_order(order)

        _setup_auth(test_client)
        test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
        try:
            resp = test_client.post("/api/admin/v1/orders/FG-TEST-0001/refund", json={"reason": "after sales"})
        finally:
            test_client.app.dependency_overrides.clear()
        # 已发货订单支持售后退款（阻断仅限 cancelled / refunded）
        assert resp.status_code == 200
        body = resp.json()
        assert body["payment_status"] == "refunded"
        assert body["status"] == "shipped"

    def test_ship_multipackage_moves_order_to_shipped(self, test_client):
        from forge.api.admin.v1.orders import ORMShipment
        from forge.infrastructure.persistence.repositories.order_repo import SQLAlchemyCustomerOrderRepository

        order = _FakeOrder(status="procuring")
        order.review_status = {"approved": True}  # 已审核通过：本用例只验证多包裹登记
        db = _fake_db_for_order(order)
        db.add = MagicMock()

        async def _fake_get_db():
            yield db

        _setup_auth(test_client)
        test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
        try:
            with patch.object(
                SQLAlchemyCustomerOrderRepository,
                "mark_shipped",
                new_callable=AsyncMock,
            ) as mocked:

                async def _mark_shipped(db, order, tracking_number=None, carrier=None):
                    order.status = "shipped"
                    order.tracking_number = tracking_number
                    return order

                mocked.side_effect = _mark_shipped
                resp = test_client.post(
                    "/api/admin/v1/orders/FG-TEST-0001/ship",
                    json={
                        "packages": [
                            {"carrier": "DHL", "tracking_number": "TRK-1"},
                            {"carrier": "DHL", "tracking_number": "TRK-2"},
                        ]
                    },
                )
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert resp.json()["status"] == "shipped"
        mocked.assert_awaited_once()
        added = [call.args[0] for call in db.add.call_args_list]
        assert len(added) == 2
        assert all(isinstance(s, ORMShipment) for s in added)
        assert [s.tracking_number for s in added] == ["TRK-1", "TRK-2"]

    def test_ship_append_package_keeps_shipped_state(self, test_client):
        from forge.infrastructure.persistence.repositories.order_repo import SQLAlchemyCustomerOrderRepository

        order = _FakeOrder(status="shipped")
        order.review_status = {"approved": True}  # 已审核通过：本用例只验证补发包裹登记
        db = _fake_db_for_order(order)
        db.add = MagicMock()

        async def _fake_get_db():
            yield db

        _setup_auth(test_client)
        test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
        try:
            with patch.object(
                SQLAlchemyCustomerOrderRepository,
                "mark_shipped",
                new_callable=AsyncMock,
            ) as mocked:
                resp = test_client.post(
                    "/api/admin/v1/orders/FG-TEST-0001/ship",
                    json={"packages": [{"carrier": "UPS", "tracking_number": "TRK-3"}]},
                )
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert resp.json()["status"] == "shipped"
        mocked.assert_not_awaited()
        assert db.add.call_count == 1

    def test_ship_blocked_when_order_not_reviewed(self, test_client):
        """硬门禁：订单未审核通过时禁止发货（不依赖站点开关）。"""
        from forge.infrastructure.persistence.repositories.order_repo import SQLAlchemyCustomerOrderRepository

        order = _FakeOrder(status="confirmed")  # review_status 默认空 = 未审核
        db = _fake_db_for_order(order)

        async def _fake_get_db():
            yield db

        _setup_auth(test_client)
        test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
        try:
            with patch.object(
                SQLAlchemyCustomerOrderRepository,
                "mark_shipped",
                new_callable=AsyncMock,
            ) as mocked:
                resp = test_client.post(
                    "/api/admin/v1/orders/FG-TEST-0001/ship",
                    json={"packages": [{"carrier": "UPS", "tracking_number": "TRK-9"}]},
                )
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 409
        mocked.assert_not_awaited()
        assert db.add.call_count == 0

    def test_ship_requires_packages(self, test_client):
        order = _FakeOrder(status="confirmed")

        async def _fake_get_db():
            yield _fake_db_for_order(order)

        _setup_auth(test_client)
        test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
        try:
            resp = test_client.post("/api/admin/v1/orders/FG-TEST-0001/ship", json={"tracking_number": "OLD"})
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 422

    def test_detail_returns_shipments_and_timeline(self, test_client):
        from forge.infrastructure.persistence.repositories.order_repo import SQLAlchemyCustomerOrderRepository
        from forge.infrastructure.persistence.repositories.return_repo import SQLAlchemyReturnRepository

        order = _FakeOrder(status="shipped")
        order.shipped_at = datetime.now()

        async def _fake_get_db():
            yield _fake_db_for_order(order)

        _setup_auth(test_client)
        test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
        try:
            with (
                patch.object(
                    SQLAlchemyCustomerOrderRepository,
                    "list_shipments",
                    new_callable=AsyncMock,
                    return_value=[],
                ),
                # 详情新增售后区块，单测以替身隔离 DB 依赖
                patch.object(
                    SQLAlchemyReturnRepository,
                    "list_by_order",
                    new_callable=AsyncMock,
                    return_value=[],
                ),
            ):
                resp = test_client.get("/api/admin/v1/orders/FG-TEST-0001")
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200
        body = resp.json()
        assert body["shipments"] == []
        timeline_statuses = [ev["status"] for ev in body["timeline"]]
        assert timeline_statuses[0] == "pending"
        assert "shipped" in timeline_statuses

    def test_detail_timeline_includes_refunded_for_refunded_order(self, test_client):
        from forge.infrastructure.persistence.repositories.order_repo import SQLAlchemyCustomerOrderRepository
        from forge.infrastructure.persistence.repositories.return_repo import SQLAlchemyReturnRepository

        order = _FakeOrder(status="refunded")

        async def _fake_get_db():
            yield _fake_db_for_order(order)

        _setup_auth(test_client)
        test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
        try:
            with (
                patch.object(
                    SQLAlchemyCustomerOrderRepository,
                    "list_shipments",
                    new_callable=AsyncMock,
                    return_value=[],
                ),
                # 详情新增售后区块，单测以替身隔离 DB 依赖
                patch.object(
                    SQLAlchemyReturnRepository,
                    "list_by_order",
                    new_callable=AsyncMock,
                    return_value=[],
                ),
            ):
                resp = test_client.get("/api/admin/v1/orders/FG-TEST-0001")
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200
        statuses = [ev["status"] for ev in resp.json()["timeline"]]
        assert "refunded" in statuses
