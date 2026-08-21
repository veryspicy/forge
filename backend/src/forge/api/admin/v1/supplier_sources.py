"""Admin - 多供应商货源管理 API（P2-5：凭据/OAuth/搜索/导入/同步）。"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from forge.application.services.supplier_source_service import (
    SupplierSourceError,
    SupplierSourceService,
    get_supplier_with_provider,
)
from forge.infrastructure.persistence.models import ORMSupplier
from forge.main.dependencies import get_db
from forge.main.rbac import require_permission
from forge.suppliers.base import ProviderAuthError, ProviderConnectionError, ProviderNotFoundError
from forge.suppliers.registry import list_providers

# 触发厂商适配器注册（含 Zendrop），保证 get_provider/list_providers 可用
import forge.suppliers.bootstrap  # noqa: F401  (isort:skip)

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic 模型
# ---------------------------------------------------------------------------
class CredentialSave(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str | None = None
    expires_at: datetime | None = None


class ImportRequest(BaseModel):
    provider_product_ids: list[str]


class OAuthCallback(BaseModel):
    code: str
    state: str
    verifier: str


class SyncRequest(BaseModel):
    trigger_type: str = "manual"


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
def _coerce_uuid(value: str, field: str = "供应商 ID") -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效的{field}") from None


async def _get_supplier(db: AsyncSession, raw_id: str) -> ORMSupplier:
    supplier_id = _coerce_uuid(raw_id)
    try:
        return await get_supplier_with_provider(db, supplier_id)
    except ProviderNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except SupplierSourceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


def _auth_guard(admin: dict[str, Any]) -> None:
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")


# ---------------------------------------------------------------------------
# 1. 已注册厂商列表
# ---------------------------------------------------------------------------
@router.get("/providers")
async def providers(
    admin: dict[str, Any] = Depends(require_permission("supplier_sources", "view")),  # noqa: B008
) -> dict[str, Any]:
    return {"data": list_providers()}


# ---------------------------------------------------------------------------
# 2. 凭据管理
# ---------------------------------------------------------------------------
@router.get("/{supplier_id}/credentials")
async def get_credentials(
    supplier_id: str,
    admin: dict[str, Any] = Depends(require_permission("supplier_sources", "view")),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict[str, Any]:
    supplier = await _get_supplier(db, supplier_id)
    credential = await SupplierSourceService.get_credential(db, supplier.id)
    if credential is None:
        return {"data": None}
    return {"data": credential.to_dict()}


@router.put("/{supplier_id}/credentials")
async def save_credentials(
    supplier_id: str,
    payload: CredentialSave,
    admin: dict[str, Any] = Depends(require_permission("supplier_sources", "manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict[str, Any]:
    _auth_guard(admin)
    supplier = await _get_supplier(db, supplier_id)
    if not payload.access_token.strip():
        raise HTTPException(status_code=400, detail="access_token 不能为空")
    credential = await SupplierSourceService.save_token(
        db,
        supplier=supplier,
        access_token=payload.access_token,
        refresh_token=payload.refresh_token,
        token_type=payload.token_type,
        expires_at=payload.expires_at,
    )
    await db.commit()
    await db.refresh(credential)
    return {"data": credential.to_dict()}


# ---------------------------------------------------------------------------
# 3. OAuth2.0 PKCE
# ---------------------------------------------------------------------------
@router.get("/{supplier_id}/auth-url")
async def oauth_auth_url(
    supplier_id: str,
    admin: dict[str, Any] = Depends(require_permission("supplier_sources", "manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict[str, Any]:
    _auth_guard(admin)
    supplier = await _get_supplier(db, supplier_id)
    try:
        state, auth_url = await SupplierSourceService.start_oauth(db, supplier=supplier)
    except SupplierSourceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    await db.commit()
    return {"data": {"auth_url": auth_url, "state": state}}


@router.post("/{supplier_id}/oauth/callback")
async def oauth_callback(
    supplier_id: str,
    payload: OAuthCallback,
    admin: dict[str, Any] = Depends(require_permission("supplier_sources", "manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict[str, Any]:
    _auth_guard(admin)
    supplier = await _get_supplier(db, supplier_id)
    try:
        credential = await SupplierSourceService.complete_oauth(
            db,
            supplier=supplier,
            code=payload.code,
            state=payload.state,
            verifier=payload.verifier,
        )
    except SupplierSourceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    await db.commit()
    await db.refresh(credential)
    return {"data": credential.to_dict()}


# ---------------------------------------------------------------------------
# 4. 货源搜索
# ---------------------------------------------------------------------------
@router.get("/{supplier_id}/search")
async def search_products(
    supplier_id: str,
    keyword: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    admin: dict[str, Any] = Depends(require_permission("supplier_sources", "view")),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict[str, Any]:
    _auth_guard(admin)
    supplier = await _get_supplier(db, supplier_id)
    try:
        result = await SupplierSourceService.search_products(
            db,
            supplier=supplier,
            keyword=keyword,
            page=page,
            page_size=page_size,
        )
    except ProviderAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from None
    except ProviderConnectionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from None
    except SupplierSourceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return {"data": result}


# ---------------------------------------------------------------------------
# 5. 导入为商品草稿
# ---------------------------------------------------------------------------
@router.post("/{supplier_id}/import", status_code=201)
async def import_products(
    supplier_id: str,
    payload: ImportRequest,
    admin: dict[str, Any] = Depends(require_permission("supplier_sources", "manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict[str, Any]:
    _auth_guard(admin)
    supplier = await _get_supplier(db, supplier_id)
    if not payload.provider_product_ids:
        raise HTTPException(status_code=400, detail="请至少选择一个货源商品")
    try:
        result = await SupplierSourceService.import_products(
            db,
            supplier=supplier,
            provider_product_ids=payload.provider_product_ids,
        )
    except ProviderAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from None
    except ProviderConnectionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from None
    except SupplierSourceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return {"data": result}


# ---------------------------------------------------------------------------
# 6. 手动/定时增量同步
# ---------------------------------------------------------------------------
@router.post("/{supplier_id}/sync")
async def sync_supplier(
    supplier_id: str,
    payload: SyncRequest,
    admin: dict[str, Any] = Depends(require_permission("supplier_sources", "manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict[str, Any]:
    _auth_guard(admin)
    supplier = await _get_supplier(db, supplier_id)
    trigger = payload.trigger_type if payload.trigger_type in ("manual", "scheduled") else "manual"
    try:
        log = await SupplierSourceService.sync_supplier(db, supplier=supplier, trigger_type=trigger)
    except ProviderAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from None
    except SupplierSourceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return {"data": log.to_dict()}


# ---------------------------------------------------------------------------
# 7. 同步日志
# ---------------------------------------------------------------------------
@router.get("/{supplier_id}/sync-logs")
async def sync_logs(
    supplier_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    admin: dict[str, Any] = Depends(require_permission("supplier_sources", "view")),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict[str, Any]:
    _auth_guard(admin)
    supplier = await _get_supplier(db, supplier_id)
    logs = await SupplierSourceService.list_sync_logs(db, supplier_id=supplier.id, limit=limit)
    return {"data": logs}
