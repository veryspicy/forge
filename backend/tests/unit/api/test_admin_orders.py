# mypy: ignore-errors
"""Unit tests for Admin Orders API (list / review / procure / refund)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

from forge.main import dependencies


class _FakeOrder:
    """Minimal in-memory order object consumed by repo methods + _order_to_dict."""

    def __init__(self, status: str = "confirmed") -> None:
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
        self.confirmed_at = datetime.now()
        self.shipped_at = None
        self.delivered_at = None
        self.deleted_at = None
        self.tracking_number = None
        self.review_status: dict[str, object] = {}
        self.procurement_info: dict[str, object] = {}
        self.shipping_address: dict[str, object] = {}
        self.items: list[object] = []
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

        _setup_auth(test_client)
        with patch.object(
            SQLAlchemyOrderRepository,
            "list_orders",
            new_callable=AsyncMock,
            return_value={"items": [{"id": "o1", "status": "PENDING"}], "total": 1},
        ):
            resp = test_client.get("/api/admin/v1/orders/")
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
        order = _FakeOrder(status="confirmed")

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

    def test_procure_moves_to_procuring_and_records_info(self, test_client):
        order = _FakeOrder(status="processing")

        async def _fake_get_db():
            yield _fake_db_for_order(order)

        _setup_auth(test_client)
        test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
        try:
            resp = test_client.post(
                "/api/admin/v1/orders/FG-TEST-0001/procure",
                json={"supplier_id": "SUP-1", "supplier_sku": "SKU-A", "cost": 12.5},
            )
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "procuring"
        assert body["procurement_info"]["supplier_id"] == "SUP-1"
        assert body["procurement_info"]["cost"] == 12.5

    def test_procure_retry_allowed_from_procure_failed(self, test_client):
        order = _FakeOrder(status="procure_failed")

        async def _fake_get_db():
            yield _fake_db_for_order(order)

        _setup_auth(test_client)
        test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
        try:
            resp = test_client.post("/api/admin/v1/orders/FG-TEST-0001/procure", json={"supplier_id": "SUP-1"})
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert resp.json()["status"] == "procuring"

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

    def test_refund_moves_unshipped_order_to_refunded(self, test_client):
        order = _FakeOrder(status="procuring")

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
        assert body["status"] == "refunded"
        assert body["review_status"]["refund_reason"] == "user request"

    def test_refund_shipped_order_returns_409(self, test_client):
        order = _FakeOrder(status="shipped")

        async def _fake_get_db():
            yield _fake_db_for_order(order)

        _setup_auth(test_client)
        test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
        try:
            resp = test_client.post("/api/admin/v1/orders/FG-TEST-0001/refund", json={"reason": "nope"})
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 409
