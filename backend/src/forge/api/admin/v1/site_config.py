"""站点配置 API - 品牌/主题/导航/分类/页脚/i18n/功能开关/轮播图 等全量配置的读写 + 图片上传到 MinIO。

注：站点配置写入数据库的 `site_profiles` 表（读取/更新 active profile），
从而确保 C 端 `/api/v1/site-profile` 与 Admin 编辑端共享同一数据源。

默认配置、别名规范化、深度合并逻辑统一放在
:mod:`forge.infrastructure.site_defaults` 共享模块中维护，避免两端不一致。
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from forge.infrastructure.persistence.models import ORMSiteProfile
from forge.infrastructure.persistence.repositories.site_profile_repo import SQLAlchemySiteProfileRepository
from forge.infrastructure.services.minio_service import MinioService, get_minio_service
from forge.infrastructure.site_defaults import merge_for_response, merge_for_save
from forge.main.dependencies import get_current_admin, get_db

logger = logging.getLogger(__name__)
router = APIRouter()


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

async def _get_active_profile(db: AsyncSession) -> Optional[ORMSiteProfile]:
    return await SQLAlchemySiteProfileRepository.get_active(db)


async def _upsert_active_config(db: AsyncSession, payload_config: dict) -> dict:
    """写入 active profile：存在则合并更新，不存在则新建默认 profile 再合并。"""
    merged_for_save = merge_for_save(payload_config)
    profile = await _get_active_profile(db)
    if profile is None:
        profile = ORMSiteProfile(
            name="default",
            label="默认站点配置",
            is_active=True,
            config=merged_for_save,
        )
        db.add(profile)
    else:
        profile.config = merged_for_save
    profile.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(profile)
    return profile.config or {}


# ----------------------------------------------------------------------
# Pydantic payload
# ----------------------------------------------------------------------

class SiteConfigPayload(BaseModel):
    config: Dict[str, Any]


# ----------------------------------------------------------------------
# Routes
# ----------------------------------------------------------------------

@router.get("/config")
async def get_site_config(
    admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取站点全量配置（若 DB 无 active profile 则返回默认结构）。"""
    profile = await _get_active_profile(db)
    merged = merge_for_response(profile.config if profile else None)
    return {"data": merged}


@router.put("/config")
async def save_site_config(
    payload: SiteConfigPayload,
    admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """保存站点全量配置 —— 写入 active profile 的 config 字段。"""
    try:
        saved = await _upsert_active_config(db, payload.config or {})
        return {"data": merge_for_response(saved)}
    except Exception as exc:  # noqa: BLE001
        logger.exception("保存站点配置失败")
        raise HTTPException(status_code=500, detail=f"保存失败: {exc}")


# ----------------------------------------------------------------------
# 图片上传（MinIO 优先，本地降级）
# ----------------------------------------------------------------------

@router.post("/upload-image")
async def upload_image(
    file: UploadFile = File(...),
    admin: dict = Depends(get_current_admin),
    minio: MinioService = Depends(get_minio_service),
):
    """上传站点图片（Logo / 轮播 / 分类图等）。返回可直接在 C 端渲染的 URL。"""
    content = await file.read()
    filename = file.filename or "image.png"
    url = minio.upload_bytes(content, filename, prefix="site")
    return {"url": url}
