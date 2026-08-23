"""Unit tests for SupplierService (new static API: db + dict)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from forge.application.services.supplier_service import (
    SupplierNameConflictError,
    SupplierService,
    SupplierValidationError,
)
from forge.infrastructure.persistence.models import ORMSupplier


def _make_supplier(**overrides: object) -> ORMSupplier:
    supplier = ORMSupplier(
        name=overrides.get("name", "Test Supplier"),
        integration_type=overrides.get("integration_type", "manual"),
        default_currency=overrides.get("default_currency", "USD"),
        is_active=overrides.get("is_active", True),
    )
    supplier.id = uuid4()
    return supplier


class TestSupplierService:
    @pytest.mark.asyncio
    async def test_create_supplier(self, mock_db_session):
        async def _fake_create(db, payload):
            return _make_supplier(**payload)

        with (
            patch(
                "forge.application.services.supplier_service.SQLAlchemySupplierRepository.get_by_name",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "forge.application.services.supplier_service.SQLAlchemySupplierRepository.create",
                side_effect=_fake_create,
            ),
        ):
            result = await SupplierService.create_supplier(
                mock_db_session, {"name": "Test Supplier", "integration_type": "api"}
            )
        assert result.name == "Test Supplier"
        assert result.integration_type == "api"

    @pytest.mark.asyncio
    async def test_create_supplier_name_conflict(self, mock_db_session):
        existing = _make_supplier(name="Duplicate")
        with (
            patch(
                "forge.application.services.supplier_service.SQLAlchemySupplierRepository.get_by_name",
                new_callable=AsyncMock,
                return_value=existing,
            ),
            pytest.raises(SupplierNameConflictError),
        ):
            await SupplierService.create_supplier(mock_db_session, {"name": "Duplicate", "integration_type": "manual"})

    @pytest.mark.asyncio
    async def test_create_supplier_missing_name(self, mock_db_session):
        with pytest.raises(SupplierValidationError):
            await SupplierService.create_supplier(mock_db_session, {"name": "   "})

    @pytest.mark.asyncio
    async def test_create_supplier_invalid_integration_type(self, mock_db_session):
        with pytest.raises(SupplierValidationError):
            await SupplierService.create_supplier(mock_db_session, {"name": "Bad", "integration_type": "unknown"})

    @pytest.mark.asyncio
    async def test_update_supplier(self, mock_db_session):
        supplier = _make_supplier(name="Old Name")
        with (
            patch(
                "forge.application.services.supplier_service.SQLAlchemySupplierRepository.get_by_name",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "forge.application.services.supplier_service.SQLAlchemySupplierRepository.update",
                new_callable=AsyncMock,
                return_value=supplier,
            ),
        ):
            result = await SupplierService.update_supplier(mock_db_session, supplier, {"name": "New Name"})
        assert result.name == "Old Name"

    @pytest.mark.asyncio
    async def test_set_active(self, mock_db_session):
        supplier = _make_supplier(is_active=True)
        with patch(
            "forge.application.services.supplier_service.SQLAlchemySupplierRepository.update",
            new_callable=AsyncMock,
            return_value=supplier,
        ) as mock_update:
            result = await SupplierService.set_active(mock_db_session, supplier, False)
        assert result.is_active is True
        mock_update.assert_awaited_once_with(mock_db_session, supplier, {"is_active": False})
