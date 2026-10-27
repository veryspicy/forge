"""C 端资源原图下载接口 —— P4 下载溯源主链路。

语义：登录用户下载原图时，动态嵌入不可见隐写 payload `U|<user_id>|<时间戳>`
并记录下载日志（resource_download_log），供 admin 取证对账。

说明：
- 输出恒为 PNG（LSB 无损保留）；JPEG 原图会转 PNG 后嵌入，体积增大属预期。
- 仅支持已上传到 MinIO 的资源（object_key 非空）；外链资源无原图可下载。
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from forge.api.v1.auth import get_current_user
from forge.infrastructure.persistence.models import ORMResource, ORMResourceDownloadLog, ORMUser
from forge.infrastructure.services.minio_service import MinioService
from forge.infrastructure.services.steganography_service import build_user_payload, embed_payload
from forge.main.dependencies import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/resources", tags=["Resources"])


@router.get("/{resource_id}/download")
async def download_original_resource(
    resource_id: str,
    request: Request,
    user_claims: dict[str, object] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """登录用户下载原图：嵌入用户级隐写 + 写下载日志，返回 PNG。"""
    try:
        rid = UUID(resource_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的资源 ID") from None

    res = (
        await db.execute(select(ORMResource).where(ORMResource.id == rid, ORMResource.deleted_at.is_(None)))
    ).scalar_one_or_none()
    if res is None:
        raise HTTPException(status_code=404, detail="资源不存在")
    if not res.object_key:
        raise HTTPException(status_code=400, detail="外链资源不支持原图下载")

    service: MinioService = MinioService.get()
    if not service.available or service._client is None:  # noqa: SLF001
        raise HTTPException(status_code=503, detail="存储服务不可用")
    try:
        data = service._client.get_object(str(res.bucket), str(res.object_key)).read()  # noqa: SLF001
    except Exception as exc:  # noqa: BLE001
        logger.warning("download original: minio get failed: %s", exc)
        raise HTTPException(status_code=404, detail="原图读取失败") from None

    # 用户级 payload：user_id 从 token email 反查 users.id
    email = str(user_claims.get("sub", ""))
    user = (
        await db.execute(select(ORMUser).where(ORMUser.email == email, ORMUser.is_active.is_(True)))
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在")

    now = datetime.now(UTC)
    payload = build_user_payload(str(user.id), now.isoformat(timespec="seconds"))
    try:
        embedded = embed_payload(data, payload)
    except ValueError as exc:
        logger.warning("download original: stego embed failed: %s", exc)
        raise HTTPException(status_code=400, detail=f"无法对原图嵌入隐写：{exc}") from None

    # 下载日志（对账依据）
    db.add(
        ORMResourceDownloadLog(
            resource_id=rid,
            user_id=cast(UUID, user.id),
            user_email=email,
            ip=request.client.host if request.client else "",
            user_agent=(request.headers.get("user-agent") or "")[:512],
            payload=payload,
        )
    )
    await db.commit()

    filename = f"{res.name or 'image'}.png"
    return Response(
        content=embedded,
        media_type="image/png",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )
