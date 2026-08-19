"""Admin - 商品管理 API（P0：CRUD + 上下架 + 图片 + 列表筛选）。"""

from __future__ import annotations

import contextlib
import uuid
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
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
from forge.infrastructure.persistence.models import ORMProduct, ORMResource
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
# 3. 商品详情
# ---------------------------------------------------------------------------
@router.get("/{product_id}")
async def get_product(
    product_id: str,
    admin: dict[str, Any] = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    product = await _get_product_or_404(db, product_id)
    return {"data": _serialize_product(product)}


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
