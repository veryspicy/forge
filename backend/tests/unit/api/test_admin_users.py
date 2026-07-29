"""Unit tests for Admin Users API."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from forge.main import dependencies

ADMIN_ID = "d290f1ee-6c54-4b01-90e6-d701748f0851"
TARGET_ID = str(uuid4())


def _setup_auth(test_client):
    async def _fake_get_db():
        yield AsyncMock()
    async def _fake_user_id():
        from uuid import UUID
        return UUID(ADMIN_ID)
    test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
    test_client.app.dependency_overrides[dependencies.get_current_user_id] = _fake_user_id


class TestAdminUsersAPI:
    """Test /api/admin/v1/users endpoints."""

    def test_list_users_success(self, test_client):
        """List users."""
        _setup_auth(test_client)
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 3
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [
            MagicMock(to_dict=lambda: {"id": TARGET_ID, "email": "u@t.com", "role": "user"})
        ]
        mock_session.execute.side_effect = [mock_result, mock_scalars]

        async def _fake_get_db():
            yield mock_session
        test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
        try:
            resp = test_client.get("/api/admin/v1/users/")
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200

    def test_get_user_success(self, test_client):
        _setup_auth(test_client)
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock(
            to_dict=lambda: {"id": TARGET_ID, "email": "u@t.com", "role": "user"}
        )
        mock_session.execute.return_value = mock_result

        async def _fake_get_db():
            yield mock_session
        test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
        try:
            resp = test_client.get(f"/api/admin/v1/users/{TARGET_ID}")
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert resp.json()["email"] == "u@t.com"

    def test_get_user_not_found(self, test_client):
        _setup_auth(test_client)
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        async def _fake_get_db():
            yield mock_session
        test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
        try:
            resp = test_client.get(f"/api/admin/v1/users/{TARGET_ID}")
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 404

    def test_update_user_role_success(self, test_client):
        _setup_auth(test_client)
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock(
            id=TARGET_ID, role="user"
        )
        mock_session.execute.return_value = mock_result

        async def _fake_get_db():
            yield mock_session
        test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
        try:
            resp = test_client.patch(
                f"/api/admin/v1/users/{TARGET_ID}/role",
                json={"role": "admin"},
            )
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200

    def test_update_own_role_blocked(self, test_client):
        """Cannot change own role."""
        _setup_auth(test_client)
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock(
            id=ADMIN_ID, role="admin"
        )
        mock_session.execute.return_value = mock_result

        async def _fake_get_db():
            yield mock_session
        test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
        try:
            resp = test_client.patch(
                f"/api/admin/v1/users/{ADMIN_ID}/role",
                json={"role": "support"},
            )
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 400

    def test_update_role_invalid(self, test_client):
        """Invalid role returns 400."""
        _setup_auth(test_client)
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock(
            id=TARGET_ID, role="user"
        )
        mock_session.execute.return_value = mock_result

        async def _fake_get_db():
            yield mock_session
        test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
        try:
            resp = test_client.patch(
                f"/api/admin/v1/users/{TARGET_ID}/role",
                json={"role": "superuser"},
            )
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 400

    def test_update_role_user_not_found(self, test_client):
        _setup_auth(test_client)
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        async def _fake_get_db():
            yield mock_session
        test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
        try:
            resp = test_client.patch(
                f"/api/admin/v1/users/{TARGET_ID}/role",
                json={"role": "admin"},
            )
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 404

    def test_users_unauthorized(self, test_client):
        resp = test_client.get("/api/admin/v1/users/")
        assert resp.status_code == 401

    def test_users_forbidden_no_role(self, test_client):
        """普通用户无后台角色访问 Users 接口 → 403"""
        from fastapi import HTTPException

        async def _fake_user_id_403():
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        test_client.app.dependency_overrides[dependencies.get_current_user_id] = _fake_user_id_403
        try:
            response = test_client.get("/api/admin/v1/users/")
        finally:
            test_client.app.dependency_overrides.clear()
        assert response.status_code == 403
