"""Unit tests for Supplier aggregate root."""

from __future__ import annotations

import pytest
from forge.domain.supplier.models import Supplier


class TestSupplier:
    """Supplier 聚合根 单元测试。"""

    def test_create_supplier_success(self):
        supplier = Supplier.create(
            name="PetSupply Direct",
            contact_email="hello@petsupply.com",
            contact_phone="+1-555-0100",
            shipping_regions=["US", "CA"],
            integration_type="api",
            api_config={"endpoint": "https://api.petsupply.com"},
            default_currency="USD",
            payment_terms="Net 30",
        )
        assert supplier.name == "PetSupply Direct"
        assert supplier.contact_email == "hello@petsupply.com"
        assert supplier.shipping_regions == ["US", "CA"]
        assert supplier.integration_type == "api"
        assert supplier.api_config == {"endpoint": "https://api.petsupply.com"}
        assert supplier.default_currency == "USD"
        assert supplier.payment_terms == "Net 30"
        assert supplier.is_active is True

    def test_create_supplier_empty_name_raises(self):
        with pytest.raises(ValueError, match="Supplier name cannot be empty"):
            Supplier.create(name="   ")

    def test_create_supplier_invalid_integration_type_raises(self):
        with pytest.raises(ValueError, match="integration_type must be 'api' or 'manual'"):
            Supplier.create(name="Test", integration_type="ftp")

    def test_create_supplier_defaults(self):
        supplier = Supplier.create(name="Minimal")
        assert supplier.contact_email == ""
        assert supplier.contact_phone == ""
        assert supplier.shipping_regions == []
        assert supplier.integration_type == "manual"
        assert supplier.api_config == {}
        assert supplier.default_currency == "USD"
        assert supplier.payment_terms == ""

    def test_deactivate_supplier(self):
        supplier = Supplier.create(name="ActiveCo")
        assert supplier.is_active is True
        supplier.deactivate()
        assert supplier.is_active is False

    def test_activate_supplier(self):
        supplier = Supplier.create(name="InactiveCo")
        supplier.deactivate()
        assert supplier.is_active is False
        supplier.activate()
        assert supplier.is_active is True

    def test_update_api_config(self):
        supplier = Supplier.create(name="APICo")
        new_config = {"endpoint": "https://v2.api.example.com", "token": "abc123"}
        supplier.update_api_config(new_config)
        assert supplier.api_config == new_config

    def test_add_region(self):
        supplier = Supplier.create(name="GlobalCo")
        supplier.add_region("US")
        supplier.add_region("CA")
        assert "US" in supplier.shipping_regions
        assert "CA" in supplier.shipping_regions
        assert len(supplier.shipping_regions) == 2

    def test_remove_region(self):
        supplier = Supplier.create(name="GlobalCo", shipping_regions=["US", "CA", "UK"])
        supplier.remove_region("CA")
        assert supplier.shipping_regions == ["US", "UK"]

    def test_add_duplicate_region_ignored(self):
        supplier = Supplier.create(name="GlobalCo", shipping_regions=["US"])
        supplier.add_region("us")  # case-insensitive
        assert supplier.shipping_regions == ["US"]

    def test_remove_nonexistent_region_ignored(self):
        supplier = Supplier.create(name="GlobalCo", shipping_regions=["US"])
        supplier.remove_region("JP")
        assert supplier.shipping_regions == ["US"]

    def test_add_region_strips_whitespace(self):
        supplier = Supplier.create(name="GlobalCo")
        supplier.add_region("  GB  ")
        assert supplier.shipping_regions == ["GB"]

    def test_create_supplier_regions_uppercased_and_stripped(self):
        supplier = Supplier.create(name="Test", shipping_regions=[" us ", "Ca", ""])
        assert supplier.shipping_regions == ["US", "CA"]
