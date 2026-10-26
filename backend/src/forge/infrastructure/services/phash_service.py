"""感知哈希（pHash）指纹服务。

用途：为上传图片计算 64bit 感知哈希，落库后供盗图发现与溯源取证
（与隐写互补：pHash 鲁棒性强，缩放/裁剪/压缩后仍可匹配，用于归属确认；
隐写用于追责到具体下载人）。

实现：经典 DCT pHash —— 灰度化 → 32x32 → DCT → 取左上 8x8 低频（跳过 DC）
→ 以中位数为阈值转 64bit → hex 字符串。

依赖：Pillow + numpy（backend pyproject 已内置，无需新增依赖）。
"""

from __future__ import annotations

import logging
from io import BytesIO

logger = logging.getLogger(__name__)

_HASH_BITS = 64
_DCT_SIZE = 32
_FEATURE_SIZE = 8


def compute_phash(data: bytes | None) -> str | None:
    """计算图片感知哈希（64bit hex）。非图片 / 解析失败返回 None。"""
    if not data:
        return None
    try:
        from PIL import Image

        img = Image.open(BytesIO(data)).convert("L")
        img = img.resize((_DCT_SIZE, _DCT_SIZE), Image.Resampling.LANCZOS)
    except Exception as exc:  # noqa: BLE001 — 非图片数据统一返回 None
        logger.debug("phash: image decode failed: %s", exc)
        return None

    try:
        import numpy as np

        arr = np.asarray(img, dtype=np.float32) / 255.0
        dct: np.ndarray = np.asarray(_dct_2d(arr), dtype=np.float32)
        feature: np.ndarray = dct[:_FEATURE_SIZE, :_FEATURE_SIZE].flatten()
        # 以中位数为阈值（对齐 imagehash.phash 标准做法，对缩放/压缩更稳健）
        threshold = float(np.median(feature))
        bits = ["1" if v > threshold else "0" for v in feature]
        hex_str = hex(int("".join(bits), 2))[2:].zfill(_HASH_BITS // 4)
        return hex_str
    except Exception as exc:  # noqa: BLE001 — numpy 缺失或异常时降级
        logger.warning("phash: computation failed: %s", exc)
        return None


def phash_distance(a: str, b: str) -> int:
    """计算两个 64bit hex 感知哈希的汉明距离（不同 bit 数）。"""
    if not a or not b:
        return _HASH_BITS
    try:
        x = int(a, 16)
        y = int(b, 16)
    except ValueError:
        return _HASH_BITS
    return (x ^ y).bit_count()


def is_similar(a: str, b: str, threshold: int = 10) -> bool:
    """汉明距离 <= threshold 视为相似（默认 10，行业常见阈值）。"""
    return phash_distance(a, b) <= threshold


def _dct_2d(matrix: object) -> object:
    """2D DCT-II（分离式，归一化正交），纯 numpy 实现避免依赖 scipy。"""
    import numpy as np

    mat = np.asarray(matrix, dtype=np.float32)
    n = mat.shape[0]
    # 一维 DCT-II 变换矩阵 A[k, n] = alpha_k * cos(pi*(2n+1)*k/(2N))
    k = np.arange(n, dtype=np.float32)[:, None]
    idx = np.arange(n, dtype=np.float32)[None, :]
    cos_base = np.cos(np.pi * (2 * idx + 1) * k / (2 * n))
    alpha = np.ones(n, dtype=np.float32)
    alpha[0] = np.sqrt(1.0 / n)
    alpha[1:] = np.sqrt(2.0 / n)
    a_mat = alpha[:, None] * cos_base
    # X = A * mat * A^T
    out = a_mat @ mat @ a_mat.T
    return out
