"""Signed URL helper for protected media paths.

Strategy (aligned with Cloudflare Images signed URLs):
  - backend signs the *path* with HMAC-SHA256(secret, f"{path}|{exp}")
  - consumers receive `?exp=<unix>&sig=<hex>` appended to /minio/** and /uploads/** URLs
  - the proxy layer verifies expiry + signature before serving; missing/invalid/expired => 403
  - when no secret is configured the helper is inert (sign returns the URL untouched,
    verify always passes), keeping local/dev deployments compatible
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import time
import urllib.parse

from forge.main.config import settings

logger = logging.getLogger(__name__)

_DEFAULT_TTL_SECONDS = 7 * 24 * 3600  # 7 days, matches Cache-Control max-age window


def _secret() -> str:
    return (settings.minio_signed_url_secret or "").strip()


def _enabled() -> bool:
    return bool(_secret())


def sign_url(url: str, *, ttl_seconds: int | None = None) -> str:
    """Append exp+sig to a protected relative URL; leave other URLs untouched."""
    if not url or not _enabled():
        return url
    if not (url.startswith("/minio/") or url.startswith("/uploads/")):
        return url
    ttl = ttl_seconds if ttl_seconds is not None else _DEFAULT_TTL_SECONDS
    exp = int(time.time()) + ttl
    sig = _signature(url, exp)
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}exp={exp}&sig={sig}"


def verify_url(path: str, *, exp: str | None, sig: str | None) -> bool:
    """Verify an incoming protected-media request. Returns True when inert (no secret)."""
    if not _enabled():
        return True
    if not exp or not sig:
        return False
    try:
        exp_int = int(exp)
    except (TypeError, ValueError):
        return False
    if time.time() > exp_int:
        return False
    expected = _signature(path, exp_int)
    return hmac.compare_digest(expected, sig)


def _signature(path: str, exp: int) -> str:
    # strip any existing query so the signed base is deterministic
    base_path = urllib.parse.urlsplit(path).path
    message = f"{base_path}|{exp}".encode()
    return hmac.new(_secret().encode(), message, hashlib.sha256).hexdigest()
