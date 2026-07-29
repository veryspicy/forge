"""Unit tests for Admin Shipments API."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from forge.main import dependencies

SHIPMENT_ID = str(uuid4())
ORDER_ID = str(uuid4())


def _setup_auth(test_client):
    async def _fake_get_db():
        yield AsyncMock()
    async def _fake_user_id():
        from uuid import UUID
        return UUID("d290f1ee-6c54-4b01-90e6-d701748f0851")
    test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
    test_client.app.dependency_overrides[dependencies.get_current_user_id] = _fake_user_id


def _make_shipment_response(shipment_id=SHIPMENT_ID, order_id=ORDER_ID, status="PENDING"):
    return {
        "id": shipment_id,
        "order_id": order_id,
        "supplier_id": "supplier-1",
        "tracking_number": "TN123456",
        "carrier": "DHL",
        "tracking_url": "https://track.dhl.com/TN123456",
        "status": status,
        "estimated_delivery": None,
        "actual_delivery": None,
        "origin": "NYC",
        "destination": "DXB",
        "events": [],
        "notes": "",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }


class TestAdminShipmentsAPI:
    """Test /api/admin/v1/shipments endpoints."""

    # ---- list shipments ----
    def test_list_shipments_success(self, test_client):
        """列出物流记录"""
        from forge.api.admin.v1 import shipments as shipments_mod

        mock_service = MagicMock()
        mock_service.list_shipments = AsyncMock(
            return_value=[_make_shipment_response()]
        )
        _setup_auth(test_client)
        test_client.app.dependency_overrides[shipments_mod.get_shipment_service] = lambda: mock_service
        try:
            resp = test_client.get("/api/admin/v1/shipments/")
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["tracking_number"] == "TN123456"

    # ---- get shipment ----
    def test_get_shipment_success(self, test_client):
        """获取单条物流详情"""
        from forge.api.admin.v1 import shipments as shipments_mod

        mock_service = MagicMock()
        mock_service.get_shipment = AsyncMock(
            return_value=_make_shipment_response()
        )
        _setup_auth(test_client)
        test_client.app.dependency_overrides[shipments_mod.get_shipment_service] = lambda: mock_service
        try:
            resp = test_client.get(f"/api/admin/v1/shipments/{SHIPMENT_ID}")
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert resp.json()["carrier"] == "DHL"

    def test_get_shipment_not_found(self, test_client):
        """物流记录不存在 → 404"""
        from forge.api.admin.v1 import shipments as shipments_mod

        mock_service = MagicMock()
        mock_service.get_shipment = AsyncMock(return_value=None)
        _setup_auth(test_client)
        test_client.app.dependency_overrides[shipments_mod.get_shipment_service] = lambda: mock_service
        try:
            resp = test_client.get(f"/api/admin/v1/shipments/{SHIPMENT_ID}")
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 404

    # ---- create shipment ----
    def test_create_shipment_success(self, test_client):
        """手动录入物流单号 → 201"""
        from forge.api.admin.v1 import shipments as shipments_mod

        mock_service = MagicMock()
        mock_service.create_shipment = AsyncMock(
            return_value=_make_shipment_response()
        )
        _setup_auth(test_client)
        test_client.app.dependency_overrides[shipments_mod.get_shipment_service] = lambda: mock_service
        try:
            resp = test_client.post(
                "/api/admin/v1/shipments/",
                json={
                    "order_id": ORDER_ID,
                    "supplier_id": "supplier-1",
                    "tracking_number": "TN123456",
                    "carrier": "DHL",
                    "tracking_url": "https://track.dhl.com/TN123456",
                    "origin": "NYC",
                    "destination": "DXB",
                },
            )
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 201
        assert resp.json()["tracking_number"] == "TN123456"

    # ---- update tracking ----
    def test_update_tracking_success(self, test_client):
        """更新物流轨迹 → 200"""
        from forge.api.admin.v1 import shipments as shipments_mod

        mock_service = MagicMock()
        mock_service.update_tracking = AsyncMock(
            return_value=_make_shipment_response(status="IN_TRANSIT")
        )
        _setup_auth(test_client)
        test_client.app.dependency_overrides[shipments_mod.get_shipment_service] = lambda: mock_service
        try:
            resp = test_client.patch(
                f"/api/admin/v1/shipments/{SHIPMENT_ID}/tracking",
                json={
                    "events": [{"status": "departed", "location": "NYC"}],
                    "status": "IN_TRANSIT",
                },
            )
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert resp.json()["status"] == "IN_TRANSIT"

    def test_update_tracking_not_found(self, test_client):
        """更新不存在的物流 → 404"""
        from forge.api.admin.v1 import shipments as shipments_mod

        mock_service = MagicMock()
        mock_service.update_tracking = AsyncMock(return_value=None)
        _setup_auth(test_client)
        test_client.app.dependency_overrides[shipments_mod.get_shipment_service] = lambda: mock_service
        try:
            resp = test_client.patch(
                f"/api/admin/v1/shipments/{SHIPMENT_ID}/tracking",
                json={
                    "events": [{"status": "departed"}],
                },
            )
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 404

    # ---- unauthorized ----
    def test_shipments_unauthorized(self, test_client):
        resp = test_client.get("/api/admin/v1/shipments/")
        assert resp.status_code == 401

    # ---- forbidden (403) ----
    def test_shipments_forbidden_no_role(self, test_client):
        """普通用户无后台角色访问 Shipments 接口 → 403"""
        from fastapi import HTTPException

        async def _fake_user_id_403():
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        test_client.app.dependency_overrides[dependencies.get_current_user_id] = _fake_user_id_403
        try:
            response = test_client.get("/api/admin/v1/shipments/")
        finally:
            test_client.app.dependency_overrides.clear()
        assert response.status_code == 403
