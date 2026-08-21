"""Admin - 供应商管理 API（P1：CRUD + 启停 + 列表筛选）。"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from forge.application.services.supplier_service import (
    SupplierNameConflictError,
    SupplierService,
    SupplierValidationError,
)
from forge.infrastructure.persistence.models import ORMSupplier
from forge.infrastructure.persistence.repositories.supplier_repo import (
    SQLAlchemySupplierRepository,
)
from forge.main.dependencies import get_db
from forge.main.rbac import require_permission

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic 模型
# ---------------------------------------------------------------------------
class SupplierCreate(BaseModel):
    name: str
    contact_email: str | None = None
    contact_phone: str | None = None
    integration_type: str = "manual"
    provider_code: str | None = None
    config: dict[str, Any] | None = None
    shipping_regions: list[str] | None = None
    default_currency: str = "USD"


class SupplierUpdate(BaseModel):
    name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    integration_type: str | None = None
    provider_code: str | None = None
    config: dict[str, Any] | None = None
    shipping_regions: list[str] | None = None
    default_currency: str | None = None
    is_active: bool | None = None


class SupplierListResponse(BaseModel):
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


async def _get_supplier_or_404(db: AsyncSession, raw_id: str) -> ORMSupplier:
    supplier_id = _coerce_uuid(raw_id)
    supplier = await SQLAlchemySupplierRepository.get_by_id(db, supplier_id)  # type: ignore[arg-type]
    if supplier is None:
        raise HTTPException(status_code=404, detail="供应商不存在")
    return supplier


def _clean_payload(data: dict[str, Any]) -> dict[str, Any]:
    """剔除 None 值字段，避免覆盖已有数据。"""
    return {k: v for k, v in data.items() if v is not None}


# ---------------------------------------------------------------------------
# 1. 创建供应商
# ---------------------------------------------------------------------------
@router.post("", status_code=201)
async def create_supplier(
    payload: SupplierCreate,
    admin: dict[str, Any] = Depends(require_permission("suppliers", "manage")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")

    data = payload.model_dump()
    try:
        supplier = await SupplierService.create_supplier(db, data)
    except SupplierNameConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except SupplierValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None

    await db.commit()
    await db.refresh(supplier)
    return {"data": supplier.to_dict()}


# ---------------------------------------------------------------------------
# 2. 供应商列表（分页 + search/is_active 筛选）
# ---------------------------------------------------------------------------
@router.get("", response_model=SupplierListResponse)
async def list_suppliers(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    search: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    admin: dict[str, Any] = Depends(require_permission("suppliers", "manage")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")

    result: dict[str, Any] = await SQLAlchemySupplierRepository.list_suppliers(
        db,
        page=page,
        page_size=page_size,
        search=search,
        is_active=is_active,
    )
    return result


# ---------------------------------------------------------------------------
# 3. 供应商详情
# ---------------------------------------------------------------------------
@router.get("/{supplier_id}")
async def get_supplier(
    supplier_id: str,
    admin: dict[str, Any] = Depends(require_permission("suppliers", "manage")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")

    supplier = await _get_supplier_or_404(db, supplier_id)
    return {"data": supplier.to_dict()}


# ---------------------------------------------------------------------------
# 4. 更新供应商
# ---------------------------------------------------------------------------
@router.patch("/{supplier_id}")
async def update_supplier(
    supplier_id: str,
    payload: SupplierUpdate,
    admin: dict[str, Any] = Depends(require_permission("suppliers", "manage")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")

    supplier = await _get_supplier_or_404(db, supplier_id)
    data = _clean_payload(payload.model_dump())
    if not data:
        raise HTTPException(status_code=400, detail="无更新字段")

    try:
        supplier = await SupplierService.update_supplier(db, supplier, data)
    except SupplierNameConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except SupplierValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None

    await db.commit()
    await db.refresh(supplier)
    return {"data": supplier.to_dict()}


# ---------------------------------------------------------------------------
# 5. 停用供应商
# ---------------------------------------------------------------------------
@router.post("/{supplier_id}/deactivate")
async def deactivate_supplier(
    supplier_id: str,
    admin: dict[str, Any] = Depends(require_permission("suppliers", "manage")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")

    supplier = await _get_supplier_or_404(db, supplier_id)
    supplier = await SupplierService.set_active(db, supplier, False)
    await db.commit()
    await db.refresh(supplier)
    return {"data": supplier.to_dict()}
