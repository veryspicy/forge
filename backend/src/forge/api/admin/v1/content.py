"""Admin - CMS 内容管理 API（轻量 CMS：CRUD + 分页筛选 + 发布/下架）。"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from forge.application.services.content_service import (
    ContentService,
    ContentSlugConflictError,
    ContentValidationError,
)
from forge.infrastructure.persistence.models import ORMContent
from forge.infrastructure.persistence.repositories.content_repo import (
    SQLAlchemyContentRepository,
)
from forge.main.dependencies import get_db
from forge.main.rbac import require_permission

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic 模型
# ---------------------------------------------------------------------------
class ContentCreate(BaseModel):
    slug: str
    title: str
    body: str = ""
    seo_title: str | None = None
    seo_description: str | None = None
    status: str = "draft"


class ContentUpdate(BaseModel):
    slug: str | None = None
    title: str | None = None
    body: str | None = None
    seo_title: str | None = None
    seo_description: str | None = None
    status: str | None = None


class ContentListResponse(BaseModel):
    items: list[dict[str, Any]]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
def _coerce_uuid(value: str, field: str = "内容 ID") -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效的{field}") from None


async def _get_content_or_404(db: AsyncSession, raw_id: str) -> ORMContent:
    content_id = _coerce_uuid(raw_id)
    content = await SQLAlchemyContentRepository.get_by_id(db, content_id)  # type: ignore[arg-type]
    if content is None:
        raise HTTPException(status_code=404, detail="内容不存在")
    return content


def _clean_payload(data: dict[str, Any]) -> dict[str, Any]:
    """剔除 None 值字段，避免覆盖已有数据。"""
    return {k: v for k, v in data.items() if v is not None}


# ---------------------------------------------------------------------------
# 1. 创建内容
# ---------------------------------------------------------------------------
@router.post("", status_code=201)
async def create_content(
    payload: ContentCreate,
    admin: dict[str, Any] = Depends(require_permission("content", "manage")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")

    data = payload.model_dump()
    try:
        content = await ContentService.create_content(db, data)
    except ContentSlugConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except ContentValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None

    await db.commit()
    await db.refresh(content)
    return {"data": content.to_dict()}


# ---------------------------------------------------------------------------
# 2. 内容列表（分页 + search/status 筛选）
# ---------------------------------------------------------------------------
@router.get("", response_model=ContentListResponse)
async def list_contents(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    search: str | None = Query(default=None),
    status: str | None = Query(default=None),
    admin: dict[str, Any] = Depends(require_permission("content", "manage")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")

    result: dict[str, Any] = await SQLAlchemyContentRepository.list_contents(
        db,
        page=page,
        page_size=page_size,
        search=search,
        status=status,
    )
    return result


# ---------------------------------------------------------------------------
# 3. 内容详情
# ---------------------------------------------------------------------------
@router.get("/{content_id}")
async def get_content(
    content_id: str,
    admin: dict[str, Any] = Depends(require_permission("content", "manage")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")

    content = await _get_content_or_404(db, content_id)
    return {"data": content.to_dict()}


# ---------------------------------------------------------------------------
# 4. 更新内容
# ---------------------------------------------------------------------------
@router.patch("/{content_id}")
async def update_content(
    content_id: str,
    payload: ContentUpdate,
    admin: dict[str, Any] = Depends(require_permission("content", "manage")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")

    content = await _get_content_or_404(db, content_id)
    data = _clean_payload(payload.model_dump())
    if not data:
        raise HTTPException(status_code=400, detail="无更新字段")

    try:
        content = await ContentService.update_content(db, content, data)
    except ContentSlugConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except ContentValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None

    await db.commit()
    await db.refresh(content)
    return {"data": content.to_dict()}


# ---------------------------------------------------------------------------
# 5. 发布 / 下架
# ---------------------------------------------------------------------------
@router.post("/{content_id}/publish")
async def publish_content(
    content_id: str,
    admin: dict[str, Any] = Depends(require_permission("content", "manage")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")

    content = await _get_content_or_404(db, content_id)
    content = await ContentService.set_status(db, content, "published")
    await db.commit()
    await db.refresh(content)
    return {"data": content.to_dict()}


@router.post("/{content_id}/unpublish")
async def unpublish_content(
    content_id: str,
    admin: dict[str, Any] = Depends(require_permission("content", "manage")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")

    content = await _get_content_or_404(db, content_id)
    content = await ContentService.set_status(db, content, "draft")
    await db.commit()
    await db.refresh(content)
    return {"data": content.to_dict()}


# ---------------------------------------------------------------------------
# 6. 删除内容
# ---------------------------------------------------------------------------
@router.delete("/{content_id}", status_code=204)
async def delete_content(
    content_id: str,
    admin: dict[str, Any] = Depends(require_permission("content", "manage")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")

    content = await _get_content_or_404(db, content_id)
    await SQLAlchemyContentRepository.delete(db, content)
    await db.commit()
    return Response(status_code=204)
