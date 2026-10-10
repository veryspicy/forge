"""Unit tests for ProductService publishing gate / image normalization / upload-with-variants."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from forge.application.services.product_service import (
    ProductService,
    ProductValidationError,
)


class TestNormalizeImages:
    """行业标准图片契约：url 必填、sort 唯一、主图唯一。"""

    def test_missing_url_raises(self) -> None:
        with pytest.raises(ProductValidationError) as exc:
            ProductService.normalize_images([{"url": ""}])
        assert "url" in exc.value.errors["images"]

    def test_non_list_raises(self) -> None:
        with pytest.raises(ProductValidationError):
            ProductService.normalize_images("not-a-list")  # type: ignore[arg-type]

    def test_duplicate_sort_is_extended(self) -> None:
        cleaned = ProductService.normalize_images(
            [{"url": "a.jpg", "sort": 0}, {"url": "b.jpg", "sort": 0}, {"url": "c.jpg", "sort": 2}]
        )
        assert [img["sort"] for img in cleaned] == [0, 1, 2]

    def test_main_unique_and_default_first(self) -> None:
        cleaned = ProductService.normalize_images(
            [{"url": "a.jpg", "is_main": True}, {"url": "b.jpg", "is_main": True}]
        )
        mains = [img for img in cleaned if img["is_main"]]
        assert len(mains) == 1
        assert mains[0]["url"] == "a.jpg"

    def test_no_main_uses_first(self) -> None:
        cleaned = ProductService.normalize_images([{"url": "a.jpg"}, {"url": "b.jpg"}])
        assert cleaned[0]["is_main"] is True


class TestPublishGate:
    """status=active 上架门禁：描述、图片、主图 alt 缺一不可。"""

    def test_draft_skips_gate(self) -> None:
        errors = ProductService._validate_active_gate({"status": "draft"})
        assert errors == {}

    def test_active_requires_description_and_images(self) -> None:
        errors = ProductService._validate_active_gate({"status": "active"})
        assert "description" in errors
        assert "images" in errors

    def test_active_requires_main_alt(self) -> None:
        errors = ProductService._validate_active_gate(
            {"status": "active", "description": "desc", "images": [{"url": "a.jpg", "is_main": True, "alt": ""}]}
        )
        assert "images" in errors

    def test_active_passes_with_full_data(self) -> None:
        errors = ProductService._validate_active_gate(
            {
                "status": "active",
                "description": "desc",
                "images": [{"url": "a.jpg", "is_main": True, "alt": "toy"}],
            }
        )
        assert errors == {}

    def test_update_merges_existing_values(self) -> None:
        existing = MagicMock()
        existing.description = "已有描述"
        existing.images = [{"url": "a.jpg", "is_main": True, "alt": "toy"}]
        errors = ProductService._validate_active_gate({"status": "active"}, existing=existing)
        assert errors == {}


class TestCreateProductWithVariants:
    """变体随商品上传：创建商品后批量建变体并重算总库存。"""

    async def test_variants_are_created_and_inventory_synced(self) -> None:
        db = AsyncMock()
        repo = MagicMock()
        repo.get_by_sku = AsyncMock(return_value=None)
        repo.create = AsyncMock(return_value=MagicMock(id="1001"))

        product = MagicMock()
        product.id = "1001"
        repo.create.return_value = product

        # _unique_slug / _validate_catalog_refs 直接短路
        with (
            patch.object(ProductService, "_unique_slug", new=AsyncMock(return_value="toy")),
            patch.object(ProductService, "_validate_catalog_refs", new=AsyncMock(return_value={})),
            patch(
                "forge.application.services.product_service.SQLAlchemyProductRepository",
                repo,
            ),
            patch.object(ProductService, "create_variant", new=AsyncMock()) as create_variant,
            patch(
                "forge.application.services.product_service.SQLAlchemyProductRepository.sync_product_inventory",
                new=AsyncMock(),
            ) as sync_inventory,
        ):
            result = await ProductService.create_product(
                db,
                {
                    "sku": "TOY-100",
                    "name": "Toy",
                    "category": "toys",
                    "price": 9.99,
                    "inventory": 0,
                    "status": "draft",
                    "variants": [{"name": "S", "sku": "TOY-100-S"}, {"name": "M", "sku": "TOY-100-M"}],
                },
            )

        assert result is product
        assert create_variant.await_count == 2
        sync_inventory.assert_awaited_once_with(db, 1001)

    async def test_invalid_variant_rejected(self) -> None:
        with pytest.raises(ProductValidationError) as exc:
            await ProductService.create_product(
                AsyncMock(),
                {
                    "sku": "TOY-101",
                    "name": "Toy",
                    "category": "toys",
                    "price": 9.99,
                    "inventory": 0,
                    "variants": [{"name": ""}],
                },
            )
        assert "variants" in exc.value.errors
