"""Unit tests for Admin Suppliers API."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from forge.main import dependencies

SUPPLIER_ID = str(uuid4())


def _setup_auth(test_client):
    async def _fake_get_db():
        yield AsyncMock()
    async def _fake_user_id():
        from uuid import UUID
        return UUID("d290f1ee-6c54-4b01-90e6-d701748f0851")
    test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
    test_client.app.dependency_overrides[dependencies.get_current_user_id] = _fake_user_id


class TestAdminSuppliersAPI:
    """Test /api/admin/v1/suppliers endpoints."""

    def _mock_service(self, test_client):
        from forge.api.admin.v1 import suppliers as mod
        svc = MagicMock()
        _setup_auth(test_client)
        test_client.app.dependency_overrides[mod.get_supplier_service] = lambda: svc
        return svc

    def test_list_suppliers_success(self, test_client):
        svc = self._mock_service(test_client)
        svc.list_suppliers = AsyncMock(return_value={"items": [], "total": 0})
        try:
            resp = test_client.get("/api/admin/v1/suppliers/")
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200

    def test_get_supplier_success(self, test_client):
        svc = self._mock_service(test_client)
        svc.get_supplier = AsyncMock(
            return_value={"id": SUPPLIER_ID, "name": "Acme", "contact_email": "a@b.com",
                          "contact_phone": "123", "shipping_regions": [], "integration_type": "manual",
                          "api_config": {}, "default_currency": "USD", "payment_terms": "", "is_active": True}
        )
        try:
            resp = test_client.get(f"/api/admin/v1/suppliers/{SUPPLIER_ID}")
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert resp.json()["name"] == "Acme"

    def test_get_supplier_not_found(self, test_client):
        svc = self._mock_service(test_client)
        svc.get_supplier = AsyncMock(return_value=None)
        try:
            resp = test_client.get(f"/api/admin/v1/suppliers/{SUPPLIER_ID}")
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 404

    def test_create_supplier_success(self, test_client):
        svc = self._mock_service(test_client)
        svc.create_supplier = AsyncMock(
            return_value=MagicMock(model_dump=lambda: {"id": SUPPLIER_ID, "name": "Acme"})
        )
        try:
            resp = test_client.post(
                "/api/admin/v1/suppliers/",
                json={"name": "Acme", "contact_email": "a@b.com", "phone": "123",
                      "shipping_regions": ["AE"], "is_active": True},
            )
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 201

    def test_create_supplier_validation_error(self, test_client):
        self._mock_service(test_client)
        try:
            resp = test_client.post("/api/admin/v1/suppliers/", json={})
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 422

    def test_update_supplier_success(self, test_client):
        svc = self._mock_service(test_client)
        svc.update_supplier = AsyncMock(
            return_value=MagicMock(to_dict=lambda: {"id": SUPPLIER_ID, "name": "Acme V2"})
        )
        try:
            resp = test_client.patch(
                f"/api/admin/v1/suppliers/{SUPPLIER_ID}",
                json={"name": "Acme V2"},
            )
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200

    def test_update_supplier_not_found(self, test_client):
        svc = self._mock_service(test_client)
        svc.update_supplier = AsyncMock(return_value=None)
        try:
            resp = test_client.patch(
                f"/api/admin/v1/suppliers/{SUPPLIER_ID}",
                json={"name": "Ghost"},
            )
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 404

    def test_deactivate_supplier_success(self, test_client):
        svc = self._mock_service(test_client)
        svc.deactivate_supplier = AsyncMock(return_value=True)
        try:
            resp = test_client.post(
                f"/api/admin/v1/suppliers/{SUPPLIER_ID}/deactivate",
            )
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200

    def test_deactivate_supplier_not_found(self, test_client):
        svc = self._mock_service(test_client)
        svc.deactivate_supplier = AsyncMock(return_value=False)
        try:
            resp = test_client.post(
                f"/api/admin/v1/suppliers/{SUPPLIER_ID}/deactivate",
            )
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 404

    def test_suppliers_unauthorized(self, test_client):
        resp = test_client.get("/api/admin/v1/suppliers/")
        assert resp.status_code == 401

    def test_suppliers_forbidden_no_role(self, test_client):
        """非 ADMIN 角色访问供应商接口 → 403"""
        from fastapi import HTTPException

        async def _fake_user_id_403():
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        test_client.app.dependency_overrides[dependencies.get_current_user_id] = _fake_user_id_403
        try:
            resp = test_client.get("/api/admin/v1/suppliers/")
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 403
