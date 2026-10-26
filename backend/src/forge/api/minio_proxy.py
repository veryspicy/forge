from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request, Response

from forge.infrastructure.services.minio_service import MinioService
from forge.infrastructure.services.url_signer import verify_url

logger = logging.getLogger(__name__)

minio_router = APIRouter(tags=["minio-proxy"])

try:
    from minio.error import S3Error
except ImportError:  # pragma: no cover
    S3Error = Exception  # type: ignore[misc, assignment]


@minio_router.get("/minio/{bucket}/{path:path}")
async def minio_object_proxy(bucket: str, path: str, request: Request) -> Response:
    # P3 signed-URL gate: mandatory when a signing secret is configured
    if not verify_url(
        request.url.path,
        exp=request.query_params.get("exp"),
        sig=request.query_params.get("sig"),
    ):
        raise HTTPException(status_code=403, detail="forbidden: missing or invalid signature")

    service: MinioService = MinioService.get()
    if not service.available or service._client is None:
        raise HTTPException(status_code=404, detail="not found")

    client = service._client
    try:
        stat = client.stat_object(bucket, path)
    except S3Error:
        raise HTTPException(status_code=404, detail="not found") from None
    except Exception as exc:  # noqa: BLE001
        logger.warning("minio stat_object error: %s", exc)
        raise HTTPException(status_code=404, detail="not found") from None

    try:
        data = client.get_object(bucket, path).read()
    except Exception as exc:  # noqa: BLE001
        logger.warning("minio get_object error: %s", exc)
        raise HTTPException(status_code=404, detail="not found") from None

    content_type: str | None = None
    if hasattr(stat, "content_type"):
        content_type = stat.content_type
    if not content_type:
        content_type = "application/octet-stream"

    headers = {"Cache-Control": "public, max-age=86400"}
    return Response(content=data, media_type=content_type, headers=headers)
