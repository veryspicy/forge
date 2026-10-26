"""Admin - 资源管理 API（全站唯一上传入口，第一版）。

覆盖：上传 / 列表 / 详情（含引用位置）/ 重命名 / 单个软删 / 批量软删。
原则：
- 文件统一上传 MinIO 并登记 resource 表（软删，不物理删 MinIO 对象）
- 站点隔离：默认写入/读取 active profile 的 site_id；super_admin 可传 site_id 查看全部
- 被引用资源软删前由前端提示引用位置供取舍（软删不影响引用处展示）；
  彻底删除默认拒绝仍被引用的资源，前端展示引用清单后 force 二次确认放行
"""

from __future__ import annotations

import contextlib
import hashlib
import logging
import uuid
from collections.abc import Sequence
from io import BytesIO
from typing import TypedDict, cast

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import delete, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from PIL import Image as PILImage
except ImportError:  # pragma: no cover
    PILImage = None  # type: ignore[assignment]

from forge.infrastructure.persistence.models import (
    ORMAdminUser,
    ORMProduct,
    ORMResource,
    ORMResourceDownloadLog,
    ORMResourceRef,
    ORMResourceTag,
    ORMResourceTagMap,
)
from forge.infrastructure.persistence.repositories.site_profile_repo import SQLAlchemySiteProfileRepository
from forge.infrastructure.services.minio_service import MinioService, get_minio_service
from forge.infrastructure.services.phash_service import compute_phash, phash_distance
from forge.infrastructure.services.steganography_service import extract_payload
from forge.infrastructure.services.watermark_service import apply_watermark
from forge.infrastructure.site_defaults import merge_for_response
from forge.main.dependencies import get_db
from forge.main.rbac import require_permission

logger = logging.getLogger(__name__)
router = APIRouter()

# ---------------------------------------------------------------------------
# 文件类型白名单与大小限制
# ---------------------------------------------------------------------------
ALLOWED_EXT = {
    "image": {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".ico"},
    "video": {".mp4", ".webm", ".mov", ".mkv", ".avi"},
    "audio": {".mp3", ".wav", ".ogg", ".flac", ".m4a"},
    "document": {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".csv", ".txt", ".zip", ".json", ".md"},
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


async def _resolve_upload_site_id(db: AsyncSession, admin: dict[str, object], requested: str | None) -> str:
    """上传归属站点：优先用户显式指定；否则使用 active profile（super_admin 也写默认站点）。"""
    if requested:
        return requested
    profile = await SQLAlchemySiteProfileRepository.get_active(db)
    if profile is None:
        raise HTTPException(status_code=500, detail="未找到 active 站点配置")
    return str(profile.id)


async def _resolve_site_id(db: AsyncSession, admin: dict[str, object], requested: str | None) -> str:
    """解析资源列表/详情的站点作用域：显式指定优先；super_admin 可查看全部；否则 active profile。"""
    if requested:
        return requested
    if admin.get("role") == "super_admin":
        return "all"
    profile = await SQLAlchemySiteProfileRepository.get_active(db)
    if profile is None:
        raise HTTPException(status_code=500, detail="未找到 active 站点配置")
    return str(profile.id)


async def _get_watermark_config(db: AsyncSession) -> dict[str, object] | None:
    """读取 active profile 的水印配置（merge_for_response 保证默认键存在）。未启用或无 Logo 返回 None。"""
    profile = await SQLAlchemySiteProfileRepository.get_active(db)
    if profile is None:
        return None
    merged = merge_for_response(profile.config or {})  # type: ignore[arg-type]
    cfg = merged.get("watermark") or {}
    if not isinstance(cfg, dict) or not cfg.get("enabled") or not cfg.get("logoUrl"):
        return None
    return cfg


def _wm_str(cfg: dict[str, object], key: str, default: str) -> str:
    val = cfg.get(key)
    return str(val) if val is not None else default


def _wm_float(cfg: dict[str, object], key: str, default: float) -> float:
    val = cfg.get(key)
    if val is None:
        return default
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        try:
            return float(val)
        except ValueError:
            return default
    return default


def _serialize(res: ORMResource) -> dict[str, object]:
    from forge.infrastructure.services.url_signer import sign_url

    return {
        "id": str(res.id),
        "site_id": str(res.site_id) if res.site_id else None,
        "bucket": res.bucket,
        "object_key": res.object_key,
        "url": sign_url(str(res.url)),
        "thumb_url": sign_url(_derive_thumb_url(res)),
        "file_type": res.file_type,
        "mime": res.mime,
        "file_size": res.file_size,
        "sha256": res.sha256,
        "phash": res.phash,
        "name": res.name,
        "directory": res.directory or "",
        "created_by": str(res.created_by) if res.created_by else None,
        "created_at": res.created_at.isoformat() if res.created_at else None,
        "deleted_at": res.deleted_at.isoformat() if res.deleted_at else None,
    }


def _derive_thumb_url(res: ORMResource) -> str:
    """推导图片缩略图 URL（约定式：site/{site}/resources/thumbs/{uuid}.jpg）。

    仅 image 类型且非 SVG 时返回；缩略图由上传流程生成，若缺失前端回退原图。
    """
    if res.file_type != "image" or not res.object_key:
        return ""
    if res.object_key.lower().endswith(".svg"):
        return ""
    # 从 object_key 推导缩略图键：resources/{uuid}.{ext} -> resources/thumbs/{uuid}.jpg
    marker = "/resources/"
    idx = res.object_key.rfind(marker)
    if idx < 0:
        return ""
    fname = res.object_key[idx + len(marker) :]
    stem = fname.rsplit(".", 1)[0]
    thumb_key = f"{res.object_key[:idx]}/resources/thumbs/{stem}.jpg"
    if res.url.startswith("/uploads/site/"):
        return f"/uploads/site/{thumb_key}"
    return f"/minio/{res.bucket}/{thumb_key}"


async def _get_tags_map(db: AsyncSession, resource_ids: list[uuid.UUID]) -> dict[str, list[str]]:
    """批量查询资源标签：返回 {resource_id_str: [tag_name, ...]}。"""
    if not resource_ids:
        return {}
    rows = (
        await db.execute(
            select(ORMResourceTagMap.resource_id, ORMResourceTag.name)
            .join(ORMResourceTag, ORMResourceTag.id == ORMResourceTagMap.tag_id)
            .where(ORMResourceTagMap.resource_id.in_(resource_ids))
        )
    ).all()
    result: dict[str, list[str]] = {}
    for rid, tag_name in rows:
        result.setdefault(str(rid), []).append(tag_name)
    return result


async def _attach_tags(db: AsyncSession, item: dict[str, object]) -> dict[str, object]:
    """为单个序列化结果附加 tags 列表。"""
    tags_map = await _get_tags_map(db, [uuid.UUID(item["id"])])  # type: ignore[arg-type]
    item["tags"] = tags_map.get(item["id"], [])  # type: ignore[call-overload]
    return item


async def _save_tags(db: AsyncSession, resource_id: uuid.UUID, tags: list[str]) -> None:
    """创建/复用标签并建立资源关联（幂等）。"""
    names = []
    for t in tags or []:
        name = (t or "").strip()
        if name and name not in names:
            names.append(name)
    if not names:
        return
    for name in names:
        tag = (await db.execute(select(ORMResourceTag).where(ORMResourceTag.name == name))).scalar_one_or_none()
        if tag is None:
            tag = ORMResourceTag(name=name)
            db.add(tag)
            await db.flush()
        exists = (
            await db.execute(
                select(ORMResourceTagMap).where(
                    ORMResourceTagMap.resource_id == resource_id,
                    ORMResourceTagMap.tag_id == tag.id,
                )
            )
        ).scalar_one_or_none()
        if exists is None:
            db.add(ORMResourceTagMap(resource_id=resource_id, tag_id=tag.id))


# ---------------------------------------------------------------------------
# 上传
# ---------------------------------------------------------------------------
@router.post("/upload")
async def upload_resource(
    file: UploadFile = File(...),
    directory: str = Form(default=""),
    tags: list[str] = Form(default=[]),
    admin: dict[str, object] = Depends(require_permission("resources", "upload")),
    db: AsyncSession = Depends(get_db),
    minio: MinioService = Depends(get_minio_service),
) -> dict[str, object]:
    """上传资源：写入 MinIO + 登记 resource 表（可选目录与标签）。"""
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")

    content = await file.read()
    filename = (file.filename or "file").strip()
    ext = ("." + filename.rsplit(".", 1)[-1]).lower() if "." in filename else ""
    mime = file.content_type or "application/octet-stream"

    file_type = _detect_file_type(ext, mime)
    limit = SIZE_LIMIT["image"] if file_type == "image" else SIZE_LIMIT["other"]
    if len(content) > limit:
        raise HTTPException(status_code=400, detail=f"文件大小超出限制（{limit // (1024 * 1024)}MB）")

    site_id = await _resolve_upload_site_id(db, admin, None)
    site_id_uuid = uuid.UUID(site_id)

    # 命名：site/{site_id}/resources/{uuid}.{ext}
    res_uuid = uuid.uuid4()
    prefix = f"site/{site_id}/resources"
    # sha256 基于上传原文件计算（溯源取证用，不被水印污染）
    content_sha256 = hashlib.sha256(content).hexdigest()

    # 图片且非 SVG：若站点水印启用且有 Logo，先叠加水印再上传主图
    upload_content = content
    if file_type == "image" and ext.lower() != ".svg":
        wm_cfg = await _get_watermark_config(db)
        if wm_cfg is not None:
            upload_content = apply_watermark(
                content,
                logo_url=_wm_str(wm_cfg, "logoUrl", ""),
                position=_wm_str(wm_cfg, "position", "bottom-right"),
                opacity=_wm_float(wm_cfg, "opacity", 0.35),
                max_area_ratio=_wm_float(wm_cfg, "maxAreaRatio", 0.05),
                minio=minio,
            )

    # pHash 感知哈希基于实际落库内容计算（水印后），保证指纹与对外展示图一致
    content_phash = compute_phash(upload_content) if file_type == "image" else None

    url = minio.upload_bytes(upload_content, f"{res_uuid}{ext}", prefix=prefix, content_type=mime)

    # 从返回 URL 反推 bucket / object_key（MinIO: /minio/{bucket}/{key}，本地: /uploads/site/{key}）
    bucket = getattr(minio, "_bucket", "") or ""
    object_key = ""
    if url.startswith("/minio/"):
        parts = url.split("/", 3)
        if len(parts) == 4:
            bucket = parts[2]
            object_key = parts[3]
    elif url.startswith("/uploads/site/"):
        object_key = url[len("/uploads/site/") :]

    # 图片生成 400px 缩略图（约定键名 resources/thumbs/{uuid}.jpg），失败不阻塞上传
    # 缩略图基于水印后的主图生成，保证角标一致性
    if file_type == "image" and ext.lower() != ".svg" and PILImage is not None:
        try:
            src_img = PILImage.open(BytesIO(upload_content))
            src_img.thumbnail((400, 400))
            # 统一输出 JPEG：RGBA/LA/P 先合成白底，避免缩略图键名与推导不一致
            if src_img.mode in ("RGBA", "LA", "P"):
                rgba = src_img.convert("RGBA")
                bg = PILImage.new("RGB", rgba.size, (255, 255, 255))
                bg.paste(rgba, mask=rgba.split()[-1])
                img = bg
            else:
                img = src_img.convert("RGB")
            thumb_buf = BytesIO()
            img.save(thumb_buf, format="JPEG", quality=82)
            # 缩略图键名必须与 _derive_thumb_url 推导一致（object_key 目录 + thumbs/stem）
            # 旧实现用 res_uuid（带连字符）命名，与 upload_bytes 内部生成的无连字符 stem 不一致，导致 404
            if object_key:
                key_dir, key_file = object_key.rsplit("/", 1)
                key_stem = key_file.rsplit(".", 1)[0]
            else:
                key_dir = f"site/{site_id}/resources"
                key_stem = str(res_uuid)
            thumb_key = f"{key_dir}/thumbs/{key_stem}.jpg"
            minio.upload_object(thumb_buf.getvalue(), thumb_key, content_type="image/jpeg")
        except Exception as exc:  # noqa: BLE001 — 缩略图失败不阻塞上传
            logger.warning("thumbnail generation failed: %s", exc)

    # created_by：admin["sub"] 是 email，需查 admin_users 表取 UUID
    created_by = None
    if admin.get("sub"):
        au = (await db.execute(select(ORMAdminUser).where(ORMAdminUser.email == admin["sub"]))).scalar_one_or_none()
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
        sha256=content_sha256,
        phash=content_phash,
        name=filename,
        directory=(directory or "").strip(),
        created_by=created_by,
    )
    db.add(res)
    await db.flush()

    if tags:
        await _save_tags(db, res.id, tags)  # type: ignore[arg-type]

    await db.commit()
    await db.refresh(res)
    data = await _attach_tags(db, _serialize(res))
    return {"data": data}


# ---------------------------------------------------------------------------
# 外部资源登记
# ---------------------------------------------------------------------------
class RegisterExternalRequest(BaseModel):
    name: str = ""
    url: str
    file_type: str | None = None
    directory: str = ""
    tags: list[str] = []


@router.post("/register-external")
async def register_external_resource(
    body: RegisterExternalRequest,
    admin: dict[str, object] = Depends(require_permission("resources", "upload")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    """登记外部 URL 为资源（不写入 MinIO）：支持图片/视频/文档等，前端粘贴外链时落库以便 syncRefs 追踪。"""
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")

    url = (body.url or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL 不能为空")
    if not (url.startswith("http://") or url.startswith("https://")):
        raise HTTPException(status_code=400, detail="仅支持 http/https 外部 URL")

    # 未显式指定 file_type 时按扩展名推导
    file_type = (body.file_type or "").strip() or "document"
    if file_type == "document":
        path = url.split("?", 1)[0].split("#", 1)[0]
        ext = ("." + path.rsplit(".", 1)[-1]).lower() if "." in path.rsplit("/", 1)[-1] else ""
        if ext in ALLOWED_EXT["image"]:
            file_type = "image"
        elif ext in ALLOWED_EXT["video"]:
            file_type = "video"
        elif ext in ALLOWED_EXT["audio"]:
            file_type = "audio"

    site_id = await _resolve_upload_site_id(db, admin, None)
    site_id_uuid = uuid.UUID(site_id)

    # 幂等：同站点同 URL 已存在（未删除）时复用既有记录，避免重复登记
    existing = (
        await db.execute(
            select(ORMResource).where(
                ORMResource.site_id == site_id_uuid,
                ORMResource.url == url,
                ORMResource.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        data = await _attach_tags(db, _serialize(existing))
        return {"data": data}

    # created_by：admin["sub"] 是 email，需查 admin_users 表取 UUID
    created_by = None
    if admin.get("sub"):
        au = (await db.execute(select(ORMAdminUser).where(ORMAdminUser.email == admin["sub"]))).scalar_one_or_none()
        if au is not None:
            created_by = au.id

    res = ORMResource(
        site_id=site_id_uuid,
        bucket="",
        object_key="",
        url=url,
        file_type=file_type,
        mime="",
        file_size=0,
        sha256=None,
        name=(body.name or url).strip(),
        directory=(body.directory or "").strip(),
        created_by=created_by,
    )
    db.add(res)
    await db.flush()

    if body.tags:
        await _save_tags(db, res.id, body.tags)  # type: ignore[arg-type]

    await db.commit()
    await db.refresh(res)
    data = await _attach_tags(db, _serialize(res))
    return {"data": data}


# ---------------------------------------------------------------------------
# 列表
# ---------------------------------------------------------------------------
class ResourceListResponse(BaseModel):
    items: list[dict[str, object]]
    total: int


@router.get("", response_model=ResourceListResponse)
async def list_resources(
    file_type: str | None = Query(default=None, alias="type"),
    site_id: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    directory: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    admin: dict[str, object] = Depends(require_permission("resources", "view")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    """资源列表：支持 type / site_id / keyword / directory / tag / page 过滤，默认上传时间倒序（不含软删）。"""
    query = select(ORMResource).where(ORMResource.deleted_at.is_(None))

    resolved_site = await _resolve_site_id(db, admin, site_id)
    if resolved_site != "all":
        query = query.where(ORMResource.site_id == uuid.UUID(resolved_site))

    if file_type:
        query = query.where(ORMResource.file_type == file_type)
    if keyword:
        like = f"%{keyword}%"
        query = query.where(
            or_(
                ORMResource.name.ilike(like),
                ORMResource.url.ilike(like),
            )
        )
    if directory is not None:
        # 精确目录；空串表示"未归档"（根目录）
        query = query.where(ORMResource.directory == directory)
    if tag:
        query = query.where(
            ORMResource.id.in_(
                select(ORMResourceTagMap.resource_id)
                .join(ORMResourceTag, ORMResourceTag.id == ORMResourceTagMap.tag_id)
                .where(ORMResourceTag.name == tag)
            )
        )

    total_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(total_query)).scalar_one()

    query = query.order_by(ORMResource.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    # 引用计数 + 标签：仅统计当前页资源，供前端橙色标识与批量删除拦截
    ids = [r.id for r in items]
    ref_counts: dict[str, int] = {}
    if ids:
        rows = (
            await db.execute(
                select(ORMResourceRef.resource_id, func.count())
                .where(ORMResourceRef.resource_id.in_(ids))
                .group_by(ORMResourceRef.resource_id)
            )
        ).all()
        ref_counts = {str(rid): cnt for rid, cnt in rows}
    tags_map = await _get_tags_map(db, ids)  # type: ignore[arg-type]

    data = []
    for r in items:
        item = _serialize(r)
        item["ref_count"] = ref_counts.get(str(r.id), 0)
        item["tags"] = tags_map.get(str(r.id), [])
        data.append(item)

    return {"items": data, "total": total}


# ---------------------------------------------------------------------------
# 目录树 / 标签列表（供左侧筛选）
# ---------------------------------------------------------------------------
@router.get("/meta/directories")
async def list_directories(
    admin: dict[str, object] = Depends(require_permission("resources", "view")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    """目录树：按 directory 分组统计资源数（不含软删），未归档资源归入 ''。"""
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")

    rows = (
        await db.execute(
            select(ORMResource.directory, func.count())
            .where(ORMResource.deleted_at.is_(None))
            .group_by(ORMResource.directory)
            .order_by(ORMResource.directory)
        )
    ).all()
    return {"data": [{"directory": d or "", "count": c} for d, c in rows]}


@router.get("/meta/tags")
async def list_tags(
    admin: dict[str, object] = Depends(require_permission("resources", "view")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    """标签列表：按标签统计资源数（不含软删）。"""
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")

    rows = (
        await db.execute(
            select(ORMResourceTag.name, func.count(ORMResourceTagMap.id))
            .join(ORMResourceTagMap, ORMResourceTagMap.tag_id == ORMResourceTag.id)
            .join(ORMResource, ORMResource.id == ORMResourceTagMap.resource_id)
            .where(ORMResource.deleted_at.is_(None))
            .group_by(ORMResourceTag.name)
            .order_by(ORMResourceTag.name)
        )
    ).all()
    return {"data": [{"name": name, "count": c} for name, c in rows]}


@router.get("/check-name")
async def check_resource_name(
    name: str = Query(...),
    exclude_id: str | None = Query(default=None),
    admin: dict[str, object] = Depends(require_permission("resources", "view")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    """重名检测：同名资源（含软删）返回是否存在及数量。"""
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")

    query = select(ORMResource).where(ORMResource.name == name.strip())
    if exclude_id:
        with contextlib.suppress(ValueError):
            query = query.where(ORMResource.id != uuid.UUID(exclude_id))
    rows = (await db.execute(query)).scalars().all()
    active = [r for r in rows if r.deleted_at is None]
    return {
        "data": {
            "exists": len(active) > 0,
            "active_count": len(active),
            "trash_count": len(rows) - len(active),
        }
    }


class CheckNamesPayload(BaseModel):
    names: list[str]


@router.post("/check-names")
async def check_resource_names(
    payload: CheckNamesPayload,
    admin: dict[str, object] = Depends(require_permission("resources", "view")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    """批量重名检测：返回已存在的同名资源（仅 active，排除软删）。"""
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")
    names = [(n or "").strip() for n in payload.names or []]
    names = list(dict.fromkeys(n for n in names if n))
    if not names:
        return {"data": {"existing": {}}}

    rows = (
        (
            await db.execute(
                select(ORMResource).where(
                    ORMResource.name.in_(names),
                    ORMResource.deleted_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )
    existing: dict[str, int] = {}
    for r in rows:
        existing.setdefault(r.name, 0)  # type: ignore[arg-type]
        existing[r.name] += 1  # type: ignore[index]
    return {"data": {"existing": existing}}


# ---------------------------------------------------------------------------
# 回收站
# ---------------------------------------------------------------------------
class TrashPayload(BaseModel):
    ids: list[str] = []
    force: bool = False


class TrashListResponse(BaseModel):
    items: list[dict[str, object]]
    total: int


@router.get("/trash", response_model=TrashListResponse)
async def list_trash(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=24, ge=1, le=200),
    keyword: str | None = Query(default=None),
    file_type: str | None = Query(default=None),
    admin: dict[str, object] = Depends(require_permission("resources", "view")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    """回收站列表：仅软删资源（deleted_at 非空）。"""
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")

    query = select(ORMResource).where(ORMResource.deleted_at.isnot(None))
    if keyword and keyword.strip():
        query = query.where(ORMResource.name.ilike(f"%{keyword.strip()}%"))
    if file_type and file_type.strip():
        query = query.where(ORMResource.file_type == file_type.strip())

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
    rows = (
        (
            await db.execute(
                query.order_by(ORMResource.deleted_at.desc()).offset((page - 1) * page_size).limit(page_size)
            )
        )
        .scalars()
        .all()
    )
    # 附带引用摘要，供彻底删除前展示引用位置
    ref_map: dict[str, list[dict[str, str]]] = {}
    if rows:
        ref_rows = (
            (await db.execute(select(ORMResourceRef).where(ORMResourceRef.resource_id.in_([r.id for r in rows]))))
            .scalars()
            .all()
        )
        for rr in ref_rows:
            ref_map.setdefault(str(rr.resource_id), []).append(
                {"ref_type": str(rr.ref_type), "ref_id": str(rr.ref_id), "ref_label": str(rr.ref_label)}
            )
    items: list[dict[str, object]] = []
    for r in rows:
        item = _serialize(r)
        refs = ref_map.get(str(r.id), [])
        item["ref_count"] = len(refs)
        item["refs"] = refs
        items.append(item)
    return {"items": items, "total": total}


@router.post("/trash/restore")
async def restore_resources(
    payload: TrashPayload,
    admin: dict[str, object] = Depends(require_permission("resources", "manage")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    """恢复回收站资源（单/批量）：清除 deleted_at。"""
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")
    if admin.get("role") not in ("super_admin", "admin"):
        raise HTTPException(status_code=403, detail="无恢复权限")

    restored = 0
    skipped: list[str] = []
    for raw_id in payload.ids or []:
        try:
            rid = uuid.UUID(raw_id)
        except ValueError:
            skipped.append(raw_id)
            continue
        res = (
            await db.execute(
                select(ORMResource).where(
                    ORMResource.id == rid,
                    ORMResource.deleted_at.isnot(None),
                )
            )
        ).scalar_one_or_none()
        if res is None:
            skipped.append(raw_id)
            continue
        res.deleted_at = None  # type: ignore[assignment]
        restored += 1
    await db.commit()
    return {"data": {"restored": restored, "skipped": skipped}}


@router.delete("/trash")
async def purge_resources(
    payload: TrashPayload,
    admin: dict[str, object] = Depends(require_permission("resources", "manage")),
    db: AsyncSession = Depends(get_db),
    minio: MinioService = Depends(get_minio_service),
) -> dict[str, object]:
    """彻底删除回收站资源（单/批量）：物理删 MinIO 对象（含缩略图）+ 删 DB 行 + 清关联。

    高风险操作：前端必须二次确认后调用。
    引用门禁：默认（force=false）仍被引用的资源拒绝彻底删除并返回引用清单，
    由前端展示引用位置；用户确认可接受裂图后携带 force=true 重调放行。
    """
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")
    if admin.get("role") not in ("super_admin", "admin"):
        raise HTTPException(status_code=403, detail="无彻底删除权限")

    purged = 0
    skipped: list[str] = []
    referenced: list[dict[str, object]] = []
    for raw_id in payload.ids or []:
        try:
            rid = uuid.UUID(raw_id)
        except ValueError:
            skipped.append(raw_id)
            continue
        res = (
            await db.execute(
                select(ORMResource).where(
                    ORMResource.id == rid,
                    ORMResource.deleted_at.isnot(None),
                )
            )
        ).scalar_one_or_none()
        if res is None:
            skipped.append(raw_id)
            continue

        # 引用门禁：软删后被引用仍可能残留（用户未解除引用即软删）
        refs = await _load_refs(db, rid)
        if refs and not payload.force:
            referenced.append(
                {
                    "resource_id": str(rid),
                    "name": res.name,
                    "ref_count": len(refs),
                    "refs": _serialize_refs(refs),
                }
            )
            continue

        # 物理删除 MinIO 对象与缩略图
        if res.object_key:
            minio.remove_object(res.object_key)  # type: ignore[arg-type]
        thumb_key = _thumb_object_key(res)
        if thumb_key:
            minio.remove_object(thumb_key)
        # 清关联表（引用、标签）
        await db.execute(delete(ORMResourceRef).where(ORMResourceRef.resource_id == rid))
        await db.execute(delete(ORMResourceTagMap).where(ORMResourceTagMap.resource_id == rid))
        await db.delete(res)
        purged += 1
    await db.commit()
    return {"data": {"purged": purged, "skipped": skipped, "referenced": referenced}}


@router.delete("/trash/empty")
async def empty_trash(
    admin: dict[str, object] = Depends(require_permission("resources", "manage")),
    db: AsyncSession = Depends(get_db),
    minio: MinioService = Depends(get_minio_service),
    payload: TrashPayload | None = None,
) -> dict[str, object]:
    """清空回收站：彻底删除所有软删资源。高风险操作，前端必须二次确认后调用。

    引用门禁：默认（force=false）若回收站仍含被引用资源，不执行清空并返回引用清单；
    前端展示清单并确认可接受裂图后，携带 force=true 再次调用放行。
    """
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")
    if admin.get("role") not in ("super_admin", "admin"):
        raise HTTPException(status_code=403, detail="无彻底删除权限")

    force = bool(payload.force) if payload is not None else False
    rows = (await db.execute(select(ORMResource).where(ORMResource.deleted_at.isnot(None)))).scalars().all()
    referenced: list[dict[str, object]] = []
    if not force:
        for res in rows:
            refs = await _load_refs(db, cast(uuid.UUID, res.id))
            if refs:
                referenced.append(
                    {
                        "resource_id": str(res.id),
                        "name": res.name,
                        "ref_count": len(refs),
                        "refs": _serialize_refs(refs),
                    }
                )
        if referenced:
            return {"data": {"purged": 0, "referenced": referenced, "blocked": True}}

    purged = 0
    for res in rows:
        if res.object_key:
            minio.remove_object(res.object_key)  # type: ignore[arg-type]
        thumb_key = _thumb_object_key(res)
        if thumb_key:
            minio.remove_object(thumb_key)
        await db.execute(delete(ORMResourceRef).where(ORMResourceRef.resource_id == res.id))
        await db.execute(delete(ORMResourceTagMap).where(ORMResourceTagMap.resource_id == res.id))
        await db.delete(res)
        purged += 1
    await db.commit()
    return {"data": {"purged": purged, "referenced": [], "blocked": False}}


def _thumb_object_key(res: ORMResource) -> str:
    """根据原 object_key 推导缩略图键名（与 _derive_thumb_url 一致）。"""
    if res.file_type != "image" or not res.object_key:
        return ""
    if res.object_key.lower().endswith(".svg"):
        return ""
    marker = "/resources/"
    idx = res.object_key.rfind(marker)
    if idx < 0:
        return ""
    fname = res.object_key[idx + len(marker) :]
    stem = fname.rsplit(".", 1)[0]
    return f"{res.object_key[:idx]}/resources/thumbs/{stem}.jpg"


# ---------------------------------------------------------------------------
# 相似图片检索（pHash 指纹，P4 取证入口）
# ---------------------------------------------------------------------------
@router.post("/search-similar")
async def search_similar_resources(
    phash: str = Form(default=""),
    file: UploadFile | None = File(default=None),
    threshold: int = Form(default=10),
    limit: int = Form(default=50),
    admin: dict[str, object] = Depends(require_permission("resources", "view")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    """按感知哈希检索相似图片：供溯源取证（P4）确认某图是否为本站资源衍生。

    入参二选一：phash（64bit hex 指纹）或 file（待查图片，自动计算指纹）。
    返回库中 phash 距离 <= threshold 的图片资源，按距离升序。
    """
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")

    target_phash = (phash or "").strip().lower()
    if file is not None:
        content = await file.read()
        target_phash = compute_phash(content) or ""
    if not target_phash or len(target_phash) != 16:
        raise HTTPException(status_code=400, detail="必须提供有效 phash 或图片文件")

    rows = (
        (
            await db.execute(
                select(ORMResource).where(
                    ORMResource.file_type == "image",
                    ORMResource.phash.is_not(None),
                    ORMResource.deleted_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )

    matches: list[dict[str, object]] = []
    from forge.infrastructure.services.url_signer import sign_url

    for res in rows:
        dist = phash_distance(target_phash, str(res.phash or ""))
        if dist <= threshold:
            matches.append(
                {
                    "id": str(res.id),
                    "url": sign_url(str(res.url)),
                    "thumb_url": sign_url(_derive_thumb_url(res)),
                    "name": res.name,
                    "directory": res.directory or "",
                    "phash": res.phash,
                    "distance": dist,
                }
            )
    matches.sort(key=lambda m: int(str(m["distance"])))
    return {"data": {"total": len(matches), "threshold": threshold, "items": matches[:limit]}}


# ---------------------------------------------------------------------------
# 取证验证（P4）：上传疑似盗图 -> sha256/pHash 比对 + 隐写提取 + 下载日志对账
# ---------------------------------------------------------------------------
@router.post("/forensics/verify")
async def verify_resource_forensics(
    file: UploadFile = File(...),
    threshold: int = Form(default=10),
    admin: dict[str, object] = Depends(require_permission("resources", "view")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    """取证验证入口：上传疑似盗图，生成完整溯源报告。

    报告维度：
    1. 原图级比对：sha256 与库中资源完全一致 => 原图泄露
    2. 衍生图比对：pHash 汉明距离 <= threshold（<=4 高度相似）=> 本站图片衍生
    3. 隐写提取：图片像素中可能携带站点标记（S|）或用户下载标记（U|user|time）
    4. 下载日志对账：隐写指认的用户在库中对应资源的下载记录
    """
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="空文件")
    if len(content) > SIZE_LIMIT["image"]:
        raise HTTPException(status_code=400, detail="图片大小不能超过 10MB")

    target_phash = compute_phash(content)
    target_sha256 = hashlib.sha256(content).hexdigest()

    # 1. 隐写提取
    stego_payload = extract_payload(content)
    stego: dict[str, object] = {
        "found": stego_payload is not None,
        "payload": stego_payload,
    }
    if stego_payload:
        parts = stego_payload.split("|", 2)
        if len(parts) == 3 and parts[0] == "U":
            stego["kind"] = "user_download"
            stego["user_id"] = parts[1]
            stego["downloaded_at"] = parts[2]
        elif len(parts) == 2 and parts[0] == "S":
            stego["kind"] = "site_mark"
            stego["site_tag"] = parts[1]
        else:
            stego["kind"] = "unknown"

    # 2. 全库相似比对（复用 pHash 索引语义）
    rows = (
        (
            await db.execute(
                select(ORMResource).where(
                    ORMResource.file_type == "image",
                    ORMResource.phash.is_not(None),
                    ORMResource.deleted_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )
    matches: list[dict[str, object]] = []
    from forge.infrastructure.services.url_signer import sign_url

    for res in rows:
        dist = phash_distance(target_phash or "", str(res.phash or ""))
        if dist > threshold:
            continue
        exact = bool(target_sha256 and res.sha256 and target_sha256 == res.sha256)
        matches.append(
            {
                "id": str(res.id),
                "url": sign_url(str(res.url)),
                "thumb_url": sign_url(_derive_thumb_url(res)),
                "name": res.name,
                "directory": res.directory or "",
                "phash": res.phash,
                "sha256": res.sha256,
                "distance": dist,
                "match_level": (
                    "原图级（sha256 一致）"
                    if exact
                    else ("高度相似（距离<=4）" if dist <= 4 else "相似（距离<=10）")
                ),
            }
        )
    matches.sort(key=lambda m: int(str(m["distance"])))

    # 3. 下载日志对账：隐写指认用户 或 匹配资源的最新下载记录
    download_logs: list[dict[str, object]] = []
    if matches:
        matched_ids = [uuid.UUID(str(m["id"])) for m in matches]
        log_query = (
            select(ORMResourceDownloadLog)
            .where(ORMResourceDownloadLog.resource_id.in_(matched_ids))
            .order_by(ORMResourceDownloadLog.created_at.desc())
        )
        if stego.get("kind") == "user_download":
            with contextlib.suppress(ValueError):
                log_query = log_query.where(
                    ORMResourceDownloadLog.user_id == uuid.UUID(str(stego["user_id"]))
                )
        logs = (await db.execute(log_query.limit(20))).scalars().all()
        download_logs = [
            {
                "id": str(log.id),
                "resource_id": str(log.resource_id),
                "user_id": str(log.user_id),
                "user_email": log.user_email,
                "ip": log.ip,
                "user_agent": log.user_agent,
                "payload": log.payload,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ]

    return {
        "data": {
            "input": {
                "filename": (file.filename or "").strip(),
                "sha256": target_sha256,
                "phash": target_phash,
            },
            "stego": stego,
            "matches": matches,
            "download_logs": download_logs,
        }
    }


# ---------------------------------------------------------------------------
# 详情（含引用位置）
# ---------------------------------------------------------------------------
@router.get("/{resource_id}")
async def get_resource(
    resource_id: str,
    admin: dict[str, object] = Depends(require_permission("resources", "view")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    try:
        rid = uuid.UUID(resource_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的资源 ID") from None

    res = (await db.execute(select(ORMResource).where(ORMResource.id == rid))).scalar_one_or_none()
    if res is None:
        raise HTTPException(status_code=404, detail="资源不存在")

    refs = (await db.execute(select(ORMResourceRef).where(ORMResourceRef.resource_id == rid))).scalars().all()

    data = await _attach_tags(db, _serialize(res))
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
# 引用登记（全量同步）—— 供商品 / 站点配置等表单保存后对齐引用关系
# ---------------------------------------------------------------------------
class ResourceRefSyncPayload(BaseModel):
    ref_type: str
    ref_id: str
    ref_label: str = ""
    resource_ids: list[str] = []


@router.post("/refs/sync")
async def sync_resource_refs(
    payload: ResourceRefSyncPayload,
    admin: dict[str, object] = Depends(require_permission("resources", "manage")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    """全量同步引用关系：将 ref_type+ref_id 下登记的引用对齐到 resource_ids 列表。

    - 新增：resource_ids 中缺失的引用记录
    - 移除：已登记但不在 resource_ids 中的记录
    - site_config 且 ref_id='active' 时自动解析为 active profile id
    - 引用的资源必须存在且未软删，否则跳过
    """
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")

    ref_type = (payload.ref_type or "").strip()
    ref_id = (payload.ref_id or "").strip()
    if not ref_type or not ref_id:
        raise HTTPException(status_code=400, detail="ref_type 与 ref_id 不能为空")
    if len(ref_type) > 64 or len(ref_id) > 128:
        raise HTTPException(status_code=400, detail="ref_type/ref_id 过长")

    # site_config：ref_id='active' 时解析真实 active profile id
    if ref_type == "site_config" and ref_id == "active":
        profile = await SQLAlchemySiteProfileRepository.get_active(db)
        if profile is None:
            raise HTTPException(status_code=500, detail="未找到 active 站点配置")
        ref_id = str(profile.id)

    # 校验资源 id 集合（存在且未软删）
    valid_ids: set[uuid.UUID] = set()
    for raw_id in dict.fromkeys(payload.resource_ids or []):
        try:
            rid = uuid.UUID(raw_id)
        except ValueError:
            continue
        res = (
            await db.execute(select(ORMResource).where(ORMResource.id == rid, ORMResource.deleted_at.is_(None)))
        ).scalar_one_or_none()
        if res is not None:
            valid_ids.add(rid)

    # 现有引用
    existing = (
        (
            await db.execute(
                select(ORMResourceRef).where(
                    ORMResourceRef.ref_type == ref_type,
                    ORMResourceRef.ref_id == ref_id,
                )
            )
        )
        .scalars()
        .all()
    )
    existing_by_rid = {r.resource_id: r for r in existing}

    ref_label = (payload.ref_label or "").strip()[:255]
    added = 0
    removed = 0
    for rid in valid_ids:
        if rid not in existing_by_rid:
            db.add(
                ORMResourceRef(
                    resource_id=rid,
                    ref_type=ref_type,
                    ref_id=ref_id,
                    ref_label=ref_label,
                )
            )
            added += 1
    for rid, ref in existing_by_rid.items():  # type: ignore[assignment]
        if rid not in valid_ids:
            await db.delete(ref)
            removed += 1

    await db.commit()
    return {"data": {"added": added, "removed": removed, "total": len(valid_ids)}}


# ---------------------------------------------------------------------------
# 清理无效引用 —— 供管理员一键解除指向不存在业务对象的悬空引用
# ---------------------------------------------------------------------------
# ref_type -> 可校验实体表；不在映射中的 ref_type 视为未知类型（无效引用）
_REF_ENTITY_TABLES: dict[str, str] = {
    "product": "products",
    "products": "products",
    "order": "orders",
    "orders": "orders",
    "user": "users",
    "users": "users",
    "supplier": "suppliers",
    "suppliers": "suppliers",
    "shipment": "shipments",
    "shipments": "shipments",
    "site": "site_profiles",
}


class ResourceRefCleanupPayload(BaseModel):
    resource_ids: list[str] = []
    dry_run: bool = False


@router.post("/refs/cleanup")
async def cleanup_invalid_resource_refs(
    payload: ResourceRefCleanupPayload,
    admin: dict[str, object] = Depends(require_permission("resources", "manage")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    """清理无效引用：引用指向的业务对象不存在，或 ref_type 未知（无对应实体表）。

    - resource_ids 为空时扫描全部引用；dry_run=true 仅返回清单不删除
    - products 额外排除 status='deleted'（软删商品视为无效）
    """
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")

    stmt = select(ORMResourceRef)
    if payload.resource_ids:
        rids: list[uuid.UUID] = []
        for raw in payload.resource_ids:
            try:
                rids.append(uuid.UUID(raw))
            except ValueError:
                continue
        if rids:
            stmt = stmt.where(ORMResourceRef.resource_id.in_(rids))
    refs = (await db.execute(stmt)).scalars().all()

    invalid: list[dict[str, object]] = []
    for ref in refs:
        table = _REF_ENTITY_TABLES.get(str(ref.ref_type))
        reason = ""
        if table is None:
            reason = "未知引用类型"
        else:
            exists = (
                await db.execute(
                    text(f"SELECT 1 FROM {table} WHERE id::text = :rid"),
                    {"rid": ref.ref_id},
                )
            ).scalar_one_or_none()
            if table == "products" and exists is not None:
                soft_deleted = (
                    await db.execute(
                        text("SELECT 1 FROM products WHERE id::text = :rid AND status = 'deleted'"),
                        {"rid": ref.ref_id},
                    )
                ).scalar_one_or_none()
                if soft_deleted is not None:
                    exists = None
            if exists is None:
                reason = f"业务对象不存在（{table}）"

        if reason:
            invalid.append(
                {
                    "id": str(ref.id),
                    "resource_id": str(ref.resource_id),
                    "ref_type": ref.ref_type,
                    "ref_id": ref.ref_id,
                    "ref_label": ref.ref_label,
                    "reason": reason,
                }
            )

    cleaned = 0
    if invalid and not payload.dry_run:
        for item in invalid:
            ref_to_delete = (
                await db.execute(select(ORMResourceRef).where(ORMResourceRef.id == uuid.UUID(str(item["id"]))))
            ).scalar_one_or_none()
            if ref_to_delete is not None:
                await db.delete(ref_to_delete)
                cleaned += 1
        await db.commit()

    return {"data": {"checked": len(refs), "invalid": invalid, "cleaned": cleaned, "dry_run": payload.dry_run}}


# ---------------------------------------------------------------------------
# 重命名
# ---------------------------------------------------------------------------
class ResourceUpdatePayload(BaseModel):
    """资源更新：可单独更新 name 或外链 url（外链资源 object_key 为空才允许改 url）。"""

    name: str | None = None
    url: str | None = None


@router.patch("/{resource_id}")
async def update_resource(
    resource_id: str,
    payload: ResourceUpdatePayload,
    admin: dict[str, object] = Depends(require_permission("resources", "manage")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    name = (payload.name or "").strip()
    url = (payload.url or "").strip()
    if not name and not url:
        raise HTTPException(status_code=400, detail="name 或 url 至少提供一个")
    if name and len(name) > 255:
        raise HTTPException(status_code=400, detail="名称过长")

    try:
        rid = uuid.UUID(resource_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的资源 ID") from None

    res = (await db.execute(select(ORMResource).where(ORMResource.id == rid))).scalar_one_or_none()
    if res is None:
        raise HTTPException(status_code=404, detail="资源不存在")

    if name:
        res.name = name  # type: ignore[assignment]

    if url:
        # 仅允许外链资源（未上传 MinIO，object_key 为空）更新 URL；本地上传资源的地址由文件决定
        if res.object_key:
            raise HTTPException(status_code=400, detail="仅外链资源支持更新 URL")
        if not (url.startswith("http://") or url.startswith("https://")):
            raise HTTPException(status_code=400, detail="仅支持 http/https 外部 URL")
        # 幂等冲突：同站点同 URL 已被其他活跃资源占用时拒绝
        conflict = (
            await db.execute(
                select(ORMResource).where(
                    ORMResource.site_id == res.site_id,
                    ORMResource.url == url,
                    ORMResource.deleted_at.is_(None),
                    ORMResource.id != rid,
                )
            )
        ).scalar_one_or_none()
        if conflict is not None:
            raise HTTPException(status_code=409, detail="该 URL 已被其他资源占用")
        res.url = url  # type: ignore[assignment]
        # 商品图片 url 由资源表 join 解析（images 仅存 resource_id 引用），无需同步快照

    await db.commit()
    await db.refresh(res)
    return {"data": _serialize(res)}


# ---------------------------------------------------------------------------
# 商品图片替换（裁剪产物换新资源）：编辑入口已收敛至资源管理页
# ---------------------------------------------------------------------------
@router.post("/{resource_id}/replace-image")
async def replace_product_image(
    resource_id: str,
    file: UploadFile = File(...),
    admin: dict[str, object] = Depends(require_permission("resources", "manage")),
    db: AsyncSession = Depends(get_db),
    minio: MinioService = Depends(get_minio_service),
) -> dict[str, object]:
    """用裁剪/编辑产物替换图片：上传新资源，商品引用切到新资源，旧资源保留（软删前仍可追溯）。

    语义：编辑生成新素材，不破坏共享引用（旧资源可能被其他商品/详情块引用）。
    """
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")

    try:
        rid = uuid.UUID(resource_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的资源 ID") from None

    res = (
        await db.execute(select(ORMResource).where(ORMResource.id == rid, ORMResource.deleted_at.is_(None)))
    ).scalar_one_or_none()
    if res is None:
        raise HTTPException(status_code=404, detail="资源不存在")

    mime = file.content_type or "application/octet-stream"
    filename = (file.filename or "file").strip()
    ext = ("." + filename.rsplit(".", 1)[-1]).lower() if "." in filename else ""
    if _detect_file_type(ext, mime) != "image":
        raise HTTPException(status_code=400, detail="仅支持图片文件")
    content = await file.read()
    if len(content) > SIZE_LIMIT["image"]:
        raise HTTPException(status_code=400, detail="图片大小不能超过 10MB")
    ext_map = {
        ".png": ".png",
        ".jpg": ".jpg",
        ".jpeg": ".jpg",
        ".webp": ".webp",
        ".gif": ".gif",
        ".bmp": ".bmp",
        ".ico": ".ico",
        ".svg": ".svg",
    }
    out_ext = ext_map.get(ext.lower(), ".png" if mime.startswith("image/png") else ".jpg")

    site_id = res.site_id
    image_key = f"site/{site_id}/resources/{rid}/{uuid.uuid4().hex}{out_ext}"
    # 站点水印启用且有 Logo 时叠加水印（替换产物同样受保护）
    upload_content = content
    if out_ext != ".svg":
        wm_cfg = await _get_watermark_config(db)
        if wm_cfg is not None:
            upload_content = apply_watermark(
                content,
                logo_url=_wm_str(wm_cfg, "logoUrl", ""),
                position=_wm_str(wm_cfg, "position", "bottom-right"),
                opacity=_wm_float(wm_cfg, "opacity", 0.35),
                max_area_ratio=_wm_float(wm_cfg, "maxAreaRatio", 0.05),
                minio=minio,
            )
    url = minio.upload_object(upload_content, image_key, content_type=mime)

    bucket = getattr(minio, "_bucket", "") or ""
    # pHash 基于实际落库内容（水印后）计算，与对外展示图一致
    content_phash = compute_phash(upload_content)
    new_resource = ORMResource(
        site_id=site_id,
        bucket=bucket,
        object_key=image_key,
        url=url,
        file_type="image",
        mime=mime,
        file_size=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        phash=content_phash,
        name=f"{res.name or 'image'} (编辑版)".strip(),
        directory=res.directory or f"products/{rid}",
    )
    db.add(new_resource)
    await db.flush()

    # 商品引用切到新资源；旧快照字段（url/key）若存在则同步替换，避免展示断裂
    refs = (
        (
            await db.execute(
                select(ORMResourceRef).where(
                    ORMResourceRef.resource_id == rid,
                    ORMResourceRef.ref_type.in_(["product", "products"]),
                )
            )
        )
        .scalars()
        .all()
    )
    updated_products = 0
    for ref in refs:
        try:
            product = (
                await db.execute(select(ORMProduct).where(ORMProduct.id == uuid.UUID(str(ref.ref_id))))
            ).scalar_one_or_none()
        except ValueError:
            continue
        if product is None:
            continue
        images: list[dict[str, object]] = product.images if isinstance(product.images, list) else []
        changed = False
        for img in images:
            if img.get("resource_id") == str(rid):
                img["resource_id"] = str(new_resource.id)
                if img.get("url") is not None:
                    img["url"] = url
                if img.get("key") is not None:
                    img["key"] = image_key
                changed = True
        if changed:
            product.images = images  # type: ignore[assignment]
            updated_products += 1

    # resource_ref 同步指向新资源（保留引用计数归属），旧资源解除商品引用但保留记录
    for ref in refs:
        ref.resource_id = new_resource.id

    await db.commit()
    await db.refresh(new_resource)
    return {
        "data": _serialize(new_resource),
        "meta": {
            "message": f"替换成功，已更新 {updated_products} 个商品的引用",
            "updated_products": updated_products,
        },
    }


# ---------------------------------------------------------------------------
# 目录 / 标签 批量操作（拖拽移动、批量打标、重名检测）
# ---------------------------------------------------------------------------
class MovePayload(BaseModel):
    ids: list[str]
    directory: str


@router.post("/move")
async def move_resources(
    payload: MovePayload,
    admin: dict[str, object] = Depends(require_permission("resources", "manage")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    """批量移动资源到目录（拖拽移动）。directory 传 '' 表示移到根目录/未归档。"""
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")

    directory = (payload.directory or "").strip().strip("/")
    moved = 0
    for raw_id in payload.ids or []:
        try:
            rid = uuid.UUID(raw_id)
        except ValueError:
            continue
        res = (
            await db.execute(select(ORMResource).where(ORMResource.id == rid, ORMResource.deleted_at.is_(None)))
        ).scalar_one_or_none()
        if res is None:
            continue
        res.directory = directory  # type: ignore[assignment]
        moved += 1
    await db.commit()
    return {"data": {"moved": moved}}


class TagsPayload(BaseModel):
    ids: list[str]
    tags: list[str]


@router.post("/tags")
async def set_resource_tags(
    payload: TagsPayload,
    admin: dict[str, object] = Depends(require_permission("resources", "manage")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    """批量设置资源标签（追加语义，幂等去重）。"""
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")

    for raw_id in payload.ids or []:
        try:
            rid = uuid.UUID(raw_id)
        except ValueError:
            continue
        res = (
            await db.execute(select(ORMResource).where(ORMResource.id == rid, ORMResource.deleted_at.is_(None)))
        ).scalar_one_or_none()
        if res is None:
            continue
        await _save_tags(db, rid, payload.tags)
    await db.commit()
    return {"data": {"updated": len(payload.ids or [])}}


# ---------------------------------------------------------------------------
# 软删（单个 / 批量）
# ---------------------------------------------------------------------------
class SoftDeleteResult(TypedDict):
    ref_count: int
    refs: list[dict[str, str]]


def _serialize_refs(refs: Sequence[ORMResourceRef]) -> list[dict[str, str]]:
    """引用摘要（ref_type / ref_id / ref_label 快照，供前端展示引用位置）。"""
    return [{"ref_type": str(r.ref_type), "ref_id": str(r.ref_id), "ref_label": str(r.ref_label)} for r in refs]


async def _load_refs(db: AsyncSession, resource_id: uuid.UUID) -> Sequence[ORMResourceRef]:
    return (await db.execute(select(ORMResourceRef).where(ORMResourceRef.resource_id == resource_id))).scalars().all()


async def _soft_delete(db: AsyncSession, resource_id: uuid.UUID) -> SoftDeleteResult | None:
    """软删单个资源。

    被引用资源不再硬拦截：软删仅置 deleted_at，MinIO 对象与 URL 仍有效，
    引用处不受影响；删除前由前端展示引用位置供用户取舍。
    返回引用摘要；None 表示资源不存在或已在回收站。
    """
    res = (await db.execute(select(ORMResource).where(ORMResource.id == resource_id))).scalar_one_or_none()
    if res is None or res.deleted_at is not None:
        return None

    refs = await _load_refs(db, resource_id)
    res.deleted_at = func.now()
    await db.flush()
    return {"ref_count": len(refs), "refs": _serialize_refs(refs)}


class BatchDeletePayload(BaseModel):
    ids: list[str]


@router.delete("/{resource_id}")
async def delete_resource(
    resource_id: str,
    admin: dict[str, object] = Depends(require_permission("resources", "manage")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")
    if admin.get("role") not in ("super_admin", "admin"):
        raise HTTPException(status_code=403, detail="无删除权限")

    try:
        rid = uuid.UUID(resource_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的资源 ID") from None

    ok = await _soft_delete(db, rid)
    if ok is None:
        raise HTTPException(status_code=404, detail="资源不存在或已删除")
    await db.commit()
    return {
        "data": {
            "deleted": 1,
            "ref_count": ok["ref_count"],
            "refs": ok["refs"],
        }
    }


@router.delete("")
async def batch_delete_resources(
    payload: BatchDeletePayload,
    admin: dict[str, object] = Depends(require_permission("resources", "manage")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    """批量软删。"""
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")
    if admin.get("role") not in ("super_admin", "admin"):
        raise HTTPException(status_code=403, detail="无删除权限")

    deleted = 0
    skipped: list[str] = []
    referenced_deleted: list[dict[str, object]] = []
    for raw_id in payload.ids or []:
        try:
            rid = uuid.UUID(raw_id)
        except ValueError:
            skipped.append(raw_id)
            continue
        info = await _soft_delete(db, rid)
        if info is None:
            skipped.append(raw_id)
            continue
        deleted += 1
        if info["ref_count"] > 0:
            referenced_deleted.append(
                {
                    "resource_id": str(rid),
                    "ref_count": info["ref_count"],
                    "refs": info["refs"],
                }
            )
    await db.commit()
    return {"data": {"deleted": deleted, "skipped": skipped, "referenced_deleted": referenced_deleted}}
