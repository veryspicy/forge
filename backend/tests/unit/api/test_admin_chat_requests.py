"""Unit tests for Admin Chat Requests API (stub implementation)."""

from __future__ import annotations

from uuid import UUID

from forge.main import dependencies


def _setup_auth(test_client):
    async def _fake_get_db():
        yield None

    async def _fake_admin():
        return {"id": UUID("d290f1ee-6c54-4b01-90e6-d701748f0851"), "role": "super_admin", "roles": ["super_admin"]}

    test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
    test_client.app.dependency_overrides[dependencies.get_current_admin] = _fake_admin


class TestAdminChatRequestsAPI:
    """Test /api/admin/v1/chat-requests endpoints (stub: list only, empty)."""

    def test_list_chat_requests_success(self, test_client):
        _setup_auth(test_client)
        try:
            resp = test_client.get("/api/admin/v1/chat-requests/")
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert resp.json() == {"items": [], "total": 0}

    def test_list_chat_requests_adopted_filter(self, test_client):
        """stub 接口忽略筛选参数，返回空列表"""
        _setup_auth(test_client)
        try:
            resp = test_client.get("/api/admin/v1/chat-requests/?adopted=true")
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert resp.json()["items"] == []

    def test_chat_requests_unauthorized(self, test_client):
        resp = test_client.get("/api/admin/v1/chat-requests/")
        assert resp.status_code == 401

    def test_chat_requests_forbidden_no_role(self, test_client):
        """普通用户无后台角色访问 Chat Requests 接口 → 403"""
        from fastapi import HTTPException

        async def _fake_admin_403():
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        test_client.app.dependency_overrides[dependencies.get_current_admin] = _fake_admin_403
        try:
            response = test_client.get("/api/admin/v1/chat-requests/")
        finally:
            test_client.app.dependency_overrides.clear()
        assert response.status_code == 403
