"""Product — Application Service.

承载商品业务规则：SKU 唯一校验、slug 自动生成、状态机校验、图片主图规则。
API 层负责 HTTP 语义与错误映射，本层只抛领域异常。
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from forge.infrastructure.persistence.models import ORMProduct, ORMProductVariant
from forge.infrastructure.persistence.repositories.product_repo import (
    SQLAlchemyProductRepository,
)

VALID_STATUSES = {"draft", "active", "inactive", "deleted"}
ALLOWED_IMAGE_MIME = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB

_ASCII_STRIP_RE = re.compile(r"[^a-z0-9]+")


class ProductValidationError(ValueError):
    """业务校验失败，携带字段级错误明细。"""

    def __init__(self, message: str, errors: dict[str, str] | None = None):
        super().__init__(message)
        self.errors = errors or {}


class ProductNotFoundError(LookupError):
    pass


class ProductSkuConflictError(ValueError):
    pass


class ProductService:
    """商品业务规则层。"""

    @staticmethod
    def slugify(name: str) -> str:
        normalized = unicodedata.normalize("NFKD", name)
        ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
        slug = _ASCII_STRIP_RE.sub("-", ascii_text).strip("-")
        return slug or "product"

    @staticmethod
    async def _unique_slug(db: AsyncSession, base: str) -> str:
        candidate = base
        suffix = 2
        while True:
            existing = await SQLAlchemyProductRepository.get_by_slug(db, candidate)
            if existing is None:
                return candidate
            candidate = f"{base}-{suffix}"
            suffix += 1

    @staticmethod
    async def create_product(db: AsyncSession, data: dict[str, Any]) -> ORMProduct:
        errors = ProductService._validate_base(data)
        if errors:
            raise ProductValidationError("商品参数校验失败", errors)

        sku = str(data["sku"]).strip()
        existing = await SQLAlchemyProductRepository.get_by_sku(db, sku)
        if existing:
            raise ProductSkuConflictError(f"SKU 已存在: {sku}")

        payload = dict(data)
        payload["sku"] = sku
        payload["slug"] = await ProductService._unique_slug(db, ProductService.slugify(str(data["name"])))
        payload.setdefault("status", "draft")
        payload.setdefault("images", [])
        return await SQLAlchemyProductRepository.create(db, payload)

    @staticmethod
    async def update_product(db: AsyncSession, product: ORMProduct, data: dict[str, Any]) -> ORMProduct:
        errors = ProductService._validate_base(data, partial=True)
        if errors:
            raise ProductValidationError("商品参数校验失败", errors)

        if "sku" in data and data["sku"] != product.sku:
            new_sku = str(data["sku"]).strip()
            existing = await SQLAlchemyProductRepository.get_by_sku(db, new_sku)
            if existing and existing.id != product.id:
                raise ProductSkuConflictError(f"SKU 已存在: {new_sku}")
            data["sku"] = new_sku

        return await SQLAlchemyProductRepository.update(db, product, data)

    @staticmethod
    async def set_status(db: AsyncSession, product: ORMProduct, status: str) -> ORMProduct:
        if status not in VALID_STATUSES:
            raise ProductValidationError(
                "非法状态值",
                {"status": f"status 必须为 {sorted(VALID_STATUSES)} 之一"},
            )
        return await SQLAlchemyProductRepository.set_status(db, product, status)

    @staticmethod
    def normalize_images(
        images: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """清洗图片数组：结构对齐、主图唯一；未指定主图时 sort 最小者为主图。"""
        cleaned: list[dict[str, Any]] = []
        main_seen = False
        for idx, img in enumerate(images):
            entry = {
                "key": str(img.get("key", "")),
                "url": str(img.get("url", "")),
                "sort": int(img.get("sort", idx)),
                "is_main": bool(img.get("is_main", False)),
                "alt": str(img.get("alt", "")),
            }
            if entry["is_main"]:
                if main_seen:
                    entry["is_main"] = False
                else:
                    main_seen = True
            cleaned.append(entry)
        if not main_seen and cleaned:
            cleaned[0]["is_main"] = True
        return cleaned

    @staticmethod
    async def add_image(
        db: AsyncSession,
        product: ORMProduct,
        image: dict[str, Any],
        is_main: bool = False,
        alt: str = "",
    ) -> ORMProduct:
        images = list(product.images or [])
        if is_main:
            for img in images:
                img["is_main"] = False
        entry = {
            "key": image["key"],
            "url": image["url"],
            "sort": len(images),
            "is_main": is_main or len(images) == 0,
            "alt": alt,
        }
        if image.get("resource_id"):
            entry["resource_id"] = image["resource_id"]
        images.append(entry)
        return await SQLAlchemyProductRepository.update_images(db, product, images)

    @staticmethod
    async def remove_image(db: AsyncSession, product: ORMProduct, key: str) -> ORMProduct:
        images = [img for img in (product.images or []) if img.get("key") != key]  # type: ignore[union-attr]
        if len(images) == len(product.images or []):
            raise ProductValidationError("图片不存在", {"key": key})
        if images and not any(img.get("is_main") for img in images):
            images.sort(key=lambda i: int(i.get("sort", 0)))
            images[0]["is_main"] = True
        return await SQLAlchemyProductRepository.update_images(db, product, images)

    @staticmethod
    def _validate_base(data: dict[str, Any], partial: bool = False) -> dict[str, str]:
        errors: dict[str, str] = {}

        if "sku" in data or not partial:
            sku = data.get("sku")
            if not sku or not str(sku).strip():
                errors["sku"] = "SKU 不能为空"
            elif len(str(sku)) > 100:
                errors["sku"] = "SKU 长度不能超过 100"

        if "name" in data or not partial:
            name = data.get("name")
            if not name or not str(name).strip():
                errors["name"] = "名称不能为空"
            elif len(str(name)) > 500:
                errors["name"] = "名称长度不能超过 500"

        if "category" in data or not partial:
            category = data.get("category")
            if not category or not str(category).strip():
                errors["category"] = "分类不能为空"

        if "price" in data or not partial:
            price = data.get("price")
            if price is None:
                errors["price"] = "价格不能为空"
            else:
                try:
                    if float(price) <= 0:
                        errors["price"] = "价格必须大于 0"
                except (TypeError, ValueError):
                    errors["price"] = "价格格式错误"

        if "inventory" in data or not partial:
            inventory = data.get("inventory")
            if inventory is None:
                errors["inventory"] = "库存不能为空"
            else:
                try:
                    if int(inventory) < 0:
                        errors["inventory"] = "库存不能为负"
                except (TypeError, ValueError):
                    errors["inventory"] = "库存格式错误"

        if "status" in data and data["status"] not in VALID_STATUSES:
            errors["status"] = f"status 必须为 {sorted(VALID_STATUSES)} 之一"

        if "slug" in data and data["slug"] and len(str(data["slug"])) > 500:
            errors["slug"] = "slug 长度不能超过 500"

        for field in ("name_translations", "description_translations", "ai_description_translations"):
            if field in data and data[field] is not None:
                translations = data[field]
                if not isinstance(translations, dict):
                    errors[field] = f"{field} 必须是语言代码到文本的映射对象"
                else:
                    for lang, text in translations.items():
                        if not isinstance(lang, str) or not lang.strip():
                            errors[field] = f"{field} 的语言代码必须是非空字符串"
                            break
                        if text is not None and not isinstance(text, str):
                            errors[field] = f"{field} 的 {lang} 值必须是字符串"
                            break

        return errors

    # ------------------------------------------------------------------
    # 变体业务（P2-1）
    # ------------------------------------------------------------------
    @staticmethod
    def _validate_variant(data: dict[str, Any], partial: bool = False) -> dict[str, str]:
        errors: dict[str, str] = {}

        if "sku" in data or not partial:
            sku = data.get("sku")
            if not sku or not str(sku).strip():
                errors["sku"] = "SKU 不能为空"
            elif len(str(sku)) > 100:
                errors["sku"] = "SKU 长度不能超过 100"

        if "name" in data or not partial:
            name = data.get("name")
            if not name or not str(name).strip():
                errors["name"] = "变体名称不能为空"
            elif len(str(name)) > 255:
                errors["name"] = "变体名称长度不能超过 255"

        if "attributes" in data and data["attributes"] is not None:
            attributes = data["attributes"]
            if not isinstance(attributes, dict):
                errors["attributes"] = "attributes 必须是对象"

        if "price" in data and data["price"] is not None:
            try:
                if float(data["price"]) <= 0:
                    errors["price"] = "价格必须大于 0"
            except (TypeError, ValueError):
                errors["price"] = "价格格式错误"

        if "inventory" in data and data["inventory"] is not None:
            try:
                if int(data["inventory"]) < 0:
                    errors["inventory"] = "库存不能为负"
            except (TypeError, ValueError):
                errors["inventory"] = "库存格式错误"

        if "status" in data and data["status"] not in VALID_STATUSES:
            errors["status"] = f"status 必须为 {sorted(VALID_STATUSES)} 之一"

        return errors

    @staticmethod
    async def create_variant(
        db: AsyncSession,
        product: ORMProduct,
        data: dict[str, Any],
    ) -> ORMProductVariant:
        errors = ProductService._validate_variant(data)
        if errors:
            raise ProductValidationError("变体参数校验失败", errors)

        sku = str(data["sku"]).strip()
        existing = await SQLAlchemyProductRepository.get_variant_by_sku(db, sku)
        if existing:
            raise ProductSkuConflictError(f"变体 SKU 已存在: {sku}")

        payload = dict(data)
        payload["product_id"] = product.id
        payload["sku"] = sku
        payload.setdefault("attributes", {})
        payload.setdefault("inventory", 0)
        payload.setdefault("status", "active")
        payload.setdefault("is_default", False)
        return await SQLAlchemyProductRepository.create_variant(db, payload)

    @staticmethod
    async def update_variant(
        db: AsyncSession,
        variant: ORMProductVariant,
        data: dict[str, Any],
    ) -> ORMProductVariant:
        errors = ProductService._validate_variant(data, partial=True)
        if errors:
            raise ProductValidationError("变体参数校验失败", errors)

        if "sku" in data and data["sku"] != variant.sku:
            new_sku = str(data["sku"]).strip()
            existing = await SQLAlchemyProductRepository.get_variant_by_sku(db, new_sku)
            if existing and existing.id != variant.id:
                raise ProductSkuConflictError(f"变体 SKU 已存在: {new_sku}")
            data["sku"] = new_sku

        return await SQLAlchemyProductRepository.update_variant(db, variant, data)
