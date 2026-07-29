"""Unit tests for SupplierService (mock repository)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from forge.application.dtos.supplier_dtos import SupplierCreateDTO, SupplierResponseDTO
from forge.application.services.supplier_service import SupplierService
from forge.domain.supplier.models import Supplier


@pytest.fixture
def supplier_service(mock_supplier_repo):
    return SupplierService(repo=mock_supplier_repo)


class TestSupplierService:
    @pytest.mark.asyncio
    async def test_create_supplier(self, supplier_service, mock_supplier_repo):
        dto = SupplierCreateDTO(name="Test Supplier", integration_type="api")

        async def _fake_create(supplier):
            supplier.id = uuid4()
            return supplier

        mock_supplier_repo.create.side_effect = _fake_create

        result = await supplier_service.create_supplier(dto)
        assert isinstance(result, SupplierResponseDTO)
        assert result.name == "Test Supplier"
        assert result.integration_type == "api"
        mock_supplier_repo.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_supplier_found(self, supplier_service, mock_supplier_repo):
        supplier_id = uuid4()
        supplier = Supplier.create(name="ExistingCo")
        supplier.id = supplier_id
        mock_supplier_repo.get_by_id.return_value = supplier

        result = await supplier_service.get_supplier(supplier_id)
        assert result is not None
        assert result.name == "ExistingCo"
        mock_supplier_repo.get_by_id.assert_awaited_once_with(supplier_id)

    @pytest.mark.asyncio
    async def test_get_supplier_not_found(self, supplier_service, mock_supplier_repo):
        mock_supplier_repo.get_by_id.return_value = None
        result = await supplier_service.get_supplier(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_list_suppliers_with_filters(self, supplier_service, mock_supplier_repo):
        s1 = Supplier.create(name="S1")
        s2 = Supplier.create(name="S2")
        mock_supplier_repo.get_all.return_value = ([s1, s2], 2)

        result = await supplier_service.list_suppliers(
            integration_type="manual", is_active=True, page=1, page_size=10
        )
        assert result.total == 2
        assert len(result.items) == 2
        assert result.page == 1
        mock_supplier_repo.get_all.assert_awaited_once_with(
            integration_type="manual", is_active=True, region=None, page=1, page_size=10
        )

    @pytest.mark.asyncio
    async def test_deactivate_supplier(self, supplier_service, mock_supplier_repo):
        supplier_id = uuid4()
        supplier = Supplier.create(name="DeactCo")
        supplier.id = supplier_id
        assert supplier.is_active is True
        mock_supplier_repo.get_by_id.return_value = supplier

        result = await supplier_service.deactivate_supplier(supplier_id)
        assert result is True
        assert supplier.is_active is False
        mock_supplier_repo.update.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_deactivate_supplier_not_found(self, supplier_service, mock_supplier_repo):
        mock_supplier_repo.get_by_id.return_value = None
        result = await supplier_service.deactivate_supplier(uuid4())
        assert result is False
