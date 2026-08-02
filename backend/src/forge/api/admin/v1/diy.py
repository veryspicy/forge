"""Admin API v1 — DIY 页面装修管理 v2.0。

挂载前缀：/api/admin/v1/site
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from forge.application.services.diy_service import DiyService
from forge.domain.diy.models import SYSTEM_PAGE_TYPES
from forge.infrastructure.persistence.repositories.diy_repo import (
    SQLAlchemyDiyRepository,
)
from forge.main.dependencies import get_db, require_permission

router = APIRouter()


def get_diy_service() -> DiyService:
    return DiyService(SQLAlchemyDiyRepository())


# ------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------


async def _resolve_page(service: DiyService, db: AsyncSession, key: str):
    """按 key（UUID 或 page_type）解析页面。"""
    if key in SYSTEM_PAGE_TYPES:
        page = await service.repo.get_page_by_type(db, key)
    else:
        try:
            page = await service.repo.get_page_by_id(db, UUID(key))
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Invalid page key")
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    return page


# ------------------------------------------------------------------
# 页面列表 / 详情
# ------------------------------------------------------------------


@router.get(
    "/pages",
    dependencies=[Depends(require_permission("settings", "manage"))],
)
async def list_site_pages(
    db: AsyncSession = Depends(get_db),
    service: DiyService = Depends(get_diy_service),
):
    """站点编辑器页面概览：系统页面卡片 + 自定义页面列表。"""
    return await service.repo.list_site_pages(db)


@router.get(
    "/pages/{key}",
    dependencies=[Depends(require_permission("settings", "manage"))],
)
async def get_page(
    key: str,
    db: AsyncSession = Depends(get_db),
    service: DiyService = Depends(get_diy_service),
):
    """获取页面详情（含组件）。key = UUID 或 page_type。"""
    page = await _resolve_page(service, db, key)
    return page.to_dict()


# ------------------------------------------------------------------
# 自定义页面 CRUD
# ------------------------------------------------------------------


@router.post(
    "/custom-pages",
    dependencies=[Depends(require_permission("settings", "manage"))],
    status_code=201,
)
async def create_page(
    data: dict,
    db: AsyncSession = Depends(get_db),
    service: DiyService = Depends(get_diy_service),
):
    """创建自定义页面。"""
    data.setdefault("page_type", "custom")
    data.setdefault("status", "draft")
    return (await service.create_page(db, data)).to_dict()


@router.put(
    "/pages/{key}",
    dependencies=[Depends(require_permission("settings", "manage"))],
)
async def update_page(
    key: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
    service: DiyService = Depends(get_diy_service),
):
    """更新页面元数据。系统页不允许修改 page_type / slug。"""
    page = await _resolve_page(service, db, key)
    if page.page_type in SYSTEM_PAGE_TYPES:
        data.pop("page_type", None)
        data.pop("slug", None)
    result = await service.repo.update_page(db, page.id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Page not found")
    return result.to_dict()


@router.delete(
    "/custom-pages/{page_id}",
    dependencies=[Depends(require_permission("settings", "manage"))],
)
async def delete_page(
    page_id: str,
    db: AsyncSession = Depends(get_db),
    service: DiyService = Depends(get_diy_service),
):
    """删除自定义页面（系统页不可删除）。"""
    try:
        pid = UUID(page_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid page ID")
    page = await service.repo.get_page_by_id(db, pid)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    if page.page_type != "custom":
        raise HTTPException(status_code=400, detail="Cannot delete system pages")
    await service.repo.delete_page(db, pid)
    return {"ok": True}


# ------------------------------------------------------------------
# 发布 / 撤销
# ------------------------------------------------------------------


@router.post(
    "/pages/{key}/publish",
    dependencies=[Depends(require_permission("settings", "manage"))],
)
async def publish_page(
    key: str,
    db: AsyncSession = Depends(get_db),
    service: DiyService = Depends(get_diy_service),
):
    """发布页面（系统页 / 自定义页 均可）。"""
    page = await _resolve_page(service, db, key)
    result = await service.publish_page(db, page.id)
    return {"status": result.status if result else "error"}


@router.post(
    "/pages/{key}/unpublish",
    dependencies=[Depends(require_permission("settings", "manage"))],
)
async def unpublish_page(
    key: str,
    db: AsyncSession = Depends(get_db),
    service: DiyService = Depends(get_diy_service),
):
    """撤销发布。"""
    page = await _resolve_page(service, db, key)
    result = await service.unpublish_page(db, page.id)
    return {"status": result.status if result else "error"}


# ------------------------------------------------------------------
# 复制
# ------------------------------------------------------------------


@router.post(
    "/custom-pages/{page_id}/duplicate",
    dependencies=[Depends(require_permission("settings", "manage"))],
)
async def duplicate_page(
    page_id: str,
    db: AsyncSession = Depends(get_db),
    service: DiyService = Depends(get_diy_service),
):
    """复制页面（含组件）。"""
    try:
        pid = UUID(page_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid page ID")
    result = await service.duplicate_page(db, pid)
    if not result:
        raise HTTPException(status_code=404, detail="Page not found")
    return result.to_dict()


# ------------------------------------------------------------------
# 组件
# ------------------------------------------------------------------


@router.put(
    "/pages/{key}/components",
    dependencies=[Depends(require_permission("settings", "manage"))],
)
async def save_components(
    key: str,
    data: list[dict],
    db: AsyncSession = Depends(get_db),
    service: DiyService = Depends(get_diy_service),
):
    """整页保存组件列表（先删后插）。"""
    page = await _resolve_page(service, db, key)
    items = [
        SimpleNamespace(
            component_id=item.get("component_id"),
            sort_order=item.get("sort_order", idx),
            config=item.get("config") or {},
            is_visible=item.get("is_visible", True),
        )
        for idx, item in enumerate(data)
    ]
    count = await service.repo.save_components(db, page.id, items)
    return {"count": count}


@router.get(
    "/components",
    dependencies=[Depends(require_permission("settings", "manage"))],
)
async def list_components(
    db: AsyncSession = Depends(get_db),
    service: DiyService = Depends(get_diy_service),
):
    """获取可用组件库列表。"""
    comps = await service.repo.get_components(db)
    return [c.to_dict() for c in comps]


# ------------------------------------------------------------------
# 图片上传
# ------------------------------------------------------------------


@router.post(
    "/upload-image",
    dependencies=[Depends(require_permission("settings", "manage"))],
)
async def upload_image(
    file: UploadFile = File(...),
):
    """上传 DIY 编辑器图片。"""
    import os
    from pathlib import Path

    upload_dir = Path("uploads/diy")
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_ext = os.path.splitext(file.filename or "image.png")[1]
    file_name = f"{uuid4().hex}{file_ext}"
    file_path = upload_dir / file_name
    content = await file.read()
    file_path.write_bytes(content)
    return {"url": f"/uploads/diy/{file_name}"}


# ------------------------------------------------------------------
# 模板
# ------------------------------------------------------------------


@router.get(
    "/templates",
    dependencies=[Depends(require_permission("settings", "manage"))],
)
async def list_templates(
    industry_tag: str | None = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    service: DiyService = Depends(get_diy_service),
):
    """模板市场列表。"""
    return await service.repo.list_templates(
        db, industry_tag=industry_tag, page=page, page_size=page_size
    )


@router.post(
    "/templates",
    dependencies=[Depends(require_permission("settings", "manage"))],
    status_code=201,
)
async def save_as_template(
    data: dict,
    db: AsyncSession = Depends(get_db),
    service: DiyService = Depends(get_diy_service),
):
    """当前站点保存为模板。"""
    result = await service.save_as_template(
        db,
        name=data["name"],
        industry_tag=data.get("industry_tag"),
        template_description=data.get("template_description"),
        template_thumbnail=data.get("template_thumbnail"),
    )
    return result.to_dict()


@router.post(
    "/templates/{template_id}/apply",
    dependencies=[Depends(require_permission("settings", "manage"))],
)
async def apply_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    service: DiyService = Depends(get_diy_service),
):
    """应用模板到当前站点。"""
    try:
        tid = UUID(template_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid template ID")
    ok = await service.apply_template(db, tid)
    if not ok:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"ok": True}
