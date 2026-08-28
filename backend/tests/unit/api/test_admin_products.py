"""Unit tests for Admin Products API (new static-service architecture)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

from forge.main import dependencies

PRODUCT_ID = str(uuid4())
FAKE_ADMIN_ID = "d290f1ee-6c54-4b01-90e6-d701748f0851"


def _setup_auth_overrides(test_client: Any) -> None:
    """Override get_db and get_current_admin (super_admin) for admin unit tests."""

    async def _fake_get_db() -> AsyncIterator[Any]:
        yield AsyncMock()

    async def _fake_admin() -> dict[str, object]:
        return {"id": UUID(FAKE_ADMIN_ID), "role": "super_admin", "roles": ["super_admin"]}

    test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
    test_client.app.dependency_overrides[dependencies.get_current_admin] = _fake_admin


def _make_product(
    name: str = "Test Product", sku: str = "SKU-001", price: float = 29.99, category: str = "toys"
) -> MagicMock:
    """Build a fake ORMProduct-like object exposing to_dict()/images."""
    product = MagicMock()
    product.to_dict.return_value = {
        "id": PRODUCT_ID,
        "sku": sku,
        "slug": sku.lower().replace(" ", "-"),
        "name": name,
        "description": "A test product",
        "price": price,
        "category": category,
        "status": "active",
        "inventory": 10,
        "images": [],
    }
    product.images = []
    product.id = PRODUCT_ID
    return product


class TestAdminProductsAPI:
    """Test /api/admin/v1/products endpoints."""

    def test_list_products_success(self, test_client: Any) -> None:
        from forge.infrastructure.persistence.repositories.product_repo import (
            SQLAlchemyProductRepository,
        )

        _setup_auth_overrides(test_client)
        with patch.object(
            SQLAlchemyProductRepository,
            "list_products",
            new_callable=AsyncMock,
            return_value={"items": [], "total": 0, "page": 1, "page_size": 20},
        ):
            response = test_client.get("/api/admin/v1/products/")
        test_client.app.dependency_overrides.clear()

        assert response.status_code == 200
        assert response.json()["total"] == 0

    def test_get_product_success(self, test_client: Any) -> None:
        from forge.infrastructure.persistence.repositories.product_repo import (
            SQLAlchemyProductRepository,
        )

        _setup_auth_overrides(test_client)
        with (
            patch.object(
                SQLAlchemyProductRepository,
                "get_by_id",
                new_callable=AsyncMock,
                return_value=_make_product(name="Test Toy", sku="TOY-001"),
            ),
            patch.object(
                SQLAlchemyProductRepository,
                "list_variants",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            response = test_client.get(f"/api/admin/v1/products/{PRODUCT_ID}")
        test_client.app.dependency_overrides.clear()

        assert response.status_code == 200
        assert response.json()["data"]["name"] == "Test Toy"

    def test_get_product_not_found(self, test_client: Any) -> None:
        from forge.infrastructure.persistence.repositories.product_repo import (
            SQLAlchemyProductRepository,
        )

        _setup_auth_overrides(test_client)
        with patch.object(SQLAlchemyProductRepository, "get_by_id", new_callable=AsyncMock, return_value=None):
            response = test_client.get(f"/api/admin/v1/products/{PRODUCT_ID}")
        test_client.app.dependency_overrides.clear()

        assert response.status_code == 404

    def test_create_product_success(self, test_client: Any) -> None:
        from forge.application.services.product_service import ProductService

        _setup_auth_overrides(test_client)
        with patch.object(
            ProductService,
            "create_product",
            new_callable=AsyncMock,
            return_value=_make_product(name="New Toy", sku="TOY-002", price=19.99),
        ):
            payload = {
                "sku": "TOY-002",
                "name": "New Toy",
                "description": "A fun toy",
                "price": 19.99,
                "cost": 8.00,
                "category": "toys",
            }
            response = test_client.post("/api/admin/v1/products/", json=payload)
        test_client.app.dependency_overrides.clear()

        assert response.status_code == 201
        assert response.json()["data"]["sku"] == "TOY-002"

    def test_create_product_validation_error(self, test_client: Any) -> None:
        _setup_auth_overrides(test_client)
        try:
            response = test_client.post("/api/admin/v1/products/", json={})
        finally:
            test_client.app.dependency_overrides.clear()

        assert response.status_code == 422

    def test_update_product_success(self, test_client: Any) -> None:
        from forge.application.services.product_service import ProductService
        from forge.infrastructure.persistence.repositories.product_repo import (
            SQLAlchemyProductRepository,
        )

        _setup_auth_overrides(test_client)
        product = _make_product(name="Updated Toy", sku="TOY-001", price=34.99)
        with (
            patch.object(
                SQLAlchemyProductRepository,
                "get_by_id",
                new_callable=AsyncMock,
                return_value=product,
            ),
            patch.object(ProductService, "update_product", new_callable=AsyncMock, return_value=product),
        ):
            response = test_client.patch(
                f"/api/admin/v1/products/{PRODUCT_ID}",
                json={"name": "Updated Toy", "price": 34.99},
            )
        test_client.app.dependency_overrides.clear()

        assert response.status_code == 200
        assert response.json()["data"]["name"] == "Updated Toy"

    def test_update_product_not_found(self, test_client: Any) -> None:
        from forge.infrastructure.persistence.repositories.product_repo import (
            SQLAlchemyProductRepository,
        )

        _setup_auth_overrides(test_client)
        with patch.object(SQLAlchemyProductRepository, "get_by_id", new_callable=AsyncMock, return_value=None):
            response = test_client.patch(f"/api/admin/v1/products/{PRODUCT_ID}", json={"name": "Ghost"})
        test_client.app.dependency_overrides.clear()

        assert response.status_code == 404

    def test_set_product_status_success(self, test_client: Any) -> None:
        from forge.application.services.product_service import ProductService
        from forge.infrastructure.persistence.repositories.product_repo import (
            SQLAlchemyProductRepository,
        )

        _setup_auth_overrides(test_client)
        product = _make_product(name="Toy", sku="TOY-001")
        with (
            patch.object(
                SQLAlchemyProductRepository,
                "get_by_id",
                new_callable=AsyncMock,
                return_value=product,
            ),
            patch.object(ProductService, "set_status", new_callable=AsyncMock, return_value=product),
        ):
            response = test_client.post(
                f"/api/admin/v1/products/{PRODUCT_ID}/status",
                json={"status": "active"},
            )
        test_client.app.dependency_overrides.clear()

        assert response.status_code == 200

    def test_set_product_status_invalid(self, test_client: Any) -> None:
        from forge.application.services.product_service import ProductService, ProductValidationError
        from forge.infrastructure.persistence.repositories.product_repo import (
            SQLAlchemyProductRepository,
        )

        _setup_auth_overrides(test_client)
        with (
            patch.object(
                SQLAlchemyProductRepository,
                "get_by_id",
                new_callable=AsyncMock,
                return_value=_make_product(name="Toy", sku="TOY-001"),
            ),
            patch.object(
                ProductService,
                "set_status",
                new_callable=AsyncMock,
                side_effect=ProductValidationError("无效状态"),
            ),
        ):
            response = test_client.post(
                f"/api/admin/v1/products/{PRODUCT_ID}/status",
                json={"status": "unknown"},
            )
        test_client.app.dependency_overrides.clear()

        assert response.status_code == 400

    def test_set_product_status_not_found(self, test_client: Any) -> None:
        from forge.infrastructure.persistence.repositories.product_repo import (
            SQLAlchemyProductRepository,
        )

        _setup_auth_overrides(test_client)
        with patch.object(SQLAlchemyProductRepository, "get_by_id", new_callable=AsyncMock, return_value=None):
            response = test_client.post(
                f"/api/admin/v1/products/{PRODUCT_ID}/status",
                json={"status": "active"},
            )
        test_client.app.dependency_overrides.clear()

        assert response.status_code == 404

    def test_list_products_with_search(self, test_client: Any) -> None:
        from forge.infrastructure.persistence.repositories.product_repo import (
            SQLAlchemyProductRepository,
        )

        _setup_auth_overrides(test_client)
        with patch.object(
            SQLAlchemyProductRepository,
            "list_products",
            new_callable=AsyncMock,
            return_value={
                "items": [_make_product(name="Cat Food", sku="CF-001").to_dict()],
                "total": 1,
                "page": 1,
                "page_size": 20,
            },
        ):
            response = test_client.get("/api/admin/v1/products/?search=cat")
        test_client.app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "Cat Food"

    def test_list_products_with_category_filter(self, test_client: Any) -> None:
        from forge.infrastructure.persistence.repositories.product_repo import (
            SQLAlchemyProductRepository,
        )

        _setup_auth_overrides(test_client)
        with patch.object(
            SQLAlchemyProductRepository,
            "list_products",
            new_callable=AsyncMock,
            return_value={
                "items": [_make_product(name="Dog Toy", sku="DT-001", category="toys").to_dict()],
                "total": 1,
                "page": 1,
                "page_size": 20,
            },
        ):
            response = test_client.get("/api/admin/v1/products/?category=toys")
        test_client.app.dependency_overrides.clear()

        assert response.status_code == 200
        assert response.json()["items"][0]["category"] == "toys"

    def test_list_products_pagination(self, test_client: Any) -> None:
        from forge.infrastructure.persistence.repositories.product_repo import (
            SQLAlchemyProductRepository,
        )

        _setup_auth_overrides(test_client)
        with patch.object(
            SQLAlchemyProductRepository,
            "list_products",
            new_callable=AsyncMock,
            return_value={"items": [], "total": 50, "page": 2, "page_size": 10},
        ):
            response = test_client.get("/api/admin/v1/products/?page=2&page_size=10")
        test_client.app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["page_size"] == 10

    def test_products_unauthorized(self, test_client: Any) -> None:
        response = test_client.get("/api/admin/v1/products/")
        assert response.status_code == 401

    def test_delete_product_soft_delete_success(self, test_client: Any) -> None:
        from forge.application.services.product_service import ProductService
        from forge.infrastructure.persistence.repositories.product_repo import (
            SQLAlchemyProductRepository,
        )

        _setup_auth_overrides(test_client)
        product = _make_product(name="Toy", sku="TOY-001")
        with (
            patch.object(
                SQLAlchemyProductRepository,
                "get_by_id",
                new_callable=AsyncMock,
                return_value=product,
            ),
            patch.object(ProductService, "set_status", new_callable=AsyncMock, return_value=product),
        ):
            response = test_client.delete(f"/api/admin/v1/products/{PRODUCT_ID}")
        test_client.app.dependency_overrides.clear()

        assert response.status_code == 200
        assert response.json()["data"]["status"] == "deleted"

    def test_delete_product_already_deleted(self, test_client: Any) -> None:
        from forge.infrastructure.persistence.repositories.product_repo import (
            SQLAlchemyProductRepository,
        )

        _setup_auth_overrides(test_client)
        product = _make_product(name="Toy", sku="TOY-001")
        product.to_dict.return_value["status"] = "deleted"
        product.status = "deleted"
        with patch.object(
            SQLAlchemyProductRepository,
            "get_by_id",
            new_callable=AsyncMock,
            return_value=product,
        ):
            response = test_client.delete(f"/api/admin/v1/products/{PRODUCT_ID}")
        test_client.app.dependency_overrides.clear()

        assert response.status_code == 400

    def test_delete_product_not_found(self, test_client: Any) -> None:
        from forge.infrastructure.persistence.repositories.product_repo import (
            SQLAlchemyProductRepository,
        )

        _setup_auth_overrides(test_client)
        with patch.object(SQLAlchemyProductRepository, "get_by_id", new_callable=AsyncMock, return_value=None):
            response = test_client.delete(f"/api/admin/v1/products/{PRODUCT_ID}")
        test_client.app.dependency_overrides.clear()

        assert response.status_code == 404

    def test_batch_status_success(self, test_client: Any) -> None:
        from forge.application.services.product_service import ProductService
        from forge.infrastructure.persistence.repositories.product_repo import (
            SQLAlchemyProductRepository,
        )

        _setup_auth_overrides(test_client)
        p1 = _make_product(name="Toy A", sku="TA-001")
        p2 = _make_product(name="Toy B", sku="TB-001")
        with (
            patch.object(
                SQLAlchemyProductRepository,
                "list_by_ids",
                new_callable=AsyncMock,
                return_value=[p1, p2],
            ),
            patch.object(ProductService, "set_status", new_callable=AsyncMock),
        ):
            response = test_client.post(
                "/api/admin/v1/products/batch-status",
                json={"ids": [PRODUCT_ID, PRODUCT_ID], "status": "inactive"},
            )
        test_client.app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["updated"] == 2
        assert data["missing"] == []

    def test_batch_status_partial_missing(self, test_client: Any) -> None:
        from forge.application.services.product_service import ProductService
        from forge.infrastructure.persistence.repositories.product_repo import (
            SQLAlchemyProductRepository,
        )

        _setup_auth_overrides(test_client)
        p1 = _make_product(name="Toy A", sku="TA-001")
        ghost_id = str(uuid4())
        with (
            patch.object(
                SQLAlchemyProductRepository,
                "list_by_ids",
                new_callable=AsyncMock,
                return_value=[p1],
            ),
            patch.object(ProductService, "set_status", new_callable=AsyncMock),
        ):
            response = test_client.post(
                "/api/admin/v1/products/batch-status",
                json={"ids": [PRODUCT_ID, ghost_id], "status": "active"},
            )
        test_client.app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["updated"] == 1
        assert data["missing"] == [ghost_id]

    def test_batch_status_empty_ids(self, test_client: Any) -> None:
        _setup_auth_overrides(test_client)
        try:
            response = test_client.post(
                "/api/admin/v1/products/batch-status",
                json={"ids": [], "status": "active"},
            )
        finally:
            test_client.app.dependency_overrides.clear()

        assert response.status_code == 400

    def test_batch_status_invalid_status(self, test_client: Any) -> None:
        _setup_auth_overrides(test_client)
        try:
            response = test_client.post(
                "/api/admin/v1/products/batch-status",
                json={"ids": [PRODUCT_ID], "status": "unknown"},
            )
        finally:
            test_client.app.dependency_overrides.clear()

        assert response.status_code == 400

    def test_batch_status_too_many(self, test_client: Any) -> None:
        _setup_auth_overrides(test_client)
        try:
            response = test_client.post(
                "/api/admin/v1/products/batch-status",
                json={"ids": [str(uuid4()) for _ in range(201)], "status": "active"},
            )
        finally:
            test_client.app.dependency_overrides.clear()

        assert response.status_code == 400
