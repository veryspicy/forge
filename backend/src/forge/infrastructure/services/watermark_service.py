"""图片水印服务：上传时叠加半透明角标品牌水印（P1）。

设计约束（见 docs/IMAGE-PROTECTION-PLAN.md）：
- 仅作为上传链路的可选增强，不阻塞上传（失败降级为原图）
- 水印面积 ≤ 5%（maxAreaRatio），透明度 30-40%，贴角落
- 水印源为 admin 站点设置上传的品牌 Logo（resources 表登记的图片）

注意：水印只作用于写入 MinIO 的主图与缩略图，不修改原始上传字节的 sha256 登记逻辑之外
（sha256 基于上传原文件计算，用于溯源取证，不应被水印污染）。
"""

from __future__ import annotations

import logging
import re
from io import BytesIO
from typing import Any, cast

try:
    from PIL import Image as PILImage
    from PIL import ImageDraw, ImageOps
except ImportError:  # pragma: no cover
    PILImage = None  # type: ignore[assignment]
    ImageDraw = None  # type: ignore[assignment]
    ImageOps = None  # type: ignore[assignment]

from forge.infrastructure.services.minio_service import MinioService

logger = logging.getLogger(__name__)

# 位置白名单
_POSITIONS = ("top-left", "top-right", "bottom-left", "bottom-right")


def _object_key_from_url(url: str) -> str:
    """从资源 URL 反推 object_key（/minio/{bucket}/{key} 或 /uploads/site/{key}）。"""
    url = (url or "").split("?", 1)[0]
    if url.startswith("/uploads/site/"):
        return url[len("/uploads/site/") :]
    m = re.match(r"^/minio/[^/]+/(.+)$", url)
    if m:
        return m.group(1)
    return ""


def _load_logo(logo_url: str, minio: MinioService) -> PILImage.Image | None:
    """加载水印 Logo：优先按 object_key 读 MinIO/本地，失败尝试直读 URL。"""
    if not logo_url:
        return None
    try:
        key = _object_key_from_url(logo_url)
        data = minio.get_object(key) if key else None
        if data is None and (logo_url.startswith("http://") or logo_url.startswith("https://")):
            import urllib.request

            with urllib.request.urlopen(logo_url, timeout=5) as resp:  # noqa: S310 — 仅管理员配置的 Logo URL
                data = resp.read()
        if not data:
            return None
        logo = PILImage.open(BytesIO(data))
        logo.load()
        if logo.mode in ("RGBA", "LA"):
            return logo.convert("RGBA")
        return logo.convert("RGBA") if PILImage is not None else None
    except Exception as exc:  # noqa: BLE001 — 水印失败不阻塞上传
        logger.warning("watermark logo load failed: %s", exc)
        return None


def apply_watermark(
    image_data: bytes,
    *,
    logo_url: str,
    position: str = "bottom-right",
    opacity: float = 0.35,
    max_area_ratio: float = 0.05,
    minio: MinioService | None = None,
) -> bytes:
    """对图片字节叠加半透明角标水印，返回新图片字节（失败返回原字节）。

    参数：
    - image_data: 原图字节（PNG/JPEG/WebP 等 PIL 可读格式）
    - logo_url: 水印 Logo 的资源 URL（/minio/... 或 /uploads/site/...）
    - position: 角落位置，top-left/top-right/bottom-left/bottom-right
    - opacity: 水印透明度 0~1（推荐 0.30~0.40）
    - max_area_ratio: 水印占图片最大面积比（默认 0.05 = 5%）
    """
    if PILImage is None:
        return image_data
    try:
        img: Any = PILImage.open(BytesIO(image_data))
        img.load()
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGBA")
        logo_loaded = _load_logo(logo_url, minio) if minio is not None else None
        if logo_loaded is None:
            return image_data
        logo = cast(Any, logo_loaded)

        # 等比缩放：水印面积 ≤ max_area_ratio * 图片面积
        img_w, img_h = img.size
        target_area = max(1.0, max_area_ratio * img_w * img_h)
        logo_w, logo_h = logo.size
        scale = min(1.0, (target_area / (logo_w * logo_h)) ** 0.5)
        if scale < 1.0:
            new_w = max(1, int(logo_w * scale))
            new_h = max(1, int(logo_h * scale))
            logo = logo.resize((new_w, new_h), PILImage.Resampling.LANCZOS)

        # 透明度
        alpha = logo.getchannel("A").point(lambda a: int(a * max(0.0, min(1.0, opacity))))
        logo.putalpha(alpha)

        # 边距：取图片短边的 1.5%
        pad = max(2, int(min(img_w, img_h) * 0.015))
        if position == "top-left":
            box = (pad, pad)
        elif position == "top-right":
            box = (img_w - logo.width - pad, pad)
        elif position == "bottom-left":
            box = (pad, img_h - logo.height - pad)
        else:  # bottom-right
            box = (img_w - logo.width - pad, img_h - logo.height - pad)

        base = img.convert("RGBA")
        base.paste(logo, box, logo)
        out = BytesIO()
        fmt = img.format or "JPEG"
        if fmt.upper() == "PNG":
            base.save(out, format="PNG")
        elif fmt.upper() in ("WEBP", "JPEG", "JPG"):
            base.convert("RGB").save(out, format="JPEG", quality=88)
        else:
            base.save(out, format=fmt)
        return out.getvalue()
    except Exception as exc:  # noqa: BLE001 — 水印失败不阻塞上传
        logger.warning("apply_watermark failed: %s", exc)
        return image_data
