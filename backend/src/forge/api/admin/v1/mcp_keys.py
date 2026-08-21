"""Admin - 对外 MCP Server 的 API Key 管理（P3）。

- POST   /api/admin/v1/mcp/keys        创建 API Key（明文仅返回一次）
- GET    /api/admin/v1/mcp/keys        列表
- DELETE /api/admin/v1/mcp/keys/{id}   吊销
- GET    /api/admin/v1/mcp/audit-logs  审计日志
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from forge.infrastructure.persistence.models import ORMMcpApiKey, ORMMcpAuditLog
from forge.main.dependencies import get_current_admin, get_db
from forge.mcp.auth import generate_api_key, hash_key

router = APIRouter()

VALID_SCOPES = {"read", "write", "all"}


class ApiKeyCreate(BaseModel):
    name: str
    scopes: list[str] = ["read"]


class ApiKeyListResponse(BaseModel):
    items: list[dict[str, Any]]
    total: int


class AuditLogResponse(BaseModel):
    items: list[dict[str, Any]]
    total: int
    page: int
    page_size: int


def _coerce_uuid(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的 ID") from None


async def _require_admin(admin: dict[str, Any] | None) -> None:
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")


@router.post("/keys", status_code=201)
async def create_api_key(
    payload: ApiKeyCreate,
    admin: dict[str, Any] = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _require_admin(admin)
    if not payload.name.strip():
        raise HTTPException(status_code=400, detail="名称不能为空")
    invalid = set(payload.scopes) - VALID_SCOPES
    if invalid:
        raise HTTPException(status_code=400, detail=f"无效的 scopes: {sorted(invalid)}")
    if not payload.scopes or set(payload.scopes) == {"read"}:
        raise HTTPException(status_code=400, detail="至少需要 read 或 write 权限")

    plain_key = generate_api_key()
    key = ORMMcpApiKey(
        name=payload.name.strip(),
        key_prefix=plain_key[:8],
        key_hash=hash_key(plain_key),
        scopes=list(dict.fromkeys(payload.scopes)),
    )
    db.add(key)
    await db.commit()
    await db.refresh(key)
    result = key.to_dict()
    # 明文仅此一次返回
    result["api_key"] = plain_key
    return {"data": result}


@router.get("/keys", response_model=ApiKeyListResponse)
async def list_api_keys(
    admin: dict[str, Any] = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _require_admin(admin)
    result = await db.execute(select(ORMMcpApiKey).order_by(ORMMcpApiKey.created_at.desc()))
    items = [k.to_dict() for k in result.scalars().all()]
    return {"items": items, "total": len(items)}


@router.delete("/keys/{key_id}", status_code=204)
async def revoke_api_key(
    key_id: str,
    admin: dict[str, Any] = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    await _require_admin(admin)
    raw = _coerce_uuid(key_id)
    result = await db.execute(select(ORMMcpApiKey).where(ORMMcpApiKey.id == raw))
    key = result.scalar_one_or_none()
    if key is None:
        raise HTTPException(status_code=404, detail="API Key 不存在")
    key.is_active = False
    key.revoked_at = datetime.now()
    await db.commit()


@router.get("/audit-logs", response_model=AuditLogResponse)
async def list_audit_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    tool_name: str | None = Query(default=None),
    result_status: str | None = Query(default=None),
    admin: dict[str, Any] = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _require_admin(admin)
    filters = []
    if tool_name:
        filters.append(ORMMcpAuditLog.tool_name == tool_name)
    if result_status:
        filters.append(ORMMcpAuditLog.result_status == result_status)

    from sqlalchemy import func

    total = (await db.execute(select(func.count(ORMMcpAuditLog.id)).where(*filters))).scalar_one()
    result = await db.execute(
        select(ORMMcpAuditLog)
        .where(*filters)
        .order_by(ORMMcpAuditLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = [
        {
            "id": str(log.id),
            "api_key_id": str(log.api_key_id) if log.api_key_id else None,
            "agent_name": log.agent_name,
            "tool_name": log.tool_name,
            "arguments": log.arguments or {},
            "result_status": log.result_status,
            "error": log.error,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in result.scalars().all()
    ]
    return {"items": items, "total": int(total), "page": page, "page_size": page_size}
