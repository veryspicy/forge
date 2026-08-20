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
from forge.infrastructure.persistence.repositories.product_repo import (
    SQLAlchemyProductRepository,
)
from forge.infrastructure.persistence.repositories.site_profile_repo import (
    SQLAlchemySiteProfileRepository,
)
from forge.infrastructure.services.minio_service import MinioService, get_minio_service
from forge.main.dependencies import get_current_admin, get_db

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


class StatusPayload(BaseModel):
    status: str


class VariantCreate(BaseModel):
    sku: str
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
def _coerce_uuid(value: str, field: str = "商品 ID") -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效的{field}") from None


async def _get_product_or_404(db: AsyncSession, raw_id: str) -> ORMProduct:
    product_id = _coerce_uuid(raw_id)
    product = await SQLAlchemyProductRepository.get_by_id(db, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="商品不存在")
    return product


def _clean_payload(data: dict[str, Any]) -> dict[str, Any]:
    """剔除 None 值字段，避免覆盖已有数据。"""
    return {k: v for k, v in data.items() if v is not None}


def _serialize_image(image: dict[str, Any]) -> dict[str, Any]:
    return {
        "key": image.get("key", ""),
        "url": image.get("url", ""),
        "sort": image.get("sort", 0),
        "is_main": bool(image.get("is_main", False)),
        "alt": image.get("alt", ""),
    }


def _serialize_product(product: ORMProduct) -> dict[str, Any]:
    data: dict[str, Any] = product.to_dict()
    data["images"] = [_serialize_image(i) for i in (product.images or [])]
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
    admin: dict[str, Any] = Depends(get_current_admin),
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
    admin: dict[str, Any] = Depends(get_current_admin),
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
    admin: dict[str, Any] = Depends(get_current_admin),
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
    admin: dict[str, Any] = Depends(get_current_admin),
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
    admin: dict[str, Any] = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    product = await _get_product_or_404(db, product_id)
    data = _serialize_product(product)
    variants = await SQLAlchemyProductRepository.list_variants(db, str(product.id))
    data["variants"] = [v.to_dict() for v in variants]
    return {"data": data}


# ---------------------------------------------------------------------------
# 4. 更新商品
# ---------------------------------------------------------------------------
@router.patch("/{product_id}")
async def update_product(
    product_id: str,
    payload: ProductUpdate,
    admin: dict[str, Any] = Depends(get_current_admin),
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
# 5. 上下架
# ---------------------------------------------------------------------------
@router.post("/{product_id}/status")
async def set_product_status(
    product_id: str,
    payload: StatusPayload,
    admin: dict[str, Any] = Depends(get_current_admin),
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
# 6. 上传商品图片（复用资源链路登记 ORMResource）
# ---------------------------------------------------------------------------
@router.post("/{product_id}/upload-image")
async def upload_product_image(
    product_id: str,
    file: UploadFile = File(...),
    is_main: bool = Form(default=False),
    alt: str = Form(default=""),
    admin: dict[str, Any] = Depends(get_current_admin),
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
    db.add(
        ORMResource(
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
    )
    await db.flush()

    image = {"key": image_key, "url": url, "sort": 0, "is_main": False, "alt": alt}
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
    admin: dict[str, Any] = Depends(get_current_admin),
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
# 8. 变体管理（P2-1）
# ---------------------------------------------------------------------------
async def _get_variant_or_404(db: AsyncSession, raw_id: str) -> ORMProductVariant:
    variant_id = _coerce_uuid(raw_id, "变体 ID")
    variant = await SQLAlchemyProductRepository.get_variant_by_id(db, variant_id)
    if variant is None:
        raise HTTPException(status_code=404, detail="变体不存在")
    return variant


@router.get("/{product_id}/variants")
async def list_product_variants(
    product_id: str,
    admin: dict[str, Any] = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    product = await _get_product_or_404(db, product_id)
    variants = await SQLAlchemyProductRepository.list_variants(db, str(product.id))
    return {"data": [v.to_dict() for v in variants]}


@router.post("/{product_id}/variants", status_code=201)
async def create_product_variant(
    product_id: str,
    payload: VariantCreate,
    admin: dict[str, Any] = Depends(get_current_admin),
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

    await db.commit()
    await db.refresh(variant)
    return {"data": variant.to_dict()}


@router.patch("/{product_id}/variants/{variant_id}")
async def update_product_variant(
    product_id: str,
    variant_id: str,
    payload: VariantUpdate,
    admin: dict[str, Any] = Depends(get_current_admin),
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

    await db.commit()
    await db.refresh(variant)
    return {"data": variant.to_dict()}


@router.delete("/{product_id}/variants/{variant_id}", status_code=204)
async def delete_product_variant(
    product_id: str,
    variant_id: str,
    admin: dict[str, Any] = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")

    await _get_product_or_404(db, product_id)
    variant = await _get_variant_or_404(db, variant_id)
    await SQLAlchemyProductRepository.delete_variant(db, variant)
    await db.commit()
