"""Unit tests for MCP API Key authentication (new hash/verify API)."""

from __future__ import annotations

from datetime import UTC
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from forge.infrastructure.persistence.models import ORMMcpApiKey
from forge.mcp.auth import check_scope, generate_api_key, hash_key, verify_api_key


def _make_session_factory(session):
    """返回一个同步可调用对象，调用后产出支持 async with 的上下文管理器。"""
    factory = MagicMock()
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=False)
    factory.return_value = cm
    return factory


def _make_key(**overrides: object) -> ORMMcpApiKey:
    key = ORMMcpApiKey(
        name=overrides.get("name", "test-key"),
        key_prefix=overrides.get("key_prefix", "fk_"),
        key_hash=overrides.get("key_hash", "h" * 64),
        scopes=overrides.get("scopes", ["read"]),
        is_active=overrides.get("is_active", True),
        revoked_at=overrides.get("revoked_at"),
    )
    key.id = uuid4()
    return key


class TestHashKey:
    def test_hash_key_deterministic(self):
        assert hash_key("my-secret-key") == hash_key("my-secret-key")

    def test_hash_key_sha256_format(self):
        import hashlib

        assert hash_key("abc") == hashlib.sha256(b"abc").hexdigest()

    def test_generate_api_key_prefix(self):
        assert generate_api_key().startswith("fk_")


class TestVerifyApiKey:
    @pytest.mark.asyncio
    async def test_verify_valid_key(self):
        key = _make_key(key_hash=hash_key("my-secret-key"))
        session = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = key
        session.execute.return_value = result
        session_factory = _make_session_factory(session)

        with patch("forge.mcp.auth.async_session_factory", session_factory):
            result = await verify_api_key("my-secret-key")

        assert result is key
        session.commit.assert_awaited_once()
        assert key.last_used_at is not None

    @pytest.mark.asyncio
    async def test_verify_unknown_key_returns_none(self):
        session = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        session.execute.return_value = result
        session_factory = _make_session_factory(session)

        with patch("forge.mcp.auth.async_session_factory", session_factory):
            result = await verify_api_key("wrong-key")

        assert result is None
        session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_verify_revoked_key_returns_none(self):
        from datetime import datetime

        key = _make_key(
            key_hash=hash_key("revoked-key"),
            is_active=True,
            revoked_at=datetime.now(UTC),
        )
        session = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = key
        session.execute.return_value = result
        session_factory = _make_session_factory(session)

        with patch("forge.mcp.auth.async_session_factory", session_factory):
            result = await verify_api_key("revoked-key")

        assert result is None

    @pytest.mark.asyncio
    async def test_verify_inactive_key_returns_none(self):
        key = _make_key(key_hash=hash_key("inactive-key"), is_active=False)
        session = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = key
        session.execute.return_value = result
        session_factory = _make_session_factory(session)

        with patch("forge.mcp.auth.async_session_factory", session_factory):
            result = await verify_api_key("inactive-key")

        assert result is None


class TestCheckScope:
    @pytest.mark.asyncio
    async def test_read_tool_with_read_scope(self):
        key = _make_key(scopes=["read"])
        assert await check_scope(key, "list_products") is True

    @pytest.mark.asyncio
    async def test_write_tool_with_read_only_scope(self):
        key = _make_key(scopes=["read"])
        assert await check_scope(key, "create_product") is False

    @pytest.mark.asyncio
    async def test_write_tool_with_write_scope(self):
        key = _make_key(scopes=["write"])
        assert await check_scope(key, "create_product") is True

    @pytest.mark.asyncio
    async def test_all_scope_allows_everything(self):
        key = _make_key(scopes=["all"])
        assert await check_scope(key, "create_product") is True
        assert await check_scope(key, "list_products") is True

    @pytest.mark.asyncio
    async def test_unknown_tool_rejected(self):
        key = _make_key(scopes=["all"])
        assert await check_scope(key, "unknown_tool") is False

    @pytest.mark.asyncio
    async def test_default_scopes_is_read(self):
        key = _make_key(scopes=None)
        assert await check_scope(key, "list_products") is True

    @pytest.mark.asyncio
    async def test_dict_key_supported(self):
        key = {"scopes": ["write"]}
        assert await check_scope(key, "create_product") is True
        assert await check_scope(key, "list_products") is True
