"""MCP API Key 鉴权。

API Key 以 SHA-256 哈希存储，请求时明文比对哈希。
每次调用更新 last_used_at；写审计日志。
"""

from __future__ import annotations

import hashlib
import secrets
from typing import Any

from sqlalchemy import select

from forge.infrastructure.persistence.models import ORMMcpApiKey, ORMMcpAuditLog
from forge.main.dependencies import async_session_factory

# 工具读写分类（用于 scope 校验）
READ_TOOLS = {
    "list_products",
    "list_suppliers",
    "get_supplier_products",
    "get_sales_stats",
    "get_product",
}
WRITE_TOOLS = {
    "create_product",
    "update_product",
    "update_product_price",
    "set_product_status",
    "batch_create_products",
}


def hash_key(api_key: str) -> str:
    """对明文 API Key 做 SHA-256 哈希。"""
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def generate_api_key() -> str:
    """生成新 API Key，前缀 fk_ 便于识别与吊销。"""
    return "fk_" + secrets.token_urlsafe(32)


async def verify_api_key(api_key: str) -> ORMMcpApiKey | None:
    """校验 API Key，返回有效的 key 记录；无效/已吊销返回 None。"""
    key_hash = hash_key(api_key)
    async with async_session_factory() as session:
        result = await session.execute(select(ORMMcpApiKey).where(ORMMcpApiKey.key_hash == key_hash))
        key = result.scalar_one_or_none()
        if key is None or not key.is_active or key.revoked_at is not None:
            return None
        # 更新最后使用时间
        from datetime import datetime

        key.last_used_at = datetime.now()
        await session.commit()
        return key


async def check_scope(key: ORMMcpApiKey | dict[str, Any], tool_name: str) -> bool:
    """校验工具调用是否在 key 的 scopes 范围内。"""
    scopes = set(key.get("scopes") or ["read"]) if isinstance(key, dict) else set(key.scopes or ["read"])
    if tool_name in READ_TOOLS:
        return bool(scopes & {"read", "read_only", "all"}) or "write" in scopes
    if tool_name in WRITE_TOOLS:
        return bool(scopes & {"write", "all"})
    # 未知工具默认拒绝
    return False


async def write_audit_log(
    *,
    api_key_id: str | None,
    agent_name: str | None,
    tool_name: str,
    arguments: dict[str, Any],
    result_status: str = "ok",
    error: str | None = None,
) -> None:
    """写入 MCP 调用审计日志。"""
    async with async_session_factory() as session:
        log = ORMMcpAuditLog(
            api_key_id=api_key_id,
            agent_name=agent_name,
            tool_name=tool_name,
            arguments=arguments,
            result_status=result_status,
            error=error,
        )
        session.add(log)
        await session.commit()
