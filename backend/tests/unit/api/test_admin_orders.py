"""Unit tests for Admin Orders API."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from forge.main import dependencies

ORDER_ID = str(uuid4())


def _setup_auth(test_client):
    async def _fake_get_db():
        yield AsyncMock()
    async def _fake_user_id():
        from uuid import UUID
        return UUID("d290f1ee-6c54-4b01-90e6-d701748f0851")
    test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
    test_client.app.dependency_overrides[dependencies.get_current_user_id] = _fake_user_id


def _make_order_dict(order_id=ORDER_ID, status="PAID"):
    return {
        "id": order_id,
        "order_number": "ORD-001",
        "user_id": "user-1",
        "status": status,
        "total_amount": 99.99,
        "currency": "USD",
        "items": [],
        "created_at": "2024-01-01T00:00:00Z",
    }


class TestAdminOrdersAPI:
    """Test /api/admin/v1/orders endpoints."""

    # ---- list orders (raw SQLAlchemy) ----
    def test_list_orders_success(self, test_client):
        _setup_auth(test_client)
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 5
        mock_scalars = MagicMock()
        mock_scalars.unique.return_value.scalars.return_value.all.return_value = [
            MagicMock(to_dict=lambda: _make_order_dict())
        ]
        mock_session.execute.side_effect = [mock_result, mock_scalars]

        async def _fake_get_db_with_mock():
            yield mock_session
        test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db_with_mock
        try:
            response = test_client.get("/api/admin/v1/orders/")
        finally:
            test_client.app.dependency_overrides.clear()
        assert response.status_code == 200

    # ---- get order ----
    def test_get_order_success(self, test_client):
        _setup_auth(test_client)
        mock_session = AsyncMock()
        orm_mock = MagicMock()
        orm_mock.to_dict.return_value = _make_order_dict()
        mock_result = MagicMock()
        mock_result.unique.return_value.scalar_one_or_none.return_value = orm_mock
        mock_session.execute.return_value = mock_result

        # Override get_db to return mock_session
        async def _fake_get_db():
            yield mock_session
        test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
        try:
            response = test_client.get(f"/api/admin/v1/orders/{ORDER_ID}")
        finally:
            test_client.app.dependency_overrides.clear()
        assert response.status_code == 200
        assert response.json()["order_number"] == "ORD-001"

    def test_get_order_not_found(self, test_client):
        _setup_auth(test_client)
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.unique.return_value.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        async def _fake_get_db():
            yield mock_session
        test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
        try:
            response = test_client.get(f"/api/admin/v1/orders/{ORDER_ID}")
        finally:
            test_client.app.dependency_overrides.clear()
        assert response.status_code == 404

    # ---- review order ----
    def test_review_order_approve(self, test_client):
        from forge.api.admin.v1 import orders as orders_mod
        from forge.application.services.order_service import OrderService

        mock_service = MagicMock()
        mock_service.review_order = AsyncMock(
            return_value=MagicMock(to_dict=lambda: _make_order_dict(status="CONFIRMED"))
        )
        _setup_auth(test_client)
        test_client.app.dependency_overrides[orders_mod.get_order_service] = lambda: mock_service
        try:
            response = test_client.post(
                f"/api/admin/v1/orders/{ORDER_ID}/review",
                json={"approved": True, "reason": "OK", "reviewed_by": "admin"},
            )
        finally:
            test_client.app.dependency_overrides.clear()
        assert response.status_code == 200

    def test_review_order_not_found(self, test_client):
        from forge.api.admin.v1 import orders as orders_mod

        mock_service = MagicMock()
        mock_service.review_order = AsyncMock(return_value=None)
        _setup_auth(test_client)
        test_client.app.dependency_overrides[orders_mod.get_order_service] = lambda: mock_service
        try:
            response = test_client.post(
                f"/api/admin/v1/orders/{ORDER_ID}/review",
                json={"approved": True, "reason": "OK"},
            )
        finally:
            test_client.app.dependency_overrides.clear()
        assert response.status_code == 404

    # ---- start procurement ----
    def test_start_procurement_success(self, test_client):
        from forge.api.admin.v1 import orders as orders_mod

        mock_service = MagicMock()
        mock_service.start_procurement = AsyncMock(
            return_value=MagicMock(to_dict=lambda: _make_order_dict(status="PROCURING"))
        )
        _setup_auth(test_client)
        test_client.app.dependency_overrides[orders_mod.get_order_service] = lambda: mock_service
        try:
            response = test_client.post(
                f"/api/admin/v1/orders/{ORDER_ID}/procure",
                json={"supplier_id": "sup-1", "supplier_sku": "SKU-1"},
            )
        finally:
            test_client.app.dependency_overrides.clear()
        assert response.status_code == 200

    def test_start_procurement_missing_supplier(self, test_client):
        """Missing supplier_id returns 422."""
        _setup_auth(test_client)
        try:
            response = test_client.post(
                f"/api/admin/v1/orders/{ORDER_ID}/procure",
                json={"supplier_sku": "SKU-1"},
            )
        finally:
            test_client.app.dependency_overrides.clear()
        assert response.status_code == 422

    # ---- procure failed ----
    def test_mark_procure_failed_success(self, test_client):
        from forge.api.admin.v1 import orders as orders_mod

        mock_service = MagicMock()
        mock_service.mark_procure_failed = AsyncMock(
            return_value=MagicMock(to_dict=lambda: _make_order_dict(status="PROCURE_FAILED"))
        )
        _setup_auth(test_client)
        test_client.app.dependency_overrides[orders_mod.get_order_service] = lambda: mock_service
        try:
            response = test_client.post(
                f"/api/admin/v1/orders/{ORDER_ID}/procure-failed",
                json={"reason": "Out of stock"},
            )
        finally:
            test_client.app.dependency_overrides.clear()
        assert response.status_code == 200

    def test_mark_procure_failed_missing_reason(self, test_client):
        """Missing reason returns 422."""
        _setup_auth(test_client)
        try:
            response = test_client.post(
                f"/api/admin/v1/orders/{ORDER_ID}/procure-failed",
                json={},
            )
        finally:
            test_client.app.dependency_overrides.clear()
        assert response.status_code == 422

    # ---- ship order ----
    def test_ship_order_success(self, test_client):
        _setup_auth(test_client)
        mock_session = AsyncMock()
        orm_mock = MagicMock()
        orm_mock.to_dict.return_value = _make_order_dict(status="SHIPPED")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = orm_mock
        mock_session.execute.return_value = mock_result

        async def _fake_get_db():
            yield mock_session
        test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
        try:
            response = test_client.post(
                f"/api/admin/v1/orders/{ORDER_ID}/ship",
                json={"tracking_number": "TRK-001", "carrier": "DHL"},
            )
        finally:
            test_client.app.dependency_overrides.clear()
        assert response.status_code == 200

    def test_ship_order_missing_tracking(self, test_client):
        """Missing tracking_number returns 422."""
        _setup_auth(test_client)
        try:
            response = test_client.post(
                f"/api/admin/v1/orders/{ORDER_ID}/ship",
                json={},
            )
        finally:
            test_client.app.dependency_overrides.clear()
        assert response.status_code == 422

    # ---- refund ----
    def test_refund_order_success(self, test_client):
        from forge.api.admin.v1 import orders as orders_mod

        mock_service = MagicMock()
        mock_service.refund_order = AsyncMock(
            return_value=MagicMock(to_dict=lambda: _make_order_dict(status="REFUNDED"))
        )
        _setup_auth(test_client)
        test_client.app.dependency_overrides[orders_mod.get_order_service] = lambda: mock_service
        try:
            response = test_client.post(
                f"/api/admin/v1/orders/{ORDER_ID}/refund",
                json={"reason": "Customer request"},
            )
        finally:
            test_client.app.dependency_overrides.clear()
        assert response.status_code == 200

    def test_refund_order_not_found(self, test_client):
        from forge.api.admin.v1 import orders as orders_mod

        mock_service = MagicMock()
        mock_service.refund_order = AsyncMock(return_value=None)
        _setup_auth(test_client)
        test_client.app.dependency_overrides[orders_mod.get_order_service] = lambda: mock_service
        try:
            response = test_client.post(
                f"/api/admin/v1/orders/{ORDER_ID}/refund",
                json={"reason": "test"},
            )
        finally:
            test_client.app.dependency_overrides.clear()
        assert response.status_code == 404

    # ---- review order: reject ----
    def test_review_order_reject(self, test_client):
        """审核拒绝: approved=False 返回 200（domain 对象由 FastAPI 序列化）"""
        from forge.api.admin.v1 import orders as orders_mod

        mock_service = MagicMock()
        mock_service.review_order = AsyncMock(
            return_value=MagicMock(to_dict=lambda: _make_order_dict(status="REJECTED"))
        )
        _setup_auth(test_client)
        test_client.app.dependency_overrides[orders_mod.get_order_service] = lambda: mock_service
        try:
            response = test_client.post(
                f"/api/admin/v1/orders/{ORDER_ID}/review",
                json={"approved": False, "reason": "不合规", "reviewed_by": "admin"},
            )
        finally:
            test_client.app.dependency_overrides.clear()
        assert response.status_code == 200

    # ---- unauthorized ----
    def test_orders_unauthorized(self, test_client):
        response = test_client.get("/api/admin/v1/orders/")
        assert response.status_code == 401

    # ---- forbidden (403) ----
    def test_orders_forbidden_no_role(self, test_client):
        """普通用户无后台角色访问 Order 接口 → 403"""
        from fastapi import HTTPException

        async def _fake_user_id_403():
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        test_client.app.dependency_overrides[dependencies.get_current_user_id] = _fake_user_id_403
        try:
            response = test_client.get("/api/admin/v1/orders/")
        finally:
            test_client.app.dependency_overrides.clear()
        assert response.status_code == 403
