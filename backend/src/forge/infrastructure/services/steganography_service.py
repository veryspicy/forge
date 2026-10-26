"""LSB 隐写（Steganography）服务 —— P4 下载溯源取证。

用途：将短文本 payload（站点标记 / 用户ID+时间戳）以 LSB 方式嵌入图片像素，
供取证时提取确认图片来源与下载人。与 pHash 互补：
- pHash 鲁棒证归属（缩放/裁剪/压缩后仍可匹配）
- 隐写精确指认（下载人 / 站点）

实现说明（重要约束）：
- 仅对**无损格式**可靠：LSB 位会被 JPEG 有损压缩破坏，嵌入输出统一为 PNG。
- 嵌入目标图片先转 RGB；输出恒为 PNG（payload 无损保留）。
- payload 编码：`F1|<len>|<utf8 bytes>|<crc16 hex>`，总长受限（默认 255）。
- 提取严格校验：header / 长度 / CRC 任一不符即返回 None（不做模糊解包）。

依赖：Pillow（backend 内置）。
"""

from __future__ import annotations

import logging
import struct
from io import BytesIO
from typing import Final, cast

logger = logging.getLogger(__name__)

_MAGIC: Final[bytes] = b"F1|"
_MAX_PAYLOAD_BYTES: Final[int] = 255
_CRC_LEN: Final[int] = 4  # crc16 hex（2 bytes）


def _crc16(data: bytes) -> int:
    """CRC-16/CCITT-FALSE，用于嵌入内容完整性校验。"""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def _build_payload_blob(payload: str) -> bytes:
    payload_bytes = payload.encode("utf-8")
    if len(payload_bytes) > _MAX_PAYLOAD_BYTES:
        raise ValueError(f"payload too long: {len(payload_bytes)} > {_MAX_PAYLOAD_BYTES} bytes")
    body = struct.pack(">H", len(payload_bytes)) + payload_bytes
    crc = struct.pack(">H", _crc16(body))
    return _MAGIC + body + crc


def _parse_payload_blob(blob: bytes) -> str | None:
    if len(blob) < len(_MAGIC) + 2 + _CRC_LEN:
        return None
    if blob[: len(_MAGIC)] != _MAGIC:
        return None
    (plen,) = struct.unpack(">H", blob[len(_MAGIC) : len(_MAGIC) + 2])
    body_end = len(_MAGIC) + 2 + plen
    crc_end = body_end + 2
    if len(blob) < crc_end:
        return None
    body = blob[len(_MAGIC) + 2 : body_end]
    stored_crc = struct.unpack(">H", blob[body_end:crc_end])[0]
    if _crc16(blob[len(_MAGIC) : body_end]) != stored_crc:
        return None
    try:
        return body.decode("utf-8")
    except UnicodeDecodeError:
        return None


def embed_payload(data: bytes, payload: str) -> bytes:
    """将 payload 嵌入图片（任意常见位图格式），返回 PNG bytes。

    输入非图片 / 无法解码时抛 ValueError；payload 超长时抛 ValueError。
    嵌入输出固定 PNG（RGB），像素级 LSB 1bit/通道。
    """
    from PIL import Image

    blob = _build_payload_blob(payload)
    required_bits = len(blob) * 8

    try:
        img: Image.Image = Image.open(BytesIO(data)).convert("RGB")
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"stego embed: image decode failed: {exc}") from None

    px = img.load()
    assert px is not None
    width, height = img.size
    if width * height * 3 < required_bits:
        raise ValueError(f"stego embed: image too small ({width}x{height}) for {len(blob)} bytes")

    bits: list[int] = []
    for byte in blob:
        bits.extend((byte >> i) & 1 for i in range(7, -1, -1))

    idx = 0
    for y in range(height):
        for x in range(width):
            r, g, b = cast(tuple[int, int, int], px[x, y])
            vals = [r, g, b]
            for c in range(3):
                if idx < len(bits):
                    vals[c] = (vals[c] & 0xFE) | bits[idx]
                    idx += 1
            px[x, y] = (vals[0], vals[1], vals[2])
            if idx >= len(bits):
                break
        if idx >= len(bits):
            break

    out = BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def extract_payload(data: bytes) -> str | None:
    """从图片数据提取隐写 payload；无隐写 / 损坏 / 非图片返回 None。"""
    from PIL import Image

    try:
        img = Image.open(BytesIO(data)).convert("RGB")
    except Exception as exc:  # noqa: BLE001
        logger.debug("stego extract: image decode failed: %s", exc)
        return None

    px = img.load()
    assert px is not None
    width, height = img.size

    # 读取全部 LSB 位，尝试按 magic 定位（PNG 无损时可精确对齐）
    bits: list[int] = []
    for y in range(height):
        for x in range(width):
            r, g, b = cast(tuple[int, int, int], px[x, y])
            bits.extend([r & 1, g & 1, b & 1])

    blob = bytearray()
    for start in range(0, len(bits) - 7, 8):
        byte = 0
        for i in range(8):
            byte = (byte << 1) | bits[start + i]
        blob.append(byte)

    payload = _parse_payload_blob(bytes(blob))
    if payload is not None:
        return payload
    # 退化：偏移扫描（保留位可能被破坏时尽力恢复），限 1 字节窗口
    for offset in (1, 2, 3):
        shifted = bytearray()
        for start in range(offset, len(bits) - 7, 8):
            byte = 0
            for i in range(8):
                byte = (byte << 1) | bits[start + i]
            shifted.append(byte)
        payload = _parse_payload_blob(bytes(shifted))
        if payload is not None:
            return payload
    return None


def build_site_payload(site_tag: str) -> str:
    """C 端展示链路站点级 payload（固定短标记，保证字节确定可缓存）。"""
    return f"S|{site_tag[:80]}"


def build_user_payload(user_id: str, timestamp: str) -> str:
    """原图下载链路用户级 payload。"""
    return f"U|{user_id}|{timestamp}"
