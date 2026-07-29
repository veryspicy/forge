"""Unit tests for Admin Auth API (uses shared /api/v1/auth)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException, status
from uuid import uuid4

ADMIN_ID = str(uuid4())


class TestAdminAuthAPI:
    """Test /api/v1/auth endpoints (admin shares the same login endpoint)."""

    def test_login_success(self, test_client):
        mock_auth = MagicMock()
        mock_auth.login = AsyncMock(
            return_value={
                "access_token": "fake-jwt",
                "token_type": "bearer",
                "user_id": ADMIN_ID,
            }
        )
        with patch("forge.api.v1.auth.AuthService", return_value=mock_auth):
            resp = test_client.post(
                "/api/v1/auth/login",
                json={"email": "admin@test.com", "password": "password123"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["access_token"] == "fake-jwt"
        assert data["user_id"] == ADMIN_ID

    def test_login_wrong_password(self, test_client):
        mock_auth = MagicMock()
        mock_auth.login = AsyncMock(
            side_effect=HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        )
        with patch("forge.api.v1.auth.AuthService", return_value=mock_auth):
            resp = test_client.post(
                "/api/v1/auth/login",
                json={"email": "admin@test.com", "password": "wrongpass"},
            )
        assert resp.status_code == 401

    def test_login_user_not_found(self, test_client):
        mock_auth = MagicMock()
        mock_auth.login = AsyncMock(
            side_effect=HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        )
        with patch("forge.api.v1.auth.AuthService", return_value=mock_auth):
            resp = test_client.post(
                "/api/v1/auth/login",
                json={"email": "nonexistent@test.com", "password": "whatever"},
            )
        assert resp.status_code == 401

    def test_login_missing_fields(self, test_client):
        resp = test_client.post("/api/v1/auth/login", json={})
        assert resp.status_code == 422
