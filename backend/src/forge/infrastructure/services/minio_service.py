"""MinIO 对象存储服务封装。

负责：
- 初始化连接（含 bucket 自动创建）
- 文件上传（支持自定义前缀、公开访问 URL）
- 简单删除（便于素材管理）

注：若 MinIO 不可达，降级为本地 uploads 目录存储，避免阻塞开发。
"""
from __future__ import annotations

import logging
import mimetypes
import os
from io import BytesIO
from pathlib import Path
from typing import Optional
from uuid import uuid4

try:
    from minio import Minio
    from minio.error import S3Error
except ImportError:  # pragma: no cover
    Minio = None  # type: ignore[assignment]
    S3Error = Exception  # type: ignore[assignment]

from forge.main.config import settings

logger = logging.getLogger(__name__)

_LOCAL_FALLBACK_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "uploads" / "site"


class MinioService:
    """封装 MinIO 上传 / URL 生成。"""

    _instance: Optional["MinioService"] = None

    def __init__(self) -> None:
        self._client: Optional[Minio] = None
        self._available = False
        self._endpoint = settings.minio_endpoint
        self._access_key = settings.minio_access_key
        self._secret_key = settings.minio_secret_key
        self._bucket = settings.minio_bucket or "forge-site"
        self._init_client()

    @classmethod
    def get(cls) -> "MinioService":
        if cls._instance is None:
            cls._instance = MinioService()
        return cls._instance

    def _init_client(self) -> None:
        if Minio is None:
            logger.warning("Minio library not installed; falling back to local file storage")
            return
        try:
            # 协议由配置显式指定（MINIO_SECURE），避免把容器服务名误判为 HTTPS
            secure = settings.minio_secure
            self._client = Minio(
                self._endpoint,
                access_key=self._access_key,
                secret_key=self._secret_key,
                secure=secure,
            )
            if not self._client.bucket_exists(self._bucket):
                self._client.make_bucket(self._bucket)
            self._available = True
            logger.info("MinIO connected: endpoint=%s bucket=%s", self._endpoint, self._bucket)
        except Exception as exc:  # noqa: BLE001 — 网络 / 配置错误统一降级
            logger.warning("MinIO unavailable (%s); falling back to local storage", exc)
            self._client = None
            self._available = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def available(self) -> bool:
        return self._available

    def upload_bytes(
        self,
        data: bytes,
        filename: str,
        *,
        prefix: str = "site/",
        content_type: Optional[str] = None,
    ) -> str:
        """上传二进制内容，返回可访问 URL（MinIO 公开 URL 或本地 /uploads/...）。"""
        ext = os.path.splitext(filename or "image.png")[1] or ".png"
        object_name = f"{prefix.rstrip('/')}/{uuid4().hex}{ext}"
        ctype = content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"

        if self._available and self._client is not None:
            try:
                length = len(data)
                self._client.put_object(
                    self._bucket,
                    object_name,
                    BytesIO(data),
                    length=length,
                    content_type=ctype,
                )
                return self._public_url(object_name)
            except Exception as exc:  # noqa: BLE001
                logger.warning("MinIO upload failed (%s); falling back to local", exc)

        # ---- 本地降级 ----
        return self._save_local(object_name, data)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _public_url(self, object_name: str) -> str:
        """构造 MinIO 对象的公开 URL。

        约定：部署时 product-images bucket 通过反代 /minio/product-images/... 暴露；
        本地开发阶段通过静态路由 /uploads/minio/:bucket/:obj 也可访问。
        这里使用通用的绝对路径形式 /minio/<bucket>/<object>，由网关/静态目录处理。
        """
        return f"/minio/{self._bucket}/{object_name}"

    def _save_local(self, object_name: str, data: bytes) -> str:
        path = _LOCAL_FALLBACK_DIR / object_name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return f"/uploads/site/{object_name}"


def get_minio_service() -> MinioService:
    """FastAPI Depends 友好的工厂函数。"""
    return MinioService.get()
