"""Admin - 资源管理 API（全站唯一上传入口，第一版）。

覆盖：上传 / 列表 / 详情（含引用位置）/ 重命名 / 单个软删 / 批量软删。
原则：
- 文件统一上传 MinIO 并登记 resource 表（软删，不物理删 MinIO 对象）
- 站点隔离：默认写入/读取 active profile 的 site_id；super_admin 可传 site_id 查看全部
- 有 resource_ref 引用的资源禁止删除
"""
from __future__ import annotations

import hashlib
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from forge.infrastructure.persistence.models import (
    ORMAdminUser,
    ORMResource,
    ORMResourceRef,
    ORMSiteProfile,
)
from forge.infrastructure.persistence.repositories.site_profile_repo import SQLAlchemySiteProfileRepository
from forge.infrastructure.services.minio_service import MinioService, get_minio_service
from forge.main.dependencies import get_current_admin, get_db

logger = logging.getLogger(__name__)
router = APIRouter()

# ---------------------------------------------------------------------------
# 文件类型白名单与大小限制
# ---------------------------------------------------------------------------
ALLOWED_EXT = {
    "image": {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".ico"},
    "video": {".mp4", ".webm", ".mov", ".mkv", ".avi"},
    "audio": {".mp3", ".wav", ".ogg", ".flac", ".m4a"},
    "document": {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
                 ".csv", ".txt", ".zip", ".json", ".md"},
}
SIZE_LIMIT = {"image": 10 * 1024 * 1024, "other": 50 * 1024 * 1024}


def _detect_file_type(ext: str, mime: str) -> str:
    if ext in ALLOWED_EXT["image"]:
        return "image"
    if ext in ALLOWED_EXT["video"]:
        return "video"
    if ext in ALLOWED_EXT["audio"]:
        return "audio"
    if ext in ALLOWED_EXT["document"]:
        return "document"
    # 按 mime 兜底
    if mime.startswith("image/"):
        return "image"
    if mime.startswith("video/"):
        return "video"
    if mime.startswith("audio/"):
        return "audio"
    raise HTTPException(status_code=400, detail=f"不支持的文件类型: {ext or mime}")


async def _resolve_upload_site_id(db: AsyncSession, admin: dict, requested: Optional[str]) -> str:
    """上传归属站点：优先用户显式指定；否则使用 active profile（super_admin 也写默认站点）。"""
    if requested:
        return requested
    profile = await SQLAlchemySiteProfileRepository.get_active(db)
    if profile is None:
        raise HTTPException(status_code=500, detail="未找到 active 站点配置")
    return str(profile.id)


def _serialize(res: ORMResource) -> dict:
    return {
        "id": str(res.id),
        "site_id": str(res.site_id) if res.site_id else None,
        "bucket": res.bucket,
        "object_key": res.object_key,
        "url": res.url,
        "file_type": res.file_type,
        "mime": res.mime,
        "file_size": res.file_size,
        "sha256": res.sha256,
        "name": res.name,
        "created_by": str(res.created_by) if res.created_by else None,
        "created_at": res.created_at.isoformat() if res.created_at else None,
        "deleted_at": res.deleted_at.isoformat() if res.deleted_at else None,
    }


# ---------------------------------------------------------------------------
# 上传
# ---------------------------------------------------------------------------
@router.post("/upload")
async def upload_resource(
    file: UploadFile = File(...),
    admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    minio: MinioService = Depends(get_minio_service),
):
    """上传资源：写入 MinIO + 登记 resource 表。"""
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")

    content = await file.read()
    filename = (file.filename or "file").strip()
    ext = ("." + filename.rsplit(".", 1)[-1]).lower() if "." in filename else ""
    mime = file.content_type or "application/octet-stream"

    file_type = _detect_file_type(ext, mime)
    limit = SIZE_LIMIT["image"] if file_type == "image" else SIZE_LIMIT["other"]
    if len(content) > limit:
        raise HTTPException(status_code=400,
                            detail=f"文件大小超出限制（{limit // (1024 * 1024)}MB）")

    site_id = await _resolve_upload_site_id(db, admin, None)
    site_id_uuid = uuid.UUID(site_id)

    # 命名：site/{site_id}/resources/{uuid}.{ext}
    res_uuid = uuid.uuid4()
    prefix = f"site/{site_id}/resources"
    url = minio.upload_bytes(content, f"{res_uuid}{ext}", prefix=prefix, content_type=mime)

    # 从返回 URL 反推 bucket / object_key（MinIO: /minio/{bucket}/{key}，本地: /uploads/site/{key}）
    bucket = getattr(minio, "_bucket", "") or ""
    object_key = ""
    if url.startswith("/minio/"):
        parts = url.split("/", 3)
        if len(parts) == 4:
            bucket = parts[2]
            object_key = parts[3]
    elif url.startswith("/uploads/site/"):
        object_key = url[len("/uploads/site/"):]

    # created_by：admin["sub"] 是 email，需查 admin_users 表取 UUID
    created_by = None
    if admin.get("sub"):
        au = (await db.execute(
            select(ORMAdminUser).where(ORMAdminUser.email == admin["sub"])
        )).scalar_one_or_none()
        if au is not None:
            created_by = au.id

    res = ORMResource(
        site_id=site_id_uuid,
        bucket=bucket,
        object_key=object_key,
        url=url,
        file_type=file_type,
        mime=mime,
        file_size=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        name=filename,
        created_by=created_by,
    )
    db.add(res)
    await db.commit()
    await db.refresh(res)
    return {"data": _serialize(res)}


# ---------------------------------------------------------------------------
# 列表
# ---------------------------------------------------------------------------
class ResourceListResponse(BaseModel):
    items: list[dict]
    total: int


@router.get("", response_model=ResourceListResponse)
async def list_resources(
    file_type: Optional[str] = Query(default=None, alias="type"),
    site_id: Optional[str] = Query(default=None),
    keyword: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """资源列表：支持 type / site_id / keyword / page 过滤，默认上传时间倒序（不含软删）。"""
    query = select(ORMResource).where(ORMResource.deleted_at.is_(None))

    resolved_site = await _resolve_site_id(db, admin, site_id)
    if resolved_site != "all":
        query = query.where(ORMResource.site_id == uuid.UUID(resolved_site))

    if file_type:
        query = query.where(ORMResource.file_type == file_type)
    if keyword:
        like = f"%{keyword}%"
        query = query.where(or_(
            ORMResource.name.ilike(like),
            ORMResource.url.ilike(like),
        ))

    total_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(total_query)).scalar_one()

    query = query.order_by(ORMResource.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return {"items": [_serialize(r) for r in items], "total": total}


# ---------------------------------------------------------------------------
# 详情（含引用位置）
# ---------------------------------------------------------------------------
@router.get("/{resource_id}")
async def get_resource(
    resource_id: str,
    admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        rid = uuid.UUID(resource_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的资源 ID")

    res = (await db.execute(
        select(ORMResource).where(ORMResource.id == rid)
    )).scalar_one_or_none()
    if res is None:
        raise HTTPException(status_code=404, detail="资源不存在")

    refs = (await db.execute(
        select(ORMResourceRef).where(ORMResourceRef.resource_id == rid)
    )).scalars().all()

    data = _serialize(res)
    data["refs"] = [
        {
            "ref_type": r.ref_type,
            "ref_id": r.ref_id,
            "ref_label": r.ref_label,
        }
        for r in refs
    ]
    return {"data": data}


# ---------------------------------------------------------------------------
# 重命名
# ---------------------------------------------------------------------------
class RenamePayload(BaseModel):
    name: str


@router.patch("/{resource_id}")
async def rename_resource(
    resource_id: str,
    payload: RenamePayload,
    admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="名称不能为空")
    if len(name) > 255:
        raise HTTPException(status_code=400, detail="名称过长")

    try:
        rid = uuid.UUID(resource_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的资源 ID")

    res = (await db.execute(
        select(ORMResource).where(ORMResource.id == rid)
    )).scalar_one_or_none()
    if res is None:
        raise HTTPException(status_code=404, detail="资源不存在")

    res.name = name
    await db.commit()
    await db.refresh(res)
    return {"data": _serialize(res)}


# ---------------------------------------------------------------------------
# 软删（单个 / 批量）
# ---------------------------------------------------------------------------
async def _soft_delete(db: AsyncSession, resource_id: uuid.UUID) -> bool:
    res = (await db.execute(
        select(ORMResource).where(ORMResource.id == resource_id)
    )).scalar_one_or_none()
    if res is None or res.deleted_at is not None:
        return False

    ref_count = (await db.execute(
        select(func.count()).select_from(ORMResourceRef)
        .where(ORMResourceRef.resource_id == resource_id)
    )).scalar_one()
    if ref_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"资源存在 {ref_count} 处引用，禁止删除",
        )

    res.deleted_at = func.now()
    await db.flush()
    return True


class BatchDeletePayload(BaseModel):
    ids: list[str]


@router.delete("/{resource_id}")
async def delete_resource(
    resource_id: str,
    admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")
    if admin.get("role") not in ("super_admin", "admin"):
        raise HTTPException(status_code=403, detail="无删除权限")

    try:
        rid = uuid.UUID(resource_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的资源 ID")

    ok = await _soft_delete(db, rid)
    if not ok:
        raise HTTPException(status_code=404, detail="资源不存在或已删除")
    await db.commit()
    return {"data": {"deleted": 1}}


@router.delete("")
async def batch_delete_resources(
    payload: BatchDeletePayload,
    admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """批量软删。"""
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")
    if admin.get("role") not in ("super_admin", "admin"):
        raise HTTPException(status_code=403, detail="无删除权限")

    deleted = 0
    skipped: list[str] = []
    for raw_id in payload.ids or []:
        try:
            rid = uuid.UUID(raw_id)
        except ValueError:
            skipped.append(raw_id)
            continue
        try:
            if await _soft_delete(db, rid):
                deleted += 1
            else:
                skipped.append(raw_id)
        except HTTPException as exc:
            skipped.append(raw_id)
    await db.commit()
    return {"data": {"deleted": deleted, "skipped": skipped}}
