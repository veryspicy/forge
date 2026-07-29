"""Unit tests for Admin Products API."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from forge.application.dtos.product_dtos import (
    PaginatedResponse,
    ProductResponseDTO,
)
from forge.main import dependencies

PRODUCT_ID = str(uuid4())


class TestAdminProductsAPI:
    """Test /api/admin/v1/products endpoints."""

    # ------------------------------------------------------------------
    # Path 1: list products
    # ------------------------------------------------------------------

    def test_list_products_success(self, test_client):
        """Normal path: list products with pagination."""
        from forge.api.admin.v1 import products as products_mod

        mock_service = MagicMock()
        mock_service.list_products = AsyncMock(
            return_value=PaginatedResponse(
                items=[], total=0, page=1, page_size=20, has_next=False, has_prev=False
            )
        )

        _setup_auth_overrides(test_client)
        test_client.app.dependency_overrides[products_mod.get_product_service] = lambda: mock_service
        try:
            response = test_client.get("/api/admin/v1/products/")
        finally:
            test_client.app.dependency_overrides.clear()

        assert response.status_code == 200
        assert response.json()["total"] == 0

    # ------------------------------------------------------------------
    # Path 2: get product
    # ------------------------------------------------------------------

    def test_get_product_success(self, test_client):
        """Get product by ID."""
        from forge.api.admin.v1 import products as products_mod

        mock_service = MagicMock()
        mock_service.get_product = AsyncMock(
            return_value=_make_product(id=PRODUCT_ID, name="Test Toy", sku="TOY-001")
        )

        _setup_auth_overrides(test_client)
        test_client.app.dependency_overrides[products_mod.get_product_service] = lambda: mock_service
        try:
            response = test_client.get(f"/api/admin/v1/products/{PRODUCT_ID}")
        finally:
            test_client.app.dependency_overrides.clear()

        assert response.status_code == 200
        assert response.json()["name"] == "Test Toy"

    def test_get_product_not_found(self, test_client):
        """Non-existent product returns 404."""
        from forge.api.admin.v1 import products as products_mod

        mock_service = MagicMock()
        mock_service.get_product = AsyncMock(return_value=None)

        _setup_auth_overrides(test_client)
        test_client.app.dependency_overrides[products_mod.get_product_service] = lambda: mock_service
        try:
            response = test_client.get(f"/api/admin/v1/products/{PRODUCT_ID}")
        finally:
            test_client.app.dependency_overrides.clear()

        assert response.status_code == 404

    # ------------------------------------------------------------------
    # Path 3: create product
    # ------------------------------------------------------------------

    def test_create_product_success(self, test_client):
        """Create a new product."""
        from forge.api.admin.v1 import products as products_mod

        mock_service = MagicMock()
        mock_service.create_product = AsyncMock(
            return_value=_make_product(id=PRODUCT_ID, name="New Toy", sku="TOY-002", price=19.99, cost=8.0)
        )

        _setup_auth_overrides(test_client)
        test_client.app.dependency_overrides[products_mod.get_product_service] = lambda: mock_service
        try:
            payload = {
                "sku": "TOY-002",
                "name": "New Toy",
                "description": "A fun toy",
                "price": 19.99,
                "cost": 8.00,
                "category": "toys",
            }
            response = test_client.post("/api/admin/v1/products/", json=payload)
        finally:
            test_client.app.dependency_overrides.clear()

        assert response.status_code == 201
        assert response.json()["sku"] == "TOY-002"

    def test_create_product_validation_error(self, test_client):
        """Missing required fields returns 422."""
        _setup_auth_overrides(test_client)
        try:
            response = test_client.post("/api/admin/v1/products/", json={})
        finally:
            test_client.app.dependency_overrides.clear()

        assert response.status_code == 422

    # ------------------------------------------------------------------
    # Path 4: update product
    # ------------------------------------------------------------------

    def test_update_product_success(self, test_client):
        """Update existing product."""
        from forge.api.admin.v1 import products as products_mod

        mock_service = MagicMock()
        mock_service.update_product = AsyncMock(
            return_value=_make_product(id=PRODUCT_ID, name="Updated Toy", sku="TOY-001", price=34.99)
        )

        _setup_auth_overrides(test_client)
        test_client.app.dependency_overrides[products_mod.get_product_service] = lambda: mock_service
        try:
            response = test_client.patch(
                f"/api/admin/v1/products/{PRODUCT_ID}",
                json={"name": "Updated Toy", "price": 34.99},
            )
        finally:
            test_client.app.dependency_overrides.clear()

        assert response.status_code == 200
        assert response.json()["name"] == "Updated Toy"

    def test_update_product_not_found(self, test_client):
        """Update non-existent product returns 404."""
        from forge.api.admin.v1 import products as products_mod

        mock_service = MagicMock()
        mock_service.update_product = AsyncMock(return_value=None)

        _setup_auth_overrides(test_client)
        test_client.app.dependency_overrides[products_mod.get_product_service] = lambda: mock_service
        try:
            response = test_client.patch(
                f"/api/admin/v1/products/{PRODUCT_ID}", json={"name": "Ghost"}
            )
        finally:
            test_client.app.dependency_overrides.clear()

        assert response.status_code == 404

    # ------------------------------------------------------------------
    # Path 5: set product status
    # ------------------------------------------------------------------

    def test_set_product_status_success(self, test_client):
        """Set product status to active."""
        from forge.api.admin.v1 import products as products_mod

        mock_service = MagicMock()
        mock_service.get_product = AsyncMock(
            return_value=_make_product(id=PRODUCT_ID, name="Toy", sku="TOY-001")
        )
        mock_service.update_product = AsyncMock(
            return_value=_make_product(id=PRODUCT_ID, name="Toy", sku="TOY-001")
        )

        _setup_auth_overrides(test_client)
        test_client.app.dependency_overrides[products_mod.get_product_service] = lambda: mock_service
        try:
            response = test_client.post(
                f"/api/admin/v1/products/{PRODUCT_ID}/status",
                json={"status": "active"},
            )
        finally:
            test_client.app.dependency_overrides.clear()

        assert response.status_code == 200

    def test_set_product_status_invalid(self, test_client):
        """Invalid status returns 400."""
        from forge.api.admin.v1 import products as products_mod

        mock_service = MagicMock()
        mock_service.get_product = AsyncMock(
            return_value=_make_product(id=PRODUCT_ID, name="Toy", sku="TOY-001")
        )

        _setup_auth_overrides(test_client)
        test_client.app.dependency_overrides[products_mod.get_product_service] = lambda: mock_service
        try:
            response = test_client.post(
                f"/api/admin/v1/products/{PRODUCT_ID}/status",
                json={"status": "deleted"},
            )
        finally:
            test_client.app.dependency_overrides.clear()

        assert response.status_code == 400

    def test_set_product_status_not_found(self, test_client):
        """Set status on non-existent product returns 404."""
        from forge.api.admin.v1 import products as products_mod

        mock_service = MagicMock()
        mock_service.get_product = AsyncMock(return_value=None)

        _setup_auth_overrides(test_client)
        test_client.app.dependency_overrides[products_mod.get_product_service] = lambda: mock_service
        try:
            response = test_client.post(
                f"/api/admin/v1/products/{PRODUCT_ID}/status",
                json={"status": "active"},
            )
        finally:
            test_client.app.dependency_overrides.clear()

        assert response.status_code == 404

    # ------------------------------------------------------------------
    # Path 6: search and filter
    # ------------------------------------------------------------------

    def test_list_products_with_search(self, test_client):
        """Search products by keyword."""
        from forge.api.admin.v1 import products as products_mod

        mock_service = MagicMock()
        mock_service.list_products = AsyncMock(
            return_value=PaginatedResponse(
                items=[_make_product(name="Cat Food", sku="CF-001")],
                total=1, page=1, page_size=20, has_next=False, has_prev=False,
            )
        )

        _setup_auth_overrides(test_client)
        test_client.app.dependency_overrides[products_mod.get_product_service] = lambda: mock_service
        try:
            response = test_client.get("/api/admin/v1/products/?search=cat")
        finally:
            test_client.app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "Cat Food"

    def test_list_products_with_category_filter(self, test_client):
        """Filter products by category."""
        from forge.api.admin.v1 import products as products_mod

        mock_service = MagicMock()
        mock_service.list_products = AsyncMock(
            return_value=PaginatedResponse(
                items=[_make_product(name="Dog Toy", sku="DT-001", category="toys")],
                total=1, page=1, page_size=20, has_next=False, has_prev=False,
            )
        )

        _setup_auth_overrides(test_client)
        test_client.app.dependency_overrides[products_mod.get_product_service] = lambda: mock_service
        try:
            response = test_client.get("/api/admin/v1/products/?category=toys")
        finally:
            test_client.app.dependency_overrides.clear()

        assert response.status_code == 200
        assert response.json()["items"][0]["category"] == "toys"

    def test_list_products_pagination(self, test_client):
        """Test pagination params are respected."""
        from forge.api.admin.v1 import products as products_mod

        mock_service = MagicMock()
        mock_service.list_products = AsyncMock(
            return_value=PaginatedResponse(
                items=[], total=50, page=2, page_size=10, has_next=True, has_prev=True,
            )
        )

        _setup_auth_overrides(test_client)
        test_client.app.dependency_overrides[products_mod.get_product_service] = lambda: mock_service
        try:
            response = test_client.get("/api/admin/v1/products/?page=2&page_size=10")
        finally:
            test_client.app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["page_size"] == 10

    # ------------------------------------------------------------------
    # Path 7: unauthorized
    # ------------------------------------------------------------------

    def test_products_unauthorized(self, test_client):
        """No auth header returns 401."""
        response = test_client.get("/api/admin/v1/products/")
        assert response.status_code == 401


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

FAKE_ADMIN_ID = "d290f1ee-6c54-4b01-90e6-d701748f0851"


def _setup_auth_overrides(test_client):
    """Setup get_db and get_current_user_id overrides."""
    async def _fake_get_db():
        yield AsyncMock()

    async def _fake_user_id():
        from uuid import UUID
        return UUID(FAKE_ADMIN_ID)

    test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
    test_client.app.dependency_overrides[dependencies.get_current_user_id] = _fake_user_id


def _make_product(
    id=PRODUCT_ID,
    name="Test Product",
    sku="SKU-001",
    price=29.99,
    cost=10.0,
    category="toys",
):
    return ProductResponseDTO(
        id=id,
        sku=sku,
        slug=sku.lower().replace(" ", "-"),
        name=name,
        description="A test product",
        ai_description=None,
        price=price,
        cost=cost,
        category=category,
        breed_groups=[],
        suitable_for={},
        tags=[],
        inventory=10,
        rating=0.0,
        review_count=0,
        images=[],
        region_availability=["AE"],
        is_ai_generated=False,
        seo_data=None,
    )
