from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Response

from forge.infrastructure.services.minio_service import MinioService

logger = logging.getLogger(__name__)

minio_router = APIRouter(tags=["minio-proxy"])

try:
    from minio.error import S3Error
except ImportError:  # pragma: no cover
    S3Error = Exception


@minio_router.get("/minio/{bucket}/{path:path}")
async def minio_object_proxy(bucket: str, path: str):
    service: MinioService = MinioService.get()
    if not service.available or service._client is None:
        raise HTTPException(status_code=404, detail="not found")

    client = service._client
    try:
        stat = client.stat_object(bucket, path)
    except S3Error:
        raise HTTPException(status_code=404, detail="not found")
    except Exception as exc:  # noqa: BLE001
        logger.warning("minio stat_object error: %s", exc)
        raise HTTPException(status_code=404, detail="not found")

    try:
        data = client.get_object(bucket, path).read()
    except Exception as exc:  # noqa: BLE001
        logger.warning("minio get_object error: %s", exc)
        raise HTTPException(status_code=404, detail="not found")

    content_type: Optional[str] = None
    if hasattr(stat, "content_type"):
        content_type = stat.content_type
    if not content_type:
        content_type = "application/octet-stream"

    headers = {"Cache-Control": "public, max-age=86400"}
    return Response(content=data, media_type=content_type, headers=headers)
