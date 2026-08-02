"""公开 API v1 — DIY 页面渲染 v2.0（Nuxt C 端调用，无需鉴权）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from forge.application.services.diy_service import DiyService
from forge.domain.diy.models import SYSTEM_PAGE_TYPES
from forge.infrastructure.persistence.repositories.diy_repo import (
    SQLAlchemyDiyRepository,
)
from forge.main.dependencies import get_db

router = APIRouter()


def get_diy_service() -> DiyService:
    return DiyService(SQLAlchemyDiyRepository())


@router.get("/pages/{page_type}")
async def get_page_by_type(
    page_type: str,
    preview: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    service: DiyService = Depends(get_diy_service),
):
    """获取系统页面渲染数据（home / category / product_detail）。

    preview=true  — 预览模式：绕过 Redis 直查 DB（允许 draft）。
    preview=false — 仅已发布页面，优先 Redis 缓存。
    """
    if page_type not in SYSTEM_PAGE_TYPES:
        raise HTTPException(status_code=404, detail="Page not found")
    payload = await service.get_page_for_render_by_type(db, page_type, preview=preview)
    if not payload:
        raise HTTPException(status_code=404, detail="Page not found")
    return payload


@router.get("/by-slug/{slug:path}")
async def get_page_by_slug(
    slug: str,
    preview: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    service: DiyService = Depends(get_diy_service),
):
    """按 slug 获取已发布的自定义页面（支持多级路径，如 promo/spring-sale）。"""
    page = await service.repo.get_page_by_slug(db, slug)
    if not page or page.page_type != "custom" or page.is_template:
        raise HTTPException(status_code=404, detail="Page not found")
    if not preview and page.status != "published":
        raise HTTPException(status_code=404, detail="Page not found")

    return await service.enrich_page_data(db, page.to_dict())
