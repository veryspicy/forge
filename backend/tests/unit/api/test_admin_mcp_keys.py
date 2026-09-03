"""Unit tests for Admin MCP API Key management."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

from forge.main import dependencies

ADMIN_ID = "d290f1ee-6c54-4b01-90e6-d701748f0851"
KEY_ID = uuid4()


def _setup_auth(test_client):
    async def _fake_get_db():
        yield AsyncMock()

    async def _fake_admin():
        return {"id": UUID(ADMIN_ID), "role": "super_admin", "roles": ["super_admin"]}

    test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
    test_client.app.dependency_overrides[dependencies.get_current_admin] = _fake_admin


def _setup_session(test_client, side_effect=None):
    session = AsyncMock()
    if side_effect is not None:
        session.execute.side_effect = side_effect

    async def _fake_get_db():
        yield session

    test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
    return session


def _scalar_result(value):
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    return r


def _scalar_one_result(value):
    r = MagicMock()
    r.scalar_one.return_value = value
    return r


def _scalars_result(items):
    r = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = items
    r.scalars.return_value = scalars
    return r


def _make_key(**kw):
    k = MagicMock()
    k.to_dict.return_value = {
        "id": str(kw.get("id", KEY_ID)),
        "name": kw.get("name", "test-key"),
        "key_prefix": "abcd1234",
        "scopes": kw.get("scopes", ["read"]),
        "is_active": kw.get("is_active", True),
    }
    return k


class TestMcpKeysAPI:
    def test_create_key_success(self, test_client):
        _setup_auth(test_client)
        _setup_session(test_client)
        try:
            resp = test_client.post(
                "/api/admin/v1/mcp/keys",
                json={"name": "my-key", "scopes": ["read", "write"]},
            )
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["name"] == "my-key"
        assert data["api_key"]  # 明文仅此一次返回

    def test_create_key_empty_name(self, test_client):
        _setup_auth(test_client)
        _setup_session(test_client)
        try:
            resp = test_client.post("/api/admin/v1/mcp/keys", json={"name": "  "})
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 400
        assert resp.json()["code"] == "MCP_KEY_NAME_REQUIRED"

    def test_create_key_invalid_scope(self, test_client):
        _setup_auth(test_client)
        _setup_session(test_client)
        try:
            resp = test_client.post("/api/admin/v1/mcp/keys", json={"name": "k", "scopes": ["admin"]})
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 400
        assert resp.json()["code"] == "MCP_KEY_INVALID_SCOPE"

    def test_create_key_empty_scopes(self, test_client):
        _setup_auth(test_client)
        _setup_session(test_client)
        try:
            resp = test_client.post("/api/admin/v1/mcp/keys", json={"name": "k", "scopes": []})
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 400

    def test_list_keys(self, test_client):
        _setup_auth(test_client)
        _setup_session(test_client, [_scalars_result([_make_key()])])
        try:
            resp = test_client.get("/api/admin/v1/mcp/keys")
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert resp.json()["total"] == 1
        assert resp.json()["items"][0]["name"] == "test-key"

    def test_revoke_key_success(self, test_client):
        _setup_auth(test_client)
        _setup_session(test_client, [_scalar_result(_make_key())])
        try:
            resp = test_client.delete(f"/api/admin/v1/mcp/keys/{KEY_ID}")
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 204

    def test_revoke_key_not_found(self, test_client):
        _setup_auth(test_client)
        _setup_session(test_client, [_scalar_result(None)])
        try:
            resp = test_client.delete(f"/api/admin/v1/mcp/keys/{KEY_ID}")
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 404

    def test_revoke_key_invalid_id(self, test_client):
        _setup_auth(test_client)
        _setup_session(test_client)
        try:
            resp = test_client.delete("/api/admin/v1/mcp/keys/not-a-uuid")
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 400

    def test_list_audit_logs(self, test_client):
        _setup_auth(test_client)
        log = MagicMock()
        log.id = uuid4()
        log.api_key_id = KEY_ID
        log.agent_name = "agent-x"
        log.tool_name = "get_catalog_products"
        log.arguments = {"x": 1}
        log.result_status = "ok"
        log.error = None
        log.created_at = None
        _setup_session(
            test_client,
            [_scalar_one_result(1), _scalars_result([log])],
        )
        try:
            resp = test_client.get("/api/admin/v1/mcp/audit-logs?tool_name=get_catalog_products&result_status=ok")
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["tool_name"] == "get_catalog_products"
        assert data["page"] == 1

    def test_unauthorized(self, test_client):
        resp = test_client.get("/api/admin/v1/mcp/keys")
        assert resp.status_code == 401

    def test_forbidden(self, test_client):
        from fastapi import HTTPException

        async def _fake_admin_403():
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        test_client.app.dependency_overrides[dependencies.get_current_admin] = _fake_admin_403
        try:
            resp = test_client.get("/api/admin/v1/mcp/keys")
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 403
