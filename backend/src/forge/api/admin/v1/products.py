"""Admin - 商品管理 API（P0：CRUD + 上下架 + 图片 + 列表筛选）。"""

from __future__ import annotations

import contextlib
import csv
import io
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
)
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from forge.application.services.product_service import (
    VALID_STATUSES,
    ProductService,
    ProductSkuConflictError,
    ProductValidationError,
)
from forge.infrastructure.persistence.models import ORMProduct, ORMProductVariant, ORMResource
from forge.infrastructure.persistence.repositories.catalog_repo import SpecRepository
from forge.infrastructure.persistence.repositories.product_repo import (
    SQLAlchemyProductRepository,
)
from forge.infrastructure.persistence.repositories.site_profile_repo import (
    SQLAlchemySiteProfileRepository,
)
from forge.infrastructure.services.minio_service import MinioService, get_minio_service
from forge.main.dependencies import get_db
from forge.main.rbac import require_permission

router = APIRouter()

IMAGE_ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp"}
IMAGE_SIZE_LIMIT = 5 * 1024 * 1024  # 5MB


# ---------------------------------------------------------------------------
# Pydantic 模型
# ---------------------------------------------------------------------------
class ProductCreate(BaseModel):
    sku: str
    name: str
    category: str
    description: str | None = None
    ai_description: str | None = None
    name_translations: dict[str, str] | None = None
    description_translations: dict[str, str] | None = None
    ai_description_translations: dict[str, str] | None = None
    price: float
    cost: float | None = 0.0
    inventory: int = 0
    status: str | None = "draft"
    is_ai_generated: bool | None = False
    tags: list[str] | None = None
    breed_groups: list[str] | None = None
    suitable_for: dict[str, Any] | None = None
    region_availability: list[str] | None = None
    supplier_id: str | None = None
    supplier_sku: str | None = None
    images: list[dict[str, Any]] | None = None
    seo_title: str | None = None
    seo_description: str | None = None
    seo_keywords: list[str] | None = None
    # 商品体系改造（PRODUCT-CATALOG-REFACTOR）目录侧外键
    category_id: int | None = None
    brand_id: int | None = None
    product_type_id: int | None = None


class ProductUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    description: str | None = None
    ai_description: str | None = None
    name_translations: dict[str, str] | None = None
    description_translations: dict[str, str] | None = None
    ai_description_translations: dict[str, str] | None = None
    price: float | None = None
    cost: float | None = None
    inventory: int | None = None
    sku: str | None = None
    is_ai_generated: bool | None = None
    tags: list[str] | None = None
    breed_groups: list[str] | None = None
    suitable_for: dict[str, Any] | None = None
    region_availability: list[str] | None = None
    supplier_id: str | None = None
    supplier_sku: str | None = None
    images: list[dict[str, Any]] | None = None
    seo_title: str | None = None
    seo_description: str | None = None
    seo_keywords: list[str] | None = None
    is_new: bool | None = None
    is_recommend: bool | None = None
    sort_order: int | None = None
    # 商品体系改造（PRODUCT-CATALOG-REFACTOR）目录侧外键
    category_id: int | None = None
    brand_id: int | None = None
    product_type_id: int | None = None


class StatusPayload(BaseModel):
    status: str


class BatchStatusPayload(BaseModel):
    ids: list[str]
    status: str


class VariantCreate(BaseModel):
    sku: str | None = None  # 空值自动生成 {商品货号}-{规格短码}
    name: str
    attributes: dict[str, Any] | None = None
    price: float | None = None
    cost: float | None = None
    inventory: int | None = 0
    status: str | None = "active"
    is_default: bool | None = False


class VariantUpdate(BaseModel):
    sku: str | None = None
    name: str | None = None
    attributes: dict[str, Any] | None = None
    price: float | None = None
    cost: float | None = None
    inventory: int | None = None
    status: str | None = None
    is_default: bool | None = None


class ProductListResponse(BaseModel):
    items: list[dict[str, Any]]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
def _coerce_uuid(value: str, field: str = "供应商 ID") -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效的{field}") from None


def _coerce_product_id(value: str, field: str = "商品 ID") -> int:
    try:
        return int(str(value))
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail=f"无效的{field}") from None


async def _get_product_or_404(db: AsyncSession, raw_id: str) -> ORMProduct:
    product_id = _coerce_product_id(raw_id)
    product = await SQLAlchemyProductRepository.get_by_id(db, product_id)  # type: ignore[arg-type]
    if product is None:
        raise HTTPException(status_code=404, detail="商品不存在")
    return product


def _clean_payload(data: dict[str, Any]) -> dict[str, Any]:
    """剔除 None 值字段，避免覆盖已有数据。"""
    return {k: v for k, v in data.items() if v is not None}


def _serialize_image(image: dict[str, Any]) -> dict[str, Any]:
    data = {
        "key": image.get("key", ""),
        "url": image.get("url", ""),
        "sort": image.get("sort", 0),
        "is_main": bool(image.get("is_main", False)),
        "alt": image.get("alt", ""),
    }
    if image.get("resource_id"):
        data["resource_id"] = image["resource_id"]
    return data


def _serialize_product(product: ORMProduct) -> dict[str, Any]:
    data: dict[str, Any] = product.to_dict()
    data["images"] = [_serialize_image(i) for i in (product.images or [])]  # type: ignore[union-attr]
    return data


async def _active_site_id(db: AsyncSession) -> str:
    profile = await SQLAlchemySiteProfileRepository.get_active(db)
    if profile is None:
        raise HTTPException(status_code=500, detail="未找到 active 站点配置")
    return str(profile.id)


# ---------------------------------------------------------------------------
# 1. 创建商品
# ---------------------------------------------------------------------------
@router.post("", status_code=201)
async def create_product(
    payload: ProductCreate,
    admin: dict[str, Any] = Depends(require_permission("products", "create")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")

    data = payload.model_dump()
    if data.get("images") is not None:
        data["images"] = ProductService.normalize_images(data["images"])
    if data.get("supplier_id"):
        data["supplier_id"] = _coerce_uuid(data["supplier_id"], "supplier_id")

    try:
        product = await ProductService.create_product(db, data)
    except ProductSkuConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except ProductValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None

    await db.commit()
    await db.refresh(product)
    return {"data": _serialize_product(product)}


# ---------------------------------------------------------------------------
# 2. 商品列表（分页 + search/category/status 筛选）
# ---------------------------------------------------------------------------
@router.get("", response_model=ProductListResponse)
async def list_products(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    category: str | None = Query(default=None),
    search: str | None = Query(default=None),
    status: str | None = Query(default=None),
    sort_by: str = Query(default="default", description="排序档：default/sort_order/sales/newest/price_asc/price_desc"),
    admin: dict[str, Any] = Depends(require_permission("products", "view")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if status and status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"status 必须为 {sorted(VALID_STATUSES)} 之一",
        )
    result: dict[str, Any] = await SQLAlchemyProductRepository.list_products(
        db,
        page=page,
        page_size=page_size,
        category=category,
        search=search,
        status=status,
        sort_by=sort_by,
    )
    result["items"] = [_normalize_images_in_dict(p) for p in result["items"]]
    return result


def _normalize_images_in_dict(item: dict[str, Any]) -> dict[str, Any]:
    """列表轻量序列化：规范化 images 元素字段。"""
    if isinstance(item.get("images"), list):
        item["images"] = [_serialize_image(i) for i in item["images"]]
    return item


# ---------------------------------------------------------------------------
# 3. 批量导出 / 导入（P2-2）
# ---------------------------------------------------------------------------
IMPORT_SIZE_LIMIT = 2 * 1024 * 1024  # 2MB
LIST_SEPARATOR = "|"

EXPORT_COLUMNS = [
    "sku",
    "name",
    "category",
    "description",
    "price",
    "cost",
    "inventory",
    "status",
    "is_ai_generated",
    "tags",
    "breed_groups",
    "region_availability",
    "supplier_sku",
]
REQUIRED_IMPORT_COLUMNS = ("sku", "name", "category", "price")


def _join_list(values: Any) -> str:
    if not values:
        return ""
    if isinstance(values, str):
        return values
    return LIST_SEPARATOR.join(str(v) for v in values)


def _split_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    text = str(value).strip()
    if not text:
        return []
    return [item.strip() for item in text.split(LIST_SEPARATOR) if item.strip()]


def _parse_bool(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "是"}


def _parse_product_row(raw: dict[str, str]) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    sku = (raw.get("sku") or "").strip()
    name = (raw.get("name") or "").strip()
    category = (raw.get("category") or "").strip()
    if not sku:
        errors.append("SKU 不能为空")
    if not name:
        errors.append("名称不能为空")
    if not category:
        errors.append("分类不能为空")

    data: dict[str, Any] = {"sku": sku, "name": name, "category": category}

    description = (raw.get("description") or "").strip()
    if description:
        data["description"] = description

    raw_price = (raw.get("price") or "").strip()
    if raw_price:
        try:
            price = float(raw_price)
            if price <= 0:
                errors.append("价格必须大于 0")
            data["price"] = price
        except ValueError:
            errors.append("价格格式错误")
    else:
        errors.append("价格不能为空")

    raw_cost = (raw.get("cost") or "").strip()
    if raw_cost:
        try:
            data["cost"] = float(raw_cost)
        except ValueError:
            errors.append("成本格式错误")

    raw_inventory = (raw.get("inventory") or "").strip()
    if raw_inventory:
        try:
            inventory = int(raw_inventory)
            if inventory < 0:
                errors.append("库存不能为负")
            data["inventory"] = inventory
        except ValueError:
            errors.append("库存格式错误")

    status = (raw.get("status") or "draft").strip()
    if status not in VALID_STATUSES:
        errors.append(f"status 必须为 {sorted(VALID_STATUSES)} 之一")
    else:
        data["status"] = status

    data["is_ai_generated"] = _parse_bool(raw.get("is_ai_generated"))

    tags = _split_list(raw.get("tags"))
    if tags:
        data["tags"] = tags
    breed_groups = _split_list(raw.get("breed_groups"))
    if breed_groups:
        data["breed_groups"] = breed_groups
    regions = _split_list(raw.get("region_availability"))
    if regions:
        data["region_availability"] = regions

    supplier_sku = (raw.get("supplier_sku") or "").strip()
    if supplier_sku:
        data["supplier_sku"] = supplier_sku

    return data, errors


@router.get("/export")
async def export_products(
    admin: dict[str, Any] = Depends(require_permission("products", "view")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")

    products = await SQLAlchemyProductRepository.list_all(db)
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=EXPORT_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for product in products:
        data = product.to_dict()
        writer.writerow(
            {
                "sku": data.get("sku", ""),
                "name": data.get("name", ""),
                "category": data.get("category", ""),
                "description": data.get("description") or "",
                "price": data.get("price", 0),
                "cost": data.get("cost") if data.get("cost") is not None else "",
                "inventory": data.get("inventory", 0),
                "status": data.get("status", "draft"),
                "is_ai_generated": "1" if data.get("is_ai_generated") else "0",
                "tags": _join_list(data.get("tags")),
                "breed_groups": _join_list(data.get("breed_groups")),
                "region_availability": _join_list(data.get("region_availability")),
                "supplier_sku": data.get("supplier_sku") or "",
            }
        )
    content = "\ufeff" + buffer.getvalue()
    filename = f"products_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        content=content.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/import")
async def import_products(
    file: UploadFile = File(...),
    admin: dict[str, Any] = Depends(require_permission("products", "create")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")

    filename = (file.filename or "").lower()
    if not filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="仅支持 CSV 文件")
    content = await file.read()
    if len(content) > IMPORT_SIZE_LIMIT:
        raise HTTPException(status_code=400, detail="文件大小不能超过 2MB")

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="文件编码需为 UTF-8") from None

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV 缺少表头")
    missing = [c for c in REQUIRED_IMPORT_COLUMNS if c not in reader.fieldnames]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"缺少必需列: {', '.join(missing)}",
        )

    created = 0
    updated = 0
    errors: list[dict[str, Any]] = []
    seen_skus: set[str] = set()

    for idx, raw in enumerate(reader, start=2):
        if not any((raw.get(col) or "").strip() for col in reader.fieldnames):
            continue  # 跳过空行
        data, row_errors = _parse_product_row(raw)
        sku = str(data.get("sku") or "").strip()
        if row_errors:
            errors.append({"row": idx, "sku": sku, "error": "; ".join(row_errors)})
            continue
        if sku in seen_skus:
            errors.append({"row": idx, "sku": sku, "error": "文件内 SKU 重复，已跳过（以首次出现行为准）"})
            continue
        seen_skus.add(sku)

        try:
            existing = await SQLAlchemyProductRepository.get_by_sku(db, sku)
            if existing is None:
                await ProductService.create_product(db, data)
                created += 1
            else:
                update_data = {k: v for k, v in data.items() if k != "sku"}
                await ProductService.update_product(db, existing, update_data)
                updated += 1
        except (ProductSkuConflictError, ProductValidationError) as exc:
            errors.append({"row": idx, "sku": sku, "error": str(exc)})

    await db.commit()
    return {
        "data": {
            "created": created,
            "updated": updated,
            "failed": len(errors),
            "errors": errors[:200],
        }
    }


# ---------------------------------------------------------------------------
# 4. 商品详情
# ---------------------------------------------------------------------------
@router.get("/{product_id}")
async def get_product(
    product_id: str,
    admin: dict[str, Any] = Depends(require_permission("products", "view")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    product = await _get_product_or_404(db, product_id)
    data = _serialize_product(product)
    variants = await SQLAlchemyProductRepository.list_variants(db, int(product.id))
    data["variants"] = [v.to_dict() for v in variants]
    return {"data": data}


# ---------------------------------------------------------------------------
# 4. 更新商品
# ---------------------------------------------------------------------------
@router.patch("/{product_id}")
async def update_product(
    product_id: str,
    payload: ProductUpdate,
    admin: dict[str, Any] = Depends(require_permission("products", "edit")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")

    product = await _get_product_or_404(db, product_id)
    data = _clean_payload(payload.model_dump())
    if not data:
        raise HTTPException(status_code=400, detail="无更新字段")

    if data.get("images") is not None:
        data["images"] = ProductService.normalize_images(data["images"])
    if data.get("supplier_id"):
        data["supplier_id"] = _coerce_uuid(data["supplier_id"], "supplier_id")

    try:
        product = await ProductService.update_product(db, product, data)
    except ProductSkuConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except ProductValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None

    await db.commit()
    await db.refresh(product)
    return {"data": _serialize_product(product)}


# ---------------------------------------------------------------------------
# 4.5 批量状态变更（含批量删除）
# ---------------------------------------------------------------------------
@router.post("/batch-status")
async def batch_set_product_status(
    payload: BatchStatusPayload,
    admin: dict[str, Any] = Depends(require_permission("products", "status")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")

    if not payload.ids:
        raise HTTPException(status_code=400, detail="ids 不能为空")
    if len(payload.ids) > 200:
        raise HTTPException(status_code=400, detail="单次批量操作最多 200 个商品")
    if payload.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"status 必须为 {sorted(VALID_STATUSES)} 之一",
        )

    ids: list[str] = []
    for raw_id in dict.fromkeys(payload.ids):
        ids.append(str(_coerce_product_id(raw_id)))

    products = await SQLAlchemyProductRepository.list_by_ids(db, ids)
    existing_ids = {str(p.id) for p in products}
    missing = [pid for pid in ids if pid not in existing_ids]

    for product in products:
        await ProductService.set_status(db, product, payload.status)

    await db.commit()
    return {
        "data": {
            "updated": len(products),
            "missing": missing,
        }
    }


# ---------------------------------------------------------------------------
# 5. 上下架
# ---------------------------------------------------------------------------
@router.post("/{product_id}/status")
async def set_product_status(
    product_id: str,
    payload: StatusPayload,
    admin: dict[str, Any] = Depends(require_permission("products", "status")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")

    product = await _get_product_or_404(db, product_id)
    try:
        product = await ProductService.set_status(db, product, payload.status)
    except ProductValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None

    await db.commit()
    await db.refresh(product)
    return {"data": _serialize_product(product)}


# ---------------------------------------------------------------------------
# 5.5 删除（软删除）
# ---------------------------------------------------------------------------
@router.delete("/{product_id}")
async def delete_product(
    product_id: str,
    admin: dict[str, Any] = Depends(require_permission("products", "delete")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")

    product = await _get_product_or_404(db, product_id)
    if product.status == "deleted":
        raise HTTPException(status_code=400, detail="商品已删除")

    await ProductService.set_status(db, product, "deleted")
    await db.commit()
    return {"data": {"id": str(product.id), "status": "deleted"}}


# ---------------------------------------------------------------------------
# 6. 上传商品图片（复用资源链路登记 ORMResource）
# ---------------------------------------------------------------------------
@router.post("/{product_id}/upload-image")
async def upload_product_image(
    product_id: str,
    file: UploadFile = File(...),
    is_main: bool = Form(default=False),
    alt: str = Form(default=""),
    admin: dict[str, Any] = Depends(require_permission("products", "edit")),
    db: AsyncSession = Depends(get_db),
    minio: MinioService = Depends(get_minio_service),
) -> dict[str, Any]:
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")

    product = await _get_product_or_404(db, product_id)
    mime = file.content_type or ""
    if mime not in IMAGE_ALLOWED_MIME:
        raise HTTPException(status_code=400, detail="仅支持 JPEG/PNG/WebP 图片")
    content = await file.read()
    if len(content) > IMAGE_SIZE_LIMIT:
        raise HTTPException(status_code=400, detail="图片大小不能超过 5MB")

    ext = {  # noqa: SIM300
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }[mime]
    site_id = await _active_site_id(db)
    image_key = f"site/{site_id}/products/{product.id}/{uuid.uuid4().hex}{ext}"
    url = minio.upload_object(content, image_key, content_type=mime)

    # 登记资源表，供资源管理页可见与统一管理
    bucket = getattr(minio, "_bucket", "") or ""
    resource = ORMResource(
        site_id=uuid.UUID(site_id),
        bucket=bucket,
        object_key=image_key,
        url=url,
        file_type="image",
        mime=mime,
        file_size=len(content),
        name=(file.filename or f"{uuid.uuid4().hex}{ext}").strip(),
        directory=f"products/{product.id}",
    )
    db.add(resource)
    await db.flush()

    image = {
        "key": image_key,
        "url": url,
        "sort": 0,
        "is_main": False,
        "alt": alt,
        "resource_id": str(resource.id),
    }
    try:
        product = await ProductService.add_image(db, product, image, is_main=is_main, alt=alt)
    except ProductValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None

    await db.commit()
    await db.refresh(product)
    return {"data": _serialize_product(product)}


# ---------------------------------------------------------------------------
# 7. 删除商品图片
# ---------------------------------------------------------------------------
@router.delete("/{product_id}/images/{key:path}")
async def delete_product_image(
    product_id: str,
    key: str,
    admin: dict[str, Any] = Depends(require_permission("products", "edit")),
    db: AsyncSession = Depends(get_db),
    minio: MinioService = Depends(get_minio_service),
) -> dict[str, Any]:
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")

    product = await _get_product_or_404(db, product_id)
    try:
        product = await ProductService.remove_image(db, product, key)
    except ProductValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None

    # 删除 MinIO 对象（失败不阻塞 DB 更新）
    with contextlib.suppress(Exception):
        minio.remove_object(key)

    await db.commit()
    await db.refresh(product)
    return {"data": _serialize_product(product)}


# ---------------------------------------------------------------------------
# 8. SEO 评分（P2-3）
# ---------------------------------------------------------------------------
SEO_TITLE_IDEAL_MIN = 30
SEO_TITLE_IDEAL_MAX = 60
SEO_DESC_IDEAL_MIN = 70
SEO_DESC_IDEAL_MAX = 160
SEO_DESC_MIN_LEN = 100
SEO_TRANSLATION_SCORE_PER_LANG = 5
SEO_TRANSLATION_MAX = 10


def _seo_dimension(
    key: str,
    label: str,
    score: int,
    max_score: int,
    suggestion: str,
) -> dict[str, Any]:
    status = "pass" if score >= max_score else ("partial" if score > 0 else "fail")
    return {
        "key": key,
        "label": label,
        "score": score,
        "max": max_score,
        "status": status,
        "suggestion": suggestion if score < max_score else "",
    }


def compute_seo_score(product: ORMProduct) -> dict[str, Any]:
    """计算商品 SEO 字段完整性评分（0-100）与优化建议。"""
    dimensions: list[dict[str, Any]] = []
    suggestions: list[str] = []

    # 1. SEO 标题
    seo_title = (product.seo_title or "").strip()
    title_len = len(seo_title)
    if not seo_title:
        dim = _seo_dimension(
            "seo_title",
            "SEO 标题",
            0,
            20,
            f"未设置 SEO 标题，建议填写 {SEO_TITLE_IDEAL_MIN}-{SEO_TITLE_IDEAL_MAX} 字符的标题",
        )
    elif SEO_TITLE_IDEAL_MIN <= title_len <= SEO_TITLE_IDEAL_MAX:
        dim = _seo_dimension("seo_title", "SEO 标题", 20, 20, "")
    else:
        dim = _seo_dimension(
            "seo_title",
            "SEO 标题",
            12,
            20,
            f"SEO 标题当前 {title_len} 字符，建议调整到 {SEO_TITLE_IDEAL_MIN}-{SEO_TITLE_IDEAL_MAX} 字符",
        )
    dimensions.append(dim)
    if dim["suggestion"]:
        suggestions.append(dim["suggestion"])

    # 2. SEO 描述
    seo_desc = (product.seo_description or "").strip()
    desc_len = len(seo_desc)
    if not seo_desc:
        dim = _seo_dimension(
            "seo_description",
            "SEO 描述",
            0,
            20,
            f"未设置 SEO 描述，建议填写 {SEO_DESC_IDEAL_MIN}-{SEO_DESC_IDEAL_MAX} 字符的描述",
        )
    elif SEO_DESC_IDEAL_MIN <= desc_len <= SEO_DESC_IDEAL_MAX:
        dim = _seo_dimension("seo_description", "SEO 描述", 20, 20, "")
    else:
        dim = _seo_dimension(
            "seo_description",
            "SEO 描述",
            12,
            20,
            f"SEO 描述当前 {desc_len} 字符，建议调整到 {SEO_DESC_IDEAL_MIN}-{SEO_DESC_IDEAL_MAX} 字符",
        )
    dimensions.append(dim)
    if dim["suggestion"]:
        suggestions.append(dim["suggestion"])

    # 3. SEO 关键词
    keywords = [k.strip() for k in (product.seo_keywords or []) if k and k.strip()]
    kw_count = len(keywords)
    if kw_count >= 3:
        dim = _seo_dimension("seo_keywords", "SEO 关键词", 15, 15, "")
    elif kw_count >= 1:
        dim = _seo_dimension(
            "seo_keywords",
            "SEO 关键词",
            8,
            15,
            f"当前 {kw_count} 个关键词，建议补充到 3 个以上",
        )
    else:
        dim = _seo_dimension("seo_keywords", "SEO 关键词", 0, 15, "未设置 SEO 关键词，建议至少填写 3 个")
    dimensions.append(dim)
    if dim["suggestion"]:
        suggestions.append(dim["suggestion"])

    # 4. 商品描述
    description = (product.description or "").strip()
    desc_main_len = len(description)
    if desc_main_len >= SEO_DESC_MIN_LEN:
        dim = _seo_dimension("description", "商品描述", 10, 10, "")
    elif description:
        dim = _seo_dimension(
            "description",
            "商品描述",
            5,
            10,
            f"商品描述当前 {desc_main_len} 字符，建议补充到 {SEO_DESC_MIN_LEN} 字符以上",
        )
    else:
        dim = _seo_dimension("description", "商品描述", 0, 10, "未填写商品描述，建议补充详细的商品介绍")
    dimensions.append(dim)
    if dim["suggestion"]:
        suggestions.append(dim["suggestion"])

    # 5. 图片（主图 + alt）
    images = product.images or []  # type: ignore[var-annotated]
    main_image = next((i for i in images if i.get("is_main")), None)  # type: ignore[union-attr]
    first_image = images[0] if images else None
    has_alt = bool((main_image or first_image or {}).get("alt", "").strip())
    if main_image and has_alt:
        dim = _seo_dimension("images", "商品图片", 10, 10, "")
    elif main_image or first_image:
        dim = _seo_dimension(
            "images",
            "商品图片",
            5,
            10,
            "已上传图片但缺少 alt 文本，建议为图片补充描述性 alt",
        )
    else:
        dim = _seo_dimension("images", "商品图片", 0, 10, "未上传商品图片，建议至少上传 1 张主图并填写 alt")
    dimensions.append(dim)
    if dim["suggestion"]:
        suggestions.append(dim["suggestion"])

    # 6. 标签
    tags = [t.strip() for t in (product.tags or []) if t and t.strip()]
    tag_count = len(tags)
    if tag_count >= 3:
        dim = _seo_dimension("tags", "标签", 10, 10, "")
    elif tag_count >= 1:
        dim = _seo_dimension("tags", "标签", 5, 10, f"当前 {tag_count} 个标签，建议补充到 3 个以上")
    else:
        dim = _seo_dimension("tags", "标签", 0, 10, "未设置标签，建议添加至少 3 个商品标签")
    dimensions.append(dim)
    if dim["suggestion"]:
        suggestions.append(dim["suggestion"])

    # 7. slug
    slug = (product.slug or "").strip()
    if not slug:
        dim = _seo_dimension("slug", "URL Slug", 0, 5, "未设置 slug，建议使用简短含关键词的英文 URL")
    elif len(slug) > 100:
        dim = _seo_dimension("slug", "URL Slug", 3, 5, f"slug 当前 {len(slug)} 字符，建议缩短到 100 字符以内")
    else:
        dim = _seo_dimension("slug", "URL Slug", 5, 5, "")
    dimensions.append(dim)
    if dim["suggestion"]:
        suggestions.append(dim["suggestion"])

    # 8. 多语言覆盖（name/description 翻译）
    name_translations = product.name_translations or {}  # type: ignore[var-annotated]
    desc_translations = product.description_translations or {}  # type: ignore[var-annotated]
    covered_langs = {
        lang
        for lang in set(name_translations) | set(desc_translations)
        if (name_translations.get(lang) or "").strip() or (desc_translations.get(lang) or "").strip()
    }
    translation_score = min(len(covered_langs) * SEO_TRANSLATION_SCORE_PER_LANG, SEO_TRANSLATION_MAX)
    if translation_score >= SEO_TRANSLATION_MAX:
        dim = _seo_dimension("translations", "多语言覆盖", SEO_TRANSLATION_MAX, SEO_TRANSLATION_MAX, "")
    elif translation_score > 0:
        target_langs = SEO_TRANSLATION_MAX // SEO_TRANSLATION_SCORE_PER_LANG
        dim = _seo_dimension(
            "translations",
            "多语言覆盖",
            translation_score,
            SEO_TRANSLATION_MAX,
            f"已覆盖 {len(covered_langs)} 门语言，建议补充到 {target_langs} 门语言以上",
        )
    else:
        dim = _seo_dimension(
            "translations",
            "多语言覆盖",
            0,
            SEO_TRANSLATION_MAX,
            "未填写任何语言翻译，建议至少补充英语外的 2 门语言翻译",
        )
    dimensions.append(dim)
    if dim["suggestion"]:
        suggestions.append(dim["suggestion"])

    total_score = sum(d["score"] for d in dimensions)
    if total_score >= 90:
        grade = "A"
    elif total_score >= 75:
        grade = "B"
    elif total_score >= 60:
        grade = "C"
    else:
        grade = "D"

    return {
        "product_id": str(product.id),
        "total_score": total_score,
        "grade": grade,
        "dimensions": dimensions,
        "suggestions": suggestions,
        "checked_at": datetime.now(UTC).isoformat(),
    }


@router.get("/{product_id}/seo-score")
async def get_product_seo_score(
    product_id: str,
    admin: dict[str, Any] = Depends(require_permission("products", "view")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    product = await _get_product_or_404(db, product_id)
    return {"data": compute_seo_score(product)}


# ---------------------------------------------------------------------------
# 9. 变体管理（P2-1）
# ---------------------------------------------------------------------------
async def _get_variant_or_404(db: AsyncSession, raw_id: str) -> ORMProductVariant:
    variant_id = _coerce_uuid(raw_id, "变体 ID")
    variant = await SQLAlchemyProductRepository.get_variant_by_id(db, variant_id)  # type: ignore[arg-type]
    if variant is None:
        raise HTTPException(status_code=404, detail="变体不存在")
    return variant


@router.get("/{product_id}/variants")
async def list_product_variants(
    product_id: str,
    admin: dict[str, Any] = Depends(require_permission("products", "view")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    product = await _get_product_or_404(db, product_id)
    variants = await SQLAlchemyProductRepository.list_variants(db, int(product.id))
    items: list[dict[str, Any]] = []
    for variant in variants:
        data = variant.to_dict()
        # 规格关系表（权威）补充：key 名 + value，供行内编辑表格使用
        data["specs"] = await SpecRepository.list_variant_spec_details(db, str(variant.id))
        items.append(data)
    return {"data": items}


@router.post("/{product_id}/variants", status_code=201)
async def create_product_variant(
    product_id: str,
    payload: VariantCreate,
    admin: dict[str, Any] = Depends(require_permission("products", "edit")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")

    product = await _get_product_or_404(db, product_id)
    data = payload.model_dump()
    try:
        variant = await ProductService.create_variant(db, product, data)
    except ProductSkuConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except ProductValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None

    await SQLAlchemyProductRepository.sync_product_inventory(db, int(product.id))
    await db.commit()
    await db.refresh(variant)
    return {"data": variant.to_dict()}


@router.patch("/{product_id}/variants/{variant_id}")
async def update_product_variant(
    product_id: str,
    variant_id: str,
    payload: VariantUpdate,
    admin: dict[str, Any] = Depends(require_permission("products", "edit")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")

    await _get_product_or_404(db, product_id)
    variant = await _get_variant_or_404(db, variant_id)
    data = _clean_payload(payload.model_dump())
    if not data:
        raise HTTPException(status_code=400, detail="无更新字段")

    try:
        variant = await ProductService.update_variant(db, variant, data)
    except ProductSkuConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except ProductValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None

    await SQLAlchemyProductRepository.sync_product_inventory(db, int(variant.product_id))
    await db.commit()
    await db.refresh(variant)
    return {"data": variant.to_dict()}


@router.delete("/{product_id}/variants/{variant_id}", status_code=204)
async def delete_product_variant(
    product_id: str,
    variant_id: str,
    admin: dict[str, Any] = Depends(require_permission("products", "edit")),
    db: AsyncSession = Depends(get_db),
) -> None:
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")

    await _get_product_or_404(db, product_id)
    variant = await _get_variant_or_404(db, variant_id)
    await SQLAlchemyProductRepository.delete_variant(db, variant)
    await SQLAlchemyProductRepository.sync_product_inventory(db, int(variant.product_id))
    # 删除后重算 products.attributes 读快照（variant_specs 由外键 CASCADE 清理）
    product = await SQLAlchemyProductRepository.get_by_id(db, str(variant.product_id))
    if product is not None:
        await SpecRepository.sync_product_attributes(db, int(product.id))
    await db.commit()
