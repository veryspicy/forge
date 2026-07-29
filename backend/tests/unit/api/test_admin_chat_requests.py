"""Unit tests for Admin Chat Requests API."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from forge.main import dependencies

CONV_ID = str(uuid4())


def _setup_auth(test_client):
    async def _fake_get_db():
        yield AsyncMock()
    async def _fake_user_id():
        from uuid import UUID
        return UUID("d290f1ee-6c54-4b01-90e6-d701748f0851")
    test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
    test_client.app.dependency_overrides[dependencies.get_current_user_id] = _fake_user_id


class TestAdminChatRequestsAPI:
    """Test /api/admin/v1/chat-requests endpoints."""

    def test_list_chat_requests_success(self, test_client):
        _setup_auth(test_client)
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 5
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [
            MagicMock(to_dict=lambda: {"id": CONV_ID, "adopted": False})
        ]
        mock_session.execute.side_effect = [mock_result, mock_scalars]

        async def _fake_get_db():
            yield mock_session
        test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
        try:
            resp = test_client.get("/api/admin/v1/chat-requests/")
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200

    def test_get_conversation_success(self, test_client):
        _setup_auth(test_client)
        mock_session = AsyncMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [
            MagicMock(to_dict=lambda: {"role": "user", "content": "Hi"})
        ]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        async def _fake_get_db():
            yield mock_session
        test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
        try:
            resp = test_client.get(f"/api/admin/v1/chat-requests/{CONV_ID}")
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert resp.json()["messages"][0]["role"] == "user"

    def test_get_conversation_not_found(self, test_client):
        _setup_auth(test_client)
        mock_session = AsyncMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        async def _fake_get_db():
            yield mock_session
        test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
        try:
            resp = test_client.get(f"/api/admin/v1/chat-requests/{CONV_ID}")
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 404

    def test_chat_requests_unauthorized(self, test_client):
        resp = test_client.get("/api/admin/v1/chat-requests/")
        assert resp.status_code == 401

    def test_list_chat_requests_adopted_filter(self, test_client):
        """按 adopted=true 筛选已被采纳的对话"""
        _setup_auth(test_client)
        mock_session = AsyncMock()
        # count subquery
        mock_count = MagicMock()
        mock_count.scalar_one.return_value = 2
        # data subquery
        mock_rows = MagicMock()
        mock_rows.all.return_value = [
            MagicMock(
                conversation_id=uuid4(),
                first_at=None,
                last_at=None,
                msg_count=3,
            ),
        ]
        mock_result_count = MagicMock()
        mock_result_data = MagicMock()
        mock_result_count.scalar_one = mock_count.scalar_one
        mock_result_data.all = mock_rows.all
        mock_session.execute.side_effect = [mock_count, mock_rows]

        async def _fake_get_db():
            yield mock_session
        test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
        try:
            resp = test_client.get("/api/admin/v1/chat-requests/?adopted=true")
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert resp.json()["items"][0]["message_count"] == 3

    def test_chat_requests_forbidden_no_role(self, test_client):
        """普通用户无后台角色访问 Chat Requests 接口 → 403"""
        from fastapi import HTTPException

        async def _fake_user_id_403():
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        test_client.app.dependency_overrides[dependencies.get_current_user_id] = _fake_user_id_403
        try:
            response = test_client.get("/api/admin/v1/chat-requests/")
        finally:
            test_client.app.dependency_overrides.clear()
        assert response.status_code == 403
