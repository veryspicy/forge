"""图片上传压缩服务：视觉无损降存储。

策略（对齐行业实践：WebP 编码，q80-90 视觉无损档）：
- JPEG → WebP 有损（quality=85，人眼无感知差异，照片类平均省 40-60%）
- PNG → WebP 无损（保留 alpha 通道，真正不降品质，平均省 20-40%）
- 已是 WebP / SVG / GIF / 动图 / 非图片 → 原样返回（避免二次有损）
- 压缩无收益（压缩后 >= 原体积）→ 回退原图，不劣化不增存

依赖：pillow（backend pyproject 已内置，无需新增依赖）。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from io import BytesIO

logger = logging.getLogger(__name__)

# 视觉无损档位：业界共识 q80-90 人眼无法感知与原始 JPEG 的差异
_WEBP_QUALITY = 85
# 跳过格式：矢量图与动图不做像素重编码
_SKIP_EXTS = {".svg", ".gif"}
# 仅处理可重编码为 WebP 的静态位图
_SUPPORTED_MIMES = {"image/jpeg", "image/jpg", "image/png"}
_SUPPORTED_EXTS = {".jpg", ".jpeg", ".png"}


@dataclass(frozen=True)
class CompressedImage:
    """压缩结果：调用方用新 data/mime/ext 替换原内容存储。"""

    data: bytes
    mime: str
    ext: str
    original_size: int
    compressed_size: int

    @property
    def saved_bytes(self) -> int:
        """压缩节省的字节数（>=0，无收益时不会返回 CompressedImage）。"""
        return self.original_size - self.compressed_size


def compress_image(data: bytes, mime: str, ext: str = "") -> CompressedImage | None:
    """压缩单张静态位图（JPEG/PNG）为 WebP。

    返回 CompressedImage 表示压缩有收益、应替换存储内容；
    返回 None 表示不可压缩或压缩无收益，调用方必须保持原图存储。
    """
    if not data:
        return None
    ext_l = (ext or "").lower()
    mime_l = (mime or "").lower()
    if ext_l in _SKIP_EXTS:
        return None
    if mime_l not in _SUPPORTED_MIMES and ext_l not in _SUPPORTED_EXTS:
        return None
    is_png = mime_l == "image/png" or ext_l == ".png"

    try:
        from PIL import Image

        img = Image.open(BytesIO(data))
        img.load()
    except Exception as exc:  # noqa: BLE001 — 解码失败按不可压缩处理
        logger.debug("compress: image decode failed: %s", exc)
        return None

    # 归一化颜色模式：P/LA 先转 RGBA 保留透明；其他非 RGB/RGBA 转 RGB
    if img.mode in ("P", "LA"):
        converted = img.convert("RGBA")
    elif img.mode not in ("RGB", "RGBA"):
        converted = img.convert("RGB")
    else:
        converted = img

    buf = BytesIO()
    try:
        if is_png:
            # PNG → 无损 WebP：不引入任何有损，alpha 保留
            converted.save(buf, format="WEBP", lossless=True)
        else:
            # JPEG → 有损 WebP：视觉无损档位
            converted.save(buf, format="WEBP", quality=_WEBP_QUALITY)
    except Exception as exc:  # noqa: BLE001 — 编码失败按不可压缩处理
        logger.debug("compress: webp encode failed: %s", exc)
        return None
    compressed = buf.getvalue()

    # 无收益（小图/已被压缩过/低质量源图）回退原图，避免劣化或增存
    if len(compressed) >= len(data):
        logger.debug("compress: no gain (%d -> %d), keep original", len(data), len(compressed))
        return None

    return CompressedImage(
        data=compressed,
        mime="image/webp",
        ext=".webp",
        original_size=len(data),
        compressed_size=len(compressed),
    )
