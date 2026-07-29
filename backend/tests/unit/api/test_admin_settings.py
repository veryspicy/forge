"""Unit tests for Admin Settings API."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from forge.main import dependencies


def _setup_auth(test_client):
    async def _fake_get_db():
        yield AsyncMock()
    async def _fake_user_id():
        from uuid import UUID
        return UUID("d290f1ee-6c54-4b01-90e6-d701748f0851")
    test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
    test_client.app.dependency_overrides[dependencies.get_current_user_id] = _fake_user_id


class TestAdminSettingsAPI:
    """Test /api/admin/v1/settings endpoints."""

    def test_get_settings_success(self, test_client):
        _setup_auth(test_client)
        try:
            resp = test_client.get("/api/admin/v1/settings/")
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200

    def test_update_settings_success(self, test_client):
        _setup_auth(test_client)
        try:
            resp = test_client.put(
                "/api/admin/v1/settings/",
                json={
                    "site_name": "Forge",
                    "admin_email": "admin@shop.com",
                    "default_currency": "USD",
                    "low_cost_threshold": 5.0,
                    "high_cost_threshold": 100.0,
                    "auto_approve_limit": 50.0,
                },
            )
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200

    def test_settings_unauthorized(self, test_client):
        resp = test_client.get("/api/admin/v1/settings/")
        assert resp.status_code == 401

    def test_settings_forbidden_no_role(self, test_client):
        """普通用户无后台角色访问 Settings 接口 → 403"""
        from fastapi import HTTPException

        async def _fake_user_id_403():
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        test_client.app.dependency_overrides[dependencies.get_current_user_id] = _fake_user_id_403
        try:
            response = test_client.get("/api/admin/v1/settings/")
        finally:
            test_client.app.dependency_overrides.clear()
        assert response.status_code == 403
