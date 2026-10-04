"""对称加解密服务（Fernet：AES-128-CBC + HMAC-SHA256）。

密钥由 ``settings.secret_key`` 经 SHA-256 派生，保证同一部署内可自洽加解密。
注意：轮换 SECRET_KEY 会导致既有密文不可解密（表现为后台显示「未配置」，需重新填写）。

用法::

    from forge.infrastructure.services.crypto_service import decrypt_str, encrypt_str

    token = encrypt_str("nvapi-xxxx")
    plain = decrypt_str(token)
"""

from __future__ import annotations

import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken

from forge.main.config import settings

logger = logging.getLogger(__name__)


def _fernet() -> Fernet:
    """由 SECRET_KEY 派生出稳定的 Fernet 实例。"""
    digest = hashlib.sha256(settings.secret_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_str(plain: str) -> str:
    """明文 → 密文（ASCII 文本）；空值原样返回空串。"""
    if not plain:
        return ""
    return _fernet().encrypt(plain.encode("utf-8")).decode("ascii")


def decrypt_str(token: str | None) -> str:
    """密文 → 明文；密文为空或解密失败（SECRET_KEY 变更）时返回空串。"""
    if not token:
        return ""
    try:
        return _fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError, UnicodeDecodeError):
        logger.warning("系统配置密文解密失败（SECRET_KEY 可能已变更），请在后台重新填写")
        return ""


def mask_secret(plain: str) -> str:
    """脱敏展示：保留前 6 位与后 4 位，中间以 ``***`` 代替。"""
    if not plain:
        return ""
    if len(plain) <= 12:
        return "*" * len(plain)
    return f"{plain[:6]}***{plain[-4:]}"
