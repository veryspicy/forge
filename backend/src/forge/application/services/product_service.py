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
from forge.infrastructure.persistence.repositories.catalog_repo import (
    BrandRepository,
    CategoryRepository,
    ProductTypeRepository,
    SpecRepository,
)
from forge.infrastructure.persistence.repositories.product_repo import (
    SQLAlchemyProductRepository,
)

VALID_STATUSES = {"draft", "active", "inactive", "deleted"}
ALLOWED_IMAGE_MIME = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB

_ASCII_STRIP_RE = re.compile(r"[^a-z0-9]+")

# 规格值 → SKU 短码的常见颜色映射（兜底规则：大写字母数字取前 3 位）
_COLOR_SHORTCODES: dict[str, str] = {
    "black": "BLK",
    "white": "WHT",
    "red": "RED",
    "blue": "BLU",
    "green": "GRN",
    "yellow": "YLW",
    "orange": "ORG",
    "purple": "PRP",
    "pink": "PNK",
    "gray": "GRY",
    "grey": "GRY",
    "brown": "BRN",
    "navy": "NVY",
    "gold": "GLD",
    "silver": "SLV",
    "beige": "BGE",
    "cream": "CRM",
    "khaki": "KHK",
    "olive": "OLV",
    "teal": "TEL",
    "coral": "CRL",
    "ivory": "IVY",
    "maroon": "MRN",
    "turquoise": "TRQ",
}

# 商品详情块（PRODUCT-DETAIL-BLOCKS）：结构化详情，避免整段 HTML 富文本
# （XSS 面、多语言不可复用、结构化数据无法抽取）
DETAIL_BLOCK_TYPES = (
    "rich_text",
    "image",
    "image_text",
    "spec_table",
    "features",
    "faq",
    "video",
)
MAX_DETAIL_BLOCKS = 50
# 每种详情块允许的字段，其余键一律丢弃（防前端塞入任意数据）
DETAIL_BLOCK_FIELDS: dict[str, tuple[str, ...]] = {
    "rich_text": ("title", "html", "align"),
    "image": ("title", "images", "caption"),
    "image_text": ("title", "image", "html", "layout"),
    "spec_table": ("title", "columns", "rows"),
    "features": ("title", "items"),
    "faq": ("title", "items"),
    "video": ("title", "url", "poster"),
}


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
    async def _validate_catalog_refs(
        db: AsyncSession,
        data: dict[str, Any],
    ) -> dict[str, str]:
        """校验目录侧外键引用（分类/品牌/类型）存在性。"""
        errors: dict[str, str] = {}
        if data.get("category_id") is not None:
            category = await CategoryRepository.get_by_id(db, int(data["category_id"]))
            if category is None:
                errors["category_id"] = "分类不存在"
        if data.get("brand_id") is not None:
            brand = await BrandRepository.get_by_id(db, int(data["brand_id"]))
            if brand is None:
                errors["brand_id"] = "品牌不存在"
        if data.get("product_type_id") is not None:
            product_type = await ProductTypeRepository.get_by_id(db, int(data["product_type_id"]))
            if product_type is None:
                errors["product_type_id"] = "商品类型不存在"
        if errors:
            return errors
        return {}

    @staticmethod
    async def create_product(db: AsyncSession, data: dict[str, Any]) -> ORMProduct:
        errors = ProductService._validate_base(data)
        if errors:
            raise ProductValidationError("商品参数校验失败", errors)
        catalog_errors = await ProductService._validate_catalog_refs(db, data)
        if catalog_errors:
            raise ProductValidationError("商品参数校验失败", catalog_errors)

        sku = str(data["sku"]).strip()
        existing = await SQLAlchemyProductRepository.get_by_sku(db, sku)
        if existing:
            raise ProductSkuConflictError(f"SKU 已存在: {sku}")

        payload = dict(data)
        payload["sku"] = sku
        requested_slug = str(data.get("slug") or "").strip()
        base_slug = (
            ProductService.slugify(requested_slug) if requested_slug else ProductService.slugify(str(data["name"]))
        )
        payload["slug"] = await ProductService._unique_slug(db, base_slug)
        if data.get("detail_blocks") is not None:
            payload["detail_blocks"] = ProductService.normalize_detail_blocks(data["detail_blocks"])
        payload.setdefault("status", "draft")
        payload.setdefault("images", [])
        return await SQLAlchemyProductRepository.create(db, payload)

    @staticmethod
    async def update_product(db: AsyncSession, product: ORMProduct, data: dict[str, Any]) -> ORMProduct:
        errors = ProductService._validate_base(data, partial=True)
        if errors:
            raise ProductValidationError("商品参数校验失败", errors)
        catalog_errors = await ProductService._validate_catalog_refs(db, data)
        if catalog_errors:
            raise ProductValidationError("商品参数校验失败", catalog_errors)

        if "sku" in data and data["sku"] != product.sku:
            new_sku = str(data["sku"]).strip()
            existing = await SQLAlchemyProductRepository.get_by_sku(db, new_sku)
            if existing and existing.id != product.id:
                raise ProductSkuConflictError(f"SKU 已存在: {new_sku}")
            data["sku"] = new_sku

        if "slug" in data:
            requested = str(data["slug"] or "").strip()
            base_slug = (
                ProductService.slugify(requested)
                if requested
                else ProductService.slugify(str(data.get("name") or product.name))
            )
            if base_slug != product.slug:
                data["slug"] = await ProductService._unique_slug(db, base_slug)
            else:
                data.pop("slug")

        if data.get("detail_blocks") is not None:
            data["detail_blocks"] = ProductService.normalize_detail_blocks(data["detail_blocks"])

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
            if img.get("resource_id"):
                entry["resource_id"] = str(img["resource_id"])
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
    def normalize_detail_blocks(blocks: Any) -> list[dict[str, Any]]:
        """清洗商品详情块：类型/字段白名单 + 文本去空白，非法输入直接抛业务异常。"""
        if not isinstance(blocks, list):
            raise ProductValidationError("详情块格式错误", {"detail_blocks": "detail_blocks 必须是数组"})
        if len(blocks) > MAX_DETAIL_BLOCKS:
            raise ProductValidationError(
                "详情块数量超限",
                {"detail_blocks": f"最多 {MAX_DETAIL_BLOCKS} 个详情块"},
            )
        cleaned: list[dict[str, Any]] = []
        for idx, block in enumerate(blocks):
            if not isinstance(block, dict):
                raise ProductValidationError(
                    "详情块格式错误",
                    {"detail_blocks": f"第 {idx + 1} 个详情块必须是对象"},
                )
            block_type = str(block.get("type") or "").strip()
            if block_type not in DETAIL_BLOCK_TYPES:
                raise ProductValidationError(
                    "详情块类型不支持",
                    {"detail_blocks": (f"第 {idx + 1} 个详情块 type 必须为 {list(DETAIL_BLOCK_TYPES)} 之一")},
                )
            entry: dict[str, Any] = {"type": block_type}
            for field in DETAIL_BLOCK_FIELDS[block_type]:
                if field not in block or block[field] is None:
                    continue
                value = block[field]
                if field in {"items", "rows", "images", "columns"}:
                    if not isinstance(value, list):
                        raise ProductValidationError(
                            "详情块格式错误",
                            {"detail_blocks": f"第 {idx + 1} 个详情块 {field} 必须是数组"},
                        )
                    entry[field] = [ProductService._clean_block_value(item) for item in value]
                elif isinstance(value, str):
                    entry[field] = value.strip()
            cleaned.append(entry)
        return cleaned

    @staticmethod
    def _clean_block_value(value: Any) -> Any:
        """详情块数组元素：对象仅保留浅层标量键，字符串去空白。"""
        if isinstance(value, dict):
            item: dict[str, Any] = {}
            for raw_key, raw_value in value.items():
                key = str(raw_key).strip()
                if not key:
                    continue
                if isinstance(raw_value, str):
                    item[key] = raw_value.strip()
                elif isinstance(raw_value, list):
                    item[key] = [v.strip() if isinstance(v, str) else v for v in raw_value]
                elif raw_value is None or isinstance(raw_value, (int, float, bool)):
                    item[key] = raw_value
            return item
        if isinstance(value, str):
            return value.strip()
        return value

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
    async def set_images(db: AsyncSession, product: ORMProduct, images: list[dict[str, Any]]) -> ORMProduct:
        """整组替换图片：一次提交排序 / 主图 / alt 变更（Admin 图片列表拖拽保存）。"""
        if not isinstance(images, list):
            raise ProductValidationError("图片格式错误", {"images": "images 必须是数组"})
        normalized = ProductService.normalize_images(images)
        return await SQLAlchemyProductRepository.update_images(db, product, normalized)

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

        if (
            "detail_blocks" in data
            and data["detail_blocks"] is not None
            and not isinstance(data["detail_blocks"], list)
        ):
            errors["detail_blocks"] = "detail_blocks 必须是数组"

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
    def _spec_shortcode(value: str) -> str:
        """规格值 → SKU 短码。颜色走常见映射，其余大写字母数字取前 3 位。"""
        text = unicodedata.normalize("NFKD", str(value))
        ascii_text = "".join(ch for ch in text if ch.isalnum()).upper()
        if not ascii_text:
            return "X"
        lower = ascii_text.lower()
        if lower in _COLOR_SHORTCODES:
            return _COLOR_SHORTCODES[lower]
        return ascii_text[:3] if len(ascii_text) > 3 else ascii_text

    @staticmethod
    async def generate_variant_sku(
        db: AsyncSession,
        product: ORMProduct,
        attributes: dict[str, Any] | None,
    ) -> str:
        """自动生成变体 SKU：{商品货号}-{规格短码}，冲突追加序号。"""
        base = str(product.sku or product.slug or "PRODUCT").strip().upper()
        shortcodes = [
            ProductService._spec_shortcode(str(v))
            for v in (attributes or {}).values()
            if v is not None and str(v).strip()
        ]
        base_sku = f"{base}-{'-'.join(shortcodes)}" if shortcodes else f"{base}-VAR"

        candidate = base_sku
        suffix = 2
        while True:
            existing = await SQLAlchemyProductRepository.get_variant_by_sku(db, candidate)
            if existing is None:
                return candidate
            candidate = f"{base_sku}-{suffix}"
            suffix += 1

    @staticmethod
    async def _validate_variant(data: dict[str, Any], partial: bool = False) -> dict[str, str]:
        errors: dict[str, str] = {}

        if "sku" in data and data["sku"] is not None:
            sku = str(data["sku"]).strip()
            if sku and len(sku) > 100:
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
        errors = await ProductService._validate_variant(data)
        if errors:
            raise ProductValidationError("变体参数校验失败", errors)

        payload = dict(data)
        attributes = payload.get("attributes") or {}
        if not payload.get("sku") or not str(payload["sku"]).strip():
            payload["sku"] = await ProductService.generate_variant_sku(db, product, attributes)
        sku = str(payload["sku"]).strip()
        existing = await SQLAlchemyProductRepository.get_variant_by_sku(db, sku)
        if existing:
            raise ProductSkuConflictError(f"变体 SKU 已存在: {sku}")

        payload["product_id"] = product.id
        payload["sku"] = sku
        payload.setdefault("attributes", {})
        payload.setdefault("inventory", 0)
        payload.setdefault("status", "active")
        payload.setdefault("is_default", False)
        variant = await SQLAlchemyProductRepository.create_variant(db, payload)

        # 规格关系表（权威）同步 + products.attributes 读快照
        await SpecRepository.sync_variant_attributes(db, variant, payload["attributes"])
        return variant

    @staticmethod
    async def update_variant(
        db: AsyncSession,
        variant: ORMProductVariant,
        data: dict[str, Any],
    ) -> ORMProductVariant:
        errors = await ProductService._validate_variant(data, partial=True)
        if errors:
            raise ProductValidationError("变体参数校验失败", errors)

        if "sku" in data and data["sku"] != variant.sku:
            if data["sku"] and str(data["sku"]).strip():
                new_sku = str(data["sku"]).strip()
                existing = await SQLAlchemyProductRepository.get_variant_by_sku(db, new_sku)
                if existing and existing.id != variant.id:
                    raise ProductSkuConflictError(f"变体 SKU 已存在: {new_sku}")
                data["sku"] = new_sku
            else:
                # 传空 sku 表示自动重新生成
                product = await SQLAlchemyProductRepository.get_by_id(db, str(variant.product_id))
                if product is None:
                    raise ProductValidationError("商品不存在", {"product_id": "商品不存在"})
                attrs = data.get("attributes")
                if attrs is None:
                    attrs = dict(variant.attributes or {})
                data["sku"] = await ProductService.generate_variant_sku(db, product, attrs)

        variant = await SQLAlchemyProductRepository.update_variant(db, variant, data)

        # attributes 变更时同步规格关系表 + 产品快照
        if "attributes" in data:
            await SpecRepository.sync_variant_attributes(db, variant, data["attributes"] or {})
        return variant
