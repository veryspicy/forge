"""Unit tests for Admin Suppliers API (new static-service architecture)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

from forge.main import dependencies

SUPPLIER_ID = str(uuid4())


def _setup_auth(test_client):
    async def _fake_get_db():
        yield AsyncMock()

    async def _fake_admin():
        return {"id": UUID("d290f1ee-6c54-4b01-90e6-d701748f0851"), "role": "super_admin", "roles": ["super_admin"]}

    test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
    test_client.app.dependency_overrides[dependencies.get_current_admin] = _fake_admin


def _make_supplier(name="Acme", email="a@b.com", is_active=True):
    supplier = MagicMock()
    supplier.to_dict.return_value = {
        "id": SUPPLIER_ID,
        "name": name,
        "contact_email": email,
        "contact_phone": "123",
        "shipping_regions": [],
        "integration_type": "manual",
        "api_config": {},
        "default_currency": "USD",
        "payment_terms": "",
        "is_active": is_active,
    }
    return supplier


class TestAdminSuppliersAPI:
    """Test /api/admin/v1/suppliers endpoints."""

    def test_list_suppliers_success(self, test_client):
        from forge.infrastructure.persistence.repositories.supplier_repo import (
            SQLAlchemySupplierRepository,
        )

        _setup_auth(test_client)
        with patch.object(
            SQLAlchemySupplierRepository,
            "list_suppliers",
            new_callable=AsyncMock,
            return_value={"items": [], "total": 0, "page": 1, "page_size": 20},
        ):
            resp = test_client.get("/api/admin/v1/suppliers/")
        test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_get_supplier_success(self, test_client):
        from forge.infrastructure.persistence.repositories.supplier_repo import (
            SQLAlchemySupplierRepository,
        )

        _setup_auth(test_client)
        with patch.object(
            SQLAlchemySupplierRepository,
            "get_by_id",
            new_callable=AsyncMock,
            return_value=_make_supplier(name="Acme"),
        ):
            resp = test_client.get(f"/api/admin/v1/suppliers/{SUPPLIER_ID}")
        test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "Acme"

    def test_get_supplier_not_found(self, test_client):
        from forge.infrastructure.persistence.repositories.supplier_repo import (
            SQLAlchemySupplierRepository,
        )

        _setup_auth(test_client)
        with patch.object(SQLAlchemySupplierRepository, "get_by_id", new_callable=AsyncMock, return_value=None):
            resp = test_client.get(f"/api/admin/v1/suppliers/{SUPPLIER_ID}")
        test_client.app.dependency_overrides.clear()
        assert resp.status_code == 404

    def test_create_supplier_success(self, test_client):
        from forge.application.services.supplier_service import SupplierService

        _setup_auth(test_client)
        with patch.object(
            SupplierService,
            "create_supplier",
            new_callable=AsyncMock,
            return_value=_make_supplier(name="Acme"),
        ):
            resp = test_client.post(
                "/api/admin/v1/suppliers/",
                json={
                    "name": "Acme",
                    "contact_email": "a@b.com",
                    "contact_phone": "123",
                    "shipping_regions": ["AE"],
                    "is_active": True,
                },
            )
        test_client.app.dependency_overrides.clear()
        assert resp.status_code == 201
        assert resp.json()["data"]["name"] == "Acme"

    def test_create_supplier_validation_error(self, test_client):
        _setup_auth(test_client)
        try:
            resp = test_client.post("/api/admin/v1/suppliers/", json={})
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 422

    def test_create_supplier_name_conflict(self, test_client):
        from forge.application.services.supplier_service import (
            SupplierNameConflictError,
            SupplierService,
        )

        _setup_auth(test_client)
        with patch.object(
            SupplierService,
            "create_supplier",
            new_callable=AsyncMock,
            side_effect=SupplierNameConflictError("供应商名称已存在"),
        ):
            resp = test_client.post(
                "/api/admin/v1/suppliers/",
                json={"name": "Acme", "contact_email": "a@b.com"},
            )
        test_client.app.dependency_overrides.clear()
        assert resp.status_code == 409

    def test_update_supplier_success(self, test_client):
        from forge.application.services.supplier_service import SupplierService
        from forge.infrastructure.persistence.repositories.supplier_repo import (
            SQLAlchemySupplierRepository,
        )

        _setup_auth(test_client)
        supplier = _make_supplier(name="Acme V2")
        with (
            patch.object(
                SQLAlchemySupplierRepository,
                "get_by_id",
                new_callable=AsyncMock,
                return_value=_make_supplier(name="Acme"),
            ),
            patch.object(SupplierService, "update_supplier", new_callable=AsyncMock, return_value=supplier),
        ):
            resp = test_client.patch(
                f"/api/admin/v1/suppliers/{SUPPLIER_ID}",
                json={"name": "Acme V2"},
            )
        test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "Acme V2"

    def test_update_supplier_not_found(self, test_client):
        from forge.infrastructure.persistence.repositories.supplier_repo import (
            SQLAlchemySupplierRepository,
        )

        _setup_auth(test_client)
        with patch.object(SQLAlchemySupplierRepository, "get_by_id", new_callable=AsyncMock, return_value=None):
            resp = test_client.patch(
                f"/api/admin/v1/suppliers/{SUPPLIER_ID}",
                json={"name": "Ghost"},
            )
        test_client.app.dependency_overrides.clear()
        assert resp.status_code == 404

    def test_deactivate_supplier_success(self, test_client):
        from forge.application.services.supplier_service import SupplierService
        from forge.infrastructure.persistence.repositories.supplier_repo import (
            SQLAlchemySupplierRepository,
        )

        _setup_auth(test_client)
        with (
            patch.object(
                SQLAlchemySupplierRepository,
                "get_by_id",
                new_callable=AsyncMock,
                return_value=_make_supplier(name="Acme", is_active=True),
            ),
            patch.object(
                SupplierService,
                "set_active",
                new_callable=AsyncMock,
                return_value=_make_supplier(name="Acme", is_active=False),
            ),
        ):
            resp = test_client.post(
                f"/api/admin/v1/suppliers/{SUPPLIER_ID}/deactivate",
            )
        test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200

    def test_deactivate_supplier_not_found(self, test_client):
        from forge.infrastructure.persistence.repositories.supplier_repo import (
            SQLAlchemySupplierRepository,
        )

        _setup_auth(test_client)
        with patch.object(SQLAlchemySupplierRepository, "get_by_id", new_callable=AsyncMock, return_value=None):
            resp = test_client.post(
                f"/api/admin/v1/suppliers/{SUPPLIER_ID}/deactivate",
            )
        test_client.app.dependency_overrides.clear()
        assert resp.status_code == 404

    def test_suppliers_unauthorized(self, test_client):
        resp = test_client.get("/api/admin/v1/suppliers/")
        assert resp.status_code == 401

    def test_suppliers_forbidden_no_role(self, test_client):
        """非 ADMIN 角色访问供应商接口 → 403"""
        from fastapi import HTTPException

        async def _fake_admin_403():
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        test_client.app.dependency_overrides[dependencies.get_current_admin] = _fake_admin_403
        try:
            resp = test_client.get("/api/admin/v1/suppliers/")
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 403
