"""Product — Application Service.

承载商品业务规则：SKU 唯一校验、slug 自动生成、状态机校验、图片主图规则。
API 层负责 HTTP 语义与错误映射，本层只抛领域异常。
"""

from __future__ import annotations

import re
import unicodedata
from datetime import UTC, datetime
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
# 审核内容字段（PRODUCT-AUDIT-FLOW 联动）：命中任一字段的内容修改均需重新审核。
# 元数据字段（is_ai_generated/is_new/is_recommend/sort_order 等）不在此列，不触发回退。
CONTENT_AUDIT_FIELDS = {
    "sku",
    "name",
    "name_translations",
    "slug",
    "category",
    "category_id",
    "brand_id",
    "product_type_id",
    "description",
    "description_translations",
    "price",
    "cost",
    "inventory",
    "fulfillment_mode",
    "supplier_id",
    "supplier_sku",
    "tags",
    "images",
    "detail_blocks",
    "detail_blocks_translations",
    "seo_title",
    "seo_description",
    "seo_keywords",
    "seo_translations",
}
ALLOWED_IMAGE_MIME = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB

_ASCII_STRIP_RE = re.compile(r"[^a-z0-9]+")

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
        errors.update(ProductService._validate_active_gate(data))
        if errors:
            raise ProductValidationError("商品参数校验失败", errors)
        catalog_errors = await ProductService._validate_catalog_refs(db, data)
        if catalog_errors:
            raise ProductValidationError("商品参数校验失败", catalog_errors)

        sku = str(data["sku"]).strip()
        existing = await SQLAlchemyProductRepository.get_by_sku(db, sku)
        if existing:
            raise ProductSkuConflictError(f"SKU 已存在: {sku}")

        # 变体随商品上传（UPLOAD-WITH-VARIANTS）：创建商品后批量建变体并重算总库存
        variants = data.pop("variants", None)

        payload = dict(data)
        payload["sku"] = sku
        requested_slug = str(data.get("slug") or "").strip()
        base_slug = (
            ProductService.slugify(requested_slug) if requested_slug else ProductService.slugify(str(data["name"]))
        )
        payload["slug"] = await ProductService._unique_slug(db, base_slug)
        if data.get("detail_blocks") is not None:
            payload["detail_blocks"] = ProductService.normalize_detail_blocks(data["detail_blocks"])
        if data.get("detail_blocks_translations") is not None:
            payload["detail_blocks_translations"] = ProductService.normalize_detail_blocks_translations(
                data["detail_blocks_translations"]
            )
        payload.setdefault("status", "draft")
        payload.setdefault("images", [])
        product = await SQLAlchemyProductRepository.create(db, payload)

        if variants:
            for variant in variants:
                await ProductService.create_variant(db, product, variant)
            await SQLAlchemyProductRepository.sync_product_inventory(db, int(product.id))
        return product

    @staticmethod
    async def update_product(db: AsyncSession, product: ORMProduct, data: dict[str, Any]) -> ORMProduct:
        # PRODUCT-AUDIT-FLOW 联动：内容字段被修改后回退待审核（pending），
        # 并清空审核留痕，需重新审核通过后方可上架。
        if ProductService._needs_reaudit(data) and (product.audit_status or "pending") != "pending":
            data["audit_status"] = "pending"
            data["audit_by"] = None
            data["audited_at"] = None
            data["audit_reason"] = None

        errors = ProductService._validate_base(data, partial=True)
        errors.update(ProductService._validate_active_gate(data, existing=product))
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
        if data.get("detail_blocks_translations") is not None:
            data["detail_blocks_translations"] = ProductService.normalize_detail_blocks_translations(
                data["detail_blocks_translations"]
            )

        return await SQLAlchemyProductRepository.update(db, product, data)

    @staticmethod
    async def set_status(db: AsyncSession, product: ORMProduct, status: str) -> ORMProduct:
        if status not in VALID_STATUSES:
            raise ProductValidationError(
                "非法状态值",
                {"status": f"status 必须为 {sorted(VALID_STATUSES)} 之一"},
            )
        # PRODUCT-AUDIT-FLOW 联动：上架（active）必须审核通过（approved），
        # 未审核/被驳回的商品禁止上架；驳回已上架商品不自动下架（驳回仅影响审核态）。
        if status == "active" and (product.audit_status or "pending") != "approved":
            raise ProductValidationError(
                "商品未通过审核，无法上架",
                {"audit_status": "审核通过（approved）后才能上架"},
            )
        return await SQLAlchemyProductRepository.set_status(db, product, status)

    @staticmethod
    async def audit_product(
        db: AsyncSession,
        product: ORMProduct,
        action: str,
        reviewer: str,
        reason: str | None = None,
    ) -> ORMProduct:
        """商品审核流转：pending → approved / rejected。

        - approve：状态置 approved，reason 可选（记入审核备注）
        - reject：状态置 rejected，reason 必填（供上传方整改）
        审核人与时间随每次审核落库，可追溯（PRODUCT-AUDIT-FLOW）。
        状态机单向：仅 pending 可审核；approved/rejected 为终态，不可重复审核，
        被驳回商品需编辑保存（内容字段修改）回退 pending 后重新审核。
        """
        current = (product.audit_status or "pending")
        if current != "pending":
            raise ProductValidationError(
                "当前审核状态不可重复审核",
                {"audit_status": f"仅待审核（pending）商品可审核，当前为 {current}"},
            )
        action = (action or "").strip().lower()
        if action not in {"approve", "reject"}:
            raise ProductValidationError(
                "非法审核动作",
                {"action": "action 必须为 approve 或 reject"},
            )
        if action == "reject" and not (reason or "").strip():
            raise ProductValidationError(
                "拒绝必须填写原因",
                {"reason": "reject 时必须填写审核原因"},
            )
        reviewer = (reviewer or "").strip()
        if not reviewer:
            raise ProductValidationError(
                "缺少审核人",
                {"reviewer": "审核人不能为空"},
            )

        product.audit_status = "approved" if action == "approve" else "rejected"
        product.audit_reason = (reason or "").strip() or None
        product.audit_by = reviewer
        product.audited_at = datetime.now(UTC)
        return product

    @staticmethod
    def _needs_reaudit(data: dict[str, Any]) -> bool:
        """判断本次更新是否命中审核内容字段（PRODUCT-AUDIT-FLOW 联动）。"""
        return any(key in CONTENT_AUDIT_FIELDS for key in data)

    @staticmethod
    def normalize_images(
        images: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """清洗图片数组：结构对齐、主图唯一、url 必填、sort 唯一。

        行业标准（Shopify/Chewy）要求商品图必须可寻址：
        - url 缺失或为空 → 抛业务异常（不允许无地址图片）
        - sort 缺失按序号补齐，重复自动顺延，保证前端拖拽排序稳定
        - is_main 恰好一个；未指定主图时 sort 最小者为主图
        """
        if not isinstance(images, list):
            raise ProductValidationError("图片格式错误", {"images": "images 必须是数组"})
        cleaned: list[dict[str, Any]] = []
        main_seen = False
        used_sorts: set[int] = set()
        for idx, img in enumerate(images):
            if not isinstance(img, dict):
                raise ProductValidationError("图片格式错误", {"images": f"第 {idx + 1} 张图片必须是对象"})
            url = str(img.get("url") or "").strip()
            if not url:
                raise ProductValidationError("图片格式错误", {"images": f"第 {idx + 1} 张图片缺少 url"})
            raw_sort = img.get("sort")
            try:
                sort = int(raw_sort) if raw_sort is not None else idx
            except (TypeError, ValueError):
                raise ProductValidationError(
                    "图片格式错误",
                    {"images": f"第 {idx + 1} 张图片 sort 格式错误"},
                ) from None
            while sort in used_sorts:
                sort += 1
            used_sorts.add(sort)
            entry = {
                "key": str(img.get("key", "")),
                "url": url,
                "sort": sort,
                "is_main": bool(img.get("is_main", False)),
                "alt": str(img.get("alt", "")),
            }
            alt_translations = img.get("alt_translations")
            if isinstance(alt_translations, dict) and alt_translations:
                entry["alt_translations"] = {str(k): str(v) for k, v in alt_translations.items() if str(v).strip()}
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
    def normalize_detail_blocks_translations(translations: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
        """清洗详情块多语言：{locale: [blocks]}，每个语言的块数组走 normalize_detail_blocks。"""
        cleaned: dict[str, list[dict[str, Any]]] = {}
        for lang, blocks in translations.items():
            lang_key = str(lang).strip()
            if not lang_key:
                continue
            cleaned[lang_key] = ProductService.normalize_detail_blocks(blocks)
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

        if "images" in data and data["images"] is not None and not isinstance(data["images"], list):
            errors["images"] = "images 必须是数组"

        if "variants" in data and data["variants"] is not None:
            if not isinstance(data["variants"], list):
                errors["variants"] = "variants 必须是数组"
            else:
                for vidx, variant in enumerate(data["variants"]):
                    if not isinstance(variant, dict):
                        errors["variants"] = f"第 {vidx + 1} 个变体必须是对象"
                        break
                    vname = variant.get("name")
                    if not vname or not str(vname).strip():
                        errors["variants"] = f"第 {vidx + 1} 个变体缺少 name"
                        break

        if "slug" in data and data["slug"] and len(str(data["slug"])) > 500:
            errors["slug"] = "slug 长度不能超过 500"

        if (
            "detail_blocks" in data
            and data["detail_blocks"] is not None
            and not isinstance(data["detail_blocks"], list)
        ):
            errors["detail_blocks"] = "detail_blocks 必须是数组"

        for field in ("name_translations", "description_translations"):
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

        if "detail_blocks_translations" in data and data["detail_blocks_translations"] is not None:
            translations = data["detail_blocks_translations"]
            if not isinstance(translations, dict):
                errors["detail_blocks_translations"] = "detail_blocks_translations 必须是语言代码到详情块数组的映射对象"
            else:
                for lang, blocks in translations.items():
                    if not isinstance(lang, str) or not lang.strip():
                        errors["detail_blocks_translations"] = "detail_blocks_translations 的语言代码必须是非空字符串"
                        break
                    if not isinstance(blocks, list):
                        errors["detail_blocks_translations"] = (
                            f"detail_blocks_translations 的 {lang} 值必须是详情块数组"
                        )
                        break
                    try:
                        ProductService.normalize_detail_blocks(blocks)
                    except ProductValidationError as exc:
                        errors["detail_blocks_translations"] = (
                            f"detail_blocks_translations 的 {lang} 语言块{exc.errors}"
                        )

        if "seo_translations" in data and data["seo_translations"] is not None:
            translations = data["seo_translations"]
            if not isinstance(translations, dict):
                errors["seo_translations"] = "seo_translations 必须是语言代码到 SEO 对象的映射"
            else:
                for lang, seo in translations.items():
                    if not isinstance(lang, str) or not lang.strip():
                        errors["seo_translations"] = "seo_translations 的语言代码必须是非空字符串"
                        break
                    if not isinstance(seo, dict):
                        errors["seo_translations"] = f"seo_translations 的 {lang} 值必须是对象"
                        break
                    for key in ("title", "description"):
                        if key in seo and seo[key] is not None and not isinstance(seo[key], str):
                            errors["seo_translations"] = f"seo_translations 的 {lang}.{key} 必须是字符串"
                            break
                    if (
                        "keywords" in seo
                        and seo["keywords"] is not None
                        and (
                            not isinstance(seo["keywords"], list)
                            or not all(isinstance(k, str) for k in seo["keywords"])
                        )
                    ):
                        errors["seo_translations"] = f"seo_translations 的 {lang}.keywords 必须是字符串数组"

        return errors

    @staticmethod
    def _validate_active_gate(data: dict[str, Any], existing: ORMProduct | None = None) -> dict[str, str]:
        """上架门禁（行业标准 Shopify/Chewy）：status=active 必须满足可展示最低要求。

        - 商品描述非空
        - 至少 1 张图片
        - 主图 alt 非空（LCP/无障碍/SEO）
        update 场景传入 existing 以合并未变更字段。
        """
        errors: dict[str, str] = {}
        if data.get("status") != "active":
            return errors
        description = data.get("description")
        if description is None and existing is not None:
            description = existing.description
        if not description or not str(description).strip():
            errors["description"] = "上架商品必须填写商品描述"
        images = data.get("images")
        if images is None and existing is not None:
            images = list(existing.images or [])
        if not images:
            errors["images"] = "上架商品必须至少上传 1 张图片"
        else:
            main_image = next((i for i in images if i.get("is_main")), images[0])
            if not (main_image or {}).get("alt", "").strip():
                errors["images"] = "上架商品主图必须填写 alt 文本"
        return errors

    # ------------------------------------------------------------------
    # 变体业务（P2-1）
    # ------------------------------------------------------------------
    @staticmethod
    async def _validate_variant(data: dict[str, Any], partial: bool = False) -> dict[str, str]:
        errors: dict[str, str] = {}

        if not partial or "sku" in data:
            sku = str(data.get("sku") or "").strip()
            if not sku:
                errors["sku"] = "SKU 不能为空（变体 SKU 必须手填）"
            elif len(sku) > 100:
                errors["sku"] = "SKU 长度不能超过 100"

        if "name" in data or not partial:
            name = data.get("name")
            if not name or not str(name).strip():
                errors["name"] = "变体名称不能为空"
            elif len(str(name)) > 255:
                errors["name"] = "变体名称长度不能超过 255"

        if "name_translations" in data and data["name_translations"] is not None:
            translations = data["name_translations"]
            if not isinstance(translations, dict):
                errors["name_translations"] = "name_translations 必须是语言代码到名称的映射对象"
            else:
                for lang, text in translations.items():
                    if not isinstance(lang, str) or not lang.strip():
                        errors["name_translations"] = "name_translations 的语言代码必须是非空字符串"
                        break
                    if text is not None and not isinstance(text, str):
                        errors["name_translations"] = f"name_translations 的 {lang} 值必须是字符串"
                        break

        if "attributes" in data and data["attributes"] is not None:
            attributes = data["attributes"]
            if not isinstance(attributes, dict):
                errors["attributes"] = "attributes 必须是对象"

        if "attributes_translations" in data and data["attributes_translations"] is not None:
            translations = data["attributes_translations"]
            if not isinstance(translations, dict):
                errors["attributes_translations"] = "attributes_translations 必须是语言代码到属性映射的对象"
            else:
                invalid = False
                for lang, values in translations.items():
                    if not isinstance(lang, str) or not lang.strip():
                        errors["attributes_translations"] = "attributes_translations 的语言代码必须是非空字符串"
                        invalid = True
                        break
                    if not isinstance(values, dict):
                        errors["attributes_translations"] = (
                            f"attributes_translations 的 {lang} 值必须是 {{key: value}} 映射对象"
                        )
                        invalid = True
                        break
                    for key, text in values.items():
                        if not isinstance(key, str) or not key.strip():
                            errors["attributes_translations"] = (
                                f"attributes_translations 的 {lang} 属性键必须是非空字符串"
                            )
                            invalid = True
                            break
                        if text is not None and not isinstance(text, str):
                            errors["attributes_translations"] = (
                                f"attributes_translations 的 {lang}.{key} 值必须是字符串"
                            )
                            invalid = True
                            break
                    if invalid:
                        break

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
        sku = str(payload.get("sku") or "").strip()
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
            new_sku = str(data.get("sku") or "").strip()
            existing = await SQLAlchemyProductRepository.get_variant_by_sku(db, new_sku)
            if existing and existing.id != variant.id:
                raise ProductSkuConflictError(f"变体 SKU 已存在: {new_sku}")
            data["sku"] = new_sku

        variant = await SQLAlchemyProductRepository.update_variant(db, variant, data)

        # attributes 变更时同步规格关系表 + 产品快照
        if "attributes" in data:
            await SpecRepository.sync_variant_attributes(db, variant, data["attributes"] or {})
        return variant
