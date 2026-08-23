"""Unit tests for Admin Auth API (new admin/v1 login endpoint)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from forge.api.admin.v1 import auth as auth_module

ADMIN_ID = "d290f1ee-6c54-4b01-90e6-d701748f0851"


def _make_admin(email="admin@test.com", role="super_admin", is_active=True):
    admin = MagicMock()
    admin.id = ADMIN_ID
    admin.email = email
    admin.display_name = "Admin"
    admin.role = role
    admin.password_hash = "$2b$12$fakehash"
    admin.is_active = is_active
    return admin


class TestAdminAuthAPI:
    """Test /api/admin/v1/auth endpoints."""

    def test_login_success(self, test_client):
        from forge.infrastructure.persistence.repositories.user_repo import (
            SQLAlchemyAdminUserRepository,
        )

        with (
            patch.object(
                SQLAlchemyAdminUserRepository,
                "get_by_email",
                new_callable=AsyncMock,
                return_value=_make_admin(),
            ),
            patch.object(auth_module.pwd_context, "verify", return_value=True),
        ):
            resp = test_client.post(
                "/api/admin/v1/auth/login",
                json={"email": "admin@test.com", "password": "password123"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["access_token"]
        assert data["user"]["email"] == "admin@test.com"
        assert data["user"]["role"] == "super_admin"

    def test_login_wrong_password(self, test_client):
        from forge.infrastructure.persistence.repositories.user_repo import (
            SQLAlchemyAdminUserRepository,
        )

        with (
            patch.object(
                SQLAlchemyAdminUserRepository,
                "get_by_email",
                new_callable=AsyncMock,
                return_value=_make_admin(),
            ),
            patch.object(auth_module.pwd_context, "verify", return_value=False),
        ):
            resp = test_client.post(
                "/api/admin/v1/auth/login",
                json={"email": "admin@test.com", "password": "wrongpass"},
            )
        assert resp.status_code == 401

    def test_login_user_not_found(self, test_client):
        from forge.infrastructure.persistence.repositories.user_repo import (
            SQLAlchemyAdminUserRepository,
        )

        with patch.object(
            SQLAlchemyAdminUserRepository,
            "get_by_email",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = test_client.post(
                "/api/admin/v1/auth/login",
                json={"email": "nonexistent@test.com", "password": "whatever"},
            )
        assert resp.status_code == 401

    def test_login_disabled_account(self, test_client):
        from forge.infrastructure.persistence.repositories.user_repo import (
            SQLAlchemyAdminUserRepository,
        )

        with (
            patch.object(
                SQLAlchemyAdminUserRepository,
                "get_by_email",
                new_callable=AsyncMock,
                return_value=_make_admin(is_active=False),
            ),
            patch.object(auth_module.pwd_context, "verify", return_value=True),
        ):
            resp = test_client.post(
                "/api/admin/v1/auth/login",
                json={"email": "admin@test.com", "password": "password123"},
            )
        assert resp.status_code == 403

    def test_login_missing_fields(self, test_client):
        resp = test_client.post("/api/admin/v1/auth/login", json={})
        assert resp.status_code == 422
