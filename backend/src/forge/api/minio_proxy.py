from __future__ import annotations

import logging
import os

from fastapi import APIRouter, HTTPException, Request, Response

from forge.infrastructure.services.minio_service import MinioService
from forge.infrastructure.services.url_signer import verify_url

logger = logging.getLogger(__name__)

minio_router = APIRouter(tags=["minio-proxy"])

# P4 展示链路站点级隐写：仅对无损位图（PNG/BMP）嵌入，JPEG/WebP 有损压缩会破坏 LSB，跳过。
_STEGO_ENABLED = os.getenv("IMAGE_STEGANOGRAPHY_ENABLED", "1") == "1"
_SITE_TAG = os.getenv("IMAGE_STEGANOGRAPHY_SITE_TAG", "forge")
_STEGO_WARNED = False


def _embed_site_stego(data: bytes, content_type: str) -> tuple[bytes, str]:
    """无损位图响应嵌入站点标记（字节确定，可缓存）。返回 (嵌入后字节, 新 content_type)。"""
    global _STEGO_WARNED  # noqa: PLW0603
    if not _STEGO_ENABLED:
        return data, content_type
    if content_type not in ("image/png", "image/bmp"):
        return data, content_type
    try:
        from forge.infrastructure.services.steganography_service import embed_payload

        payload = f"S|{_SITE_TAG}"
        return embed_payload(data, payload), "image/png"
    except Exception as exc:  # noqa: BLE001 — 隐写失败不阻塞原图
        if not _STEGO_WARNED:
            _STEGO_WARNED = True
            logger.warning("stego embed on proxy failed: %s", exc)
        return data, content_type

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

    data, content_type = _embed_site_stego(data, content_type)

    headers = {"Cache-Control": "public, max-age=86400"}
    return Response(content=data, media_type=content_type, headers=headers)
