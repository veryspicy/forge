"""Unit tests for Admin Dashboard API (simplified repo-count implementation)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import UUID

from forge.main import dependencies

FAKE_ADMIN_ID = "d290f1ee-6c54-4b01-90e6-d701748f0851"


def _setup_auth(test_client):
    async def _fake_get_db():
        yield AsyncMock()

    async def _fake_admin():
        return {"id": UUID(FAKE_ADMIN_ID), "role": "super_admin", "roles": ["super_admin"]}

    test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
    test_client.app.dependency_overrides[dependencies.get_current_admin] = _fake_admin


class TestDashboardAPI:
    """Test /api/admin/v1/dashboard endpoint."""

    def test_get_dashboard_success(self, test_client):
        from forge.infrastructure.persistence.repositories.order_repo import SQLAlchemyOrderRepository
        from forge.infrastructure.persistence.repositories.product_repo import SQLAlchemyProductRepository
        from forge.infrastructure.persistence.repositories.user_repo import SQLAlchemyUserRepository

        _setup_auth(test_client)
        with (
            patch.object(SQLAlchemyUserRepository, "count", new_callable=AsyncMock, return_value=12),
            patch.object(SQLAlchemyProductRepository, "count", new_callable=AsyncMock, return_value=42),
            patch.object(SQLAlchemyOrderRepository, "count", new_callable=AsyncMock, return_value=5),
            patch.object(
                SQLAlchemyOrderRepository,
                "count_by_status",
                new_callable=AsyncMock,
                return_value={"PENDING": 2, "COMPLETED": 3},
            ),
        ):
            response = test_client.get("/api/admin/v1/dashboard")
        test_client.app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["total_orders"] == 5
        assert data["total_users"] == 12
        assert data["total_products"] == 42
        assert data["order_status"]["PENDING"] == 2
        assert data["order_trend"] == []

    def test_get_dashboard_zeros(self, test_client):
        from forge.infrastructure.persistence.repositories.order_repo import SQLAlchemyOrderRepository
        from forge.infrastructure.persistence.repositories.product_repo import SQLAlchemyProductRepository
        from forge.infrastructure.persistence.repositories.user_repo import SQLAlchemyUserRepository

        _setup_auth(test_client)
        with (
            patch.object(SQLAlchemyUserRepository, "count", new_callable=AsyncMock, return_value=0),
            patch.object(SQLAlchemyProductRepository, "count", new_callable=AsyncMock, return_value=0),
            patch.object(SQLAlchemyOrderRepository, "count", new_callable=AsyncMock, return_value=0),
            patch.object(SQLAlchemyOrderRepository, "count_by_status", new_callable=AsyncMock, return_value={}),
        ):
            response = test_client.get("/api/admin/v1/dashboard")
        test_client.app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["total_orders"] == 0
        assert data["total_users"] == 0
        assert data["total_products"] == 0

    def test_get_dashboard_unauthorized(self, test_client):
        """No auth header returns 401."""
        response = test_client.get("/api/admin/v1/dashboard")
        assert response.status_code == 401

    def test_get_dashboard_forbidden_no_role(self, test_client):
        """普通用户无后台角色访问 Dashboard → 403"""
        from fastapi import HTTPException

        async def _fake_admin_403():
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        test_client.app.dependency_overrides[dependencies.get_current_admin] = _fake_admin_403
        try:
            response = test_client.get("/api/admin/v1/dashboard")
        finally:
            test_client.app.dependency_overrides.clear()
        assert response.status_code == 403
