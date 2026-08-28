"""Unit tests for Admin Users API (simplified: list only)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import UUID

from forge.main import dependencies


def _setup_auth(test_client):
    async def _fake_get_db():
        yield AsyncMock()

    async def _fake_admin():
        return {"id": UUID("d290f1ee-6c54-4b01-90e6-d701748f0851"), "role": "super_admin", "roles": ["super_admin"]}

    test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
    test_client.app.dependency_overrides[dependencies.get_current_admin] = _fake_admin


class TestAdminUsersAPI:
    """Test /api/admin/v1/users endpoints (simplified: list only)."""

    def test_list_users_success(self, test_client):
        from forge.infrastructure.persistence.repositories.user_repo import SQLAlchemyUserRepository

        _setup_auth(test_client)
        with patch.object(
            SQLAlchemyUserRepository,
            "list_users",
            new_callable=AsyncMock,
            return_value={"items": [{"id": "u1", "email": "a@b.com"}], "total": 1},
        ):
            resp = test_client.get("/api/admin/v1/users/")
        test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_users_unauthorized(self, test_client):
        resp = test_client.get("/api/admin/v1/users/")
        assert resp.status_code == 401

    def test_users_forbidden_no_role(self, test_client):
        """普通用户无后台角色访问 Users 接口 → 403"""
        from fastapi import HTTPException

        async def _fake_admin_403():
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        test_client.app.dependency_overrides[dependencies.get_current_admin] = _fake_admin_403
        try:
            response = test_client.get("/api/admin/v1/users/")
        finally:
            test_client.app.dependency_overrides.clear()
        assert response.status_code == 403
