"""Unit tests for Supplier API endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest


FAKE_USER_ID = "d290f1ee-6c54-4b01-90e6-d701748f0851"


class TestSuppliersAPI:
    @patch("forge.main.dependencies.get_db")
    @patch("forge.main.dependencies.get_current_user_id")
    def test_list_suppliers(self, mock_user, mock_db, test_client):
        mock_user.return_value = FAKE_USER_ID
        mock_db.return_value = AsyncMock()

        from forge.domain.supplier.models import Supplier
        from forge.infrastructure.persistence.repositories.supplier_repo import SQLAlchemySupplierRepository

        s1 = Supplier.create(name="Supplier A")
        s1.id = uuid4()

        with patch.object(
            SQLAlchemySupplierRepository, "get_all", new_callable=AsyncMock
        ) as mock_get_all:
            mock_get_all.return_value = ([s1], 1)
            response = test_client.get("/api/v1/suppliers/")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "Supplier A"

    def test_create_supplier(self, test_client):
        from forge.main import dependencies
        from forge.infrastructure.persistence.repositories.supplier_repo import SQLAlchemySupplierRepository

        async def _fake_get_db():
            yield AsyncMock()

        async def _fake_user_id():
            from uuid import UUID
            return UUID(FAKE_USER_ID)

        test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
        test_client.app.dependency_overrides[dependencies.get_current_user_id] = _fake_user_id

        try:
            with patch.object(
                SQLAlchemySupplierRepository, "create", new_callable=AsyncMock
            ) as mock_create:

                async def _fake_create(supplier):
                    supplier.id = uuid4()
                    return supplier

                mock_create.side_effect = _fake_create

                payload = {
                    "name": "New Supplier",
                    "contact_email": "info@new.com",
                    "integration_type": "api",
                    "api_config": {"endpoint": "https://api.new.com"},
                }
                response = test_client.post(
                    "/api/v1/suppliers/", json=payload
                )

            assert response.status_code == 201
            data = response.json()
            assert data["name"] == "New Supplier"
        finally:
            test_client.app.dependency_overrides.clear()

    def test_create_supplier_validation_error(self, test_client):
        """Missing required fields should return 422."""
        from forge.main import dependencies

        async def _fake_get_db():
            yield AsyncMock()

        async def _fake_user_id():
            from uuid import UUID
            return UUID(FAKE_USER_ID)

        test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
        test_client.app.dependency_overrides[dependencies.get_current_user_id] = _fake_user_id

        try:
            payload = {"name": ""}  # empty name
            response = test_client.post("/api/v1/suppliers/", json=payload)
        finally:
            test_client.app.dependency_overrides.clear()

        assert response.status_code == 422

    def test_deactivate_supplier(self, test_client):
        supplier_id = uuid4()
        from forge.main import dependencies
        from forge.domain.supplier.models import Supplier
        from forge.infrastructure.persistence.repositories.supplier_repo import SQLAlchemySupplierRepository

        async def _fake_get_db():
            yield AsyncMock()

        async def _fake_user_id():
            from uuid import UUID
            return UUID(FAKE_USER_ID)

        test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
        test_client.app.dependency_overrides[dependencies.get_current_user_id] = _fake_user_id

        try:
            supplier = Supplier.create(name="Active Co")
            supplier.id = supplier_id

            with (
                patch.object(
                    SQLAlchemySupplierRepository,
                    "get_by_id",
                    new_callable=AsyncMock,
                ) as mock_get,
                patch.object(
                    SQLAlchemySupplierRepository,
                    "update",
                    new_callable=AsyncMock,
                ) as mock_update,
            ):
                mock_get.return_value = supplier

                response = test_client.post(
                    f"/api/v1/suppliers/{supplier_id}/deactivate"
                )

            assert response.status_code == 200
            data = response.json()
            assert "detail" in data
        finally:
            test_client.app.dependency_overrides.clear()

    @patch("forge.main.dependencies.get_db")
    @patch("forge.main.dependencies.get_current_user_id")
    def test_list_suppliers_with_filters(
        self, mock_user, mock_db, test_client
    ):
        mock_user.return_value = FAKE_USER_ID
        mock_db.return_value = AsyncMock()

        from forge.infrastructure.persistence.repositories.supplier_repo import SQLAlchemySupplierRepository

        with patch.object(
            SQLAlchemySupplierRepository, "get_all", new_callable=AsyncMock
        ) as mock_get_all:
            mock_get_all.return_value = ([], 0)
            response = test_client.get(
                "/api/v1/suppliers/?integration_type=api&is_active=true&region=US"
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0

    def test_update_supplier_not_found(self, test_client):
        from forge.main import dependencies
        from forge.infrastructure.persistence.repositories.supplier_repo import SQLAlchemySupplierRepository

        async def _fake_get_db():
            yield AsyncMock()

        async def _fake_user_id():
            from uuid import UUID
            return UUID(FAKE_USER_ID)

        test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
        test_client.app.dependency_overrides[dependencies.get_current_user_id] = _fake_user_id

        try:
            with patch.object(
                SQLAlchemySupplierRepository, "get_by_id", new_callable=AsyncMock
            ) as mock_get:
                mock_get.return_value = None
                response = test_client.patch(
                    f"/api/v1/suppliers/{uuid4()}",
                    json={"name": "New Name"},
                )

            assert response.status_code == 404
        finally:
            test_client.app.dependency_overrides.clear()
