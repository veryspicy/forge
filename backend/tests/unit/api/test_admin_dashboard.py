"""Unit tests for Admin Dashboard API (aggregated dashboard stats)."""

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
        from forge.infrastructure.persistence.repositories.supplier_repo import SQLAlchemySupplierRepository
        from forge.infrastructure.persistence.repositories.user_repo import SQLAlchemyUserRepository

        order_stats = {
            "total_orders": 5,
            "total_revenue": 1280.5,
            "today_orders": 2,
            "today_gmv": 199.0,
            "pending_orders": 1,
            "procurement_errors": 0,
            "status_counts": {"pending": 2, "delivered": 3},
            "order_trend": {"dates": ["9/9", "9/10"], "counts": [1, 2]},
        }

        _setup_auth(test_client)
        with (
            patch.object(SQLAlchemyUserRepository, "count", new_callable=AsyncMock, return_value=12),
            patch.object(SQLAlchemyProductRepository, "count", new_callable=AsyncMock, return_value=42),
            patch.object(SQLAlchemyProductRepository, "count_active", new_callable=AsyncMock, return_value=30),
            patch.object(
                SQLAlchemyProductRepository,
                "category_distribution",
                new_callable=AsyncMock,
                return_value=[{"name": "toys", "value": 30}],
            ),
            patch.object(SQLAlchemySupplierRepository, "count", new_callable=AsyncMock, return_value=4),
            patch.object(
                SQLAlchemyOrderRepository,
                "dashboard_stats",
                new_callable=AsyncMock,
                return_value=order_stats,
            ),
        ):
            response = test_client.get("/api/admin/v1/dashboard")
        test_client.app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        # 兼容旧字段
        assert data["total_orders"] == 5
        assert data["total_users"] == 12
        assert data["total_products"] == 42
        assert data["order_status"]["pending"] == 2
        # 统计卡字段（前端 dashboard 契约）
        assert data["today_orders"] == 2
        assert data["today_gmv"] == 199.0
        assert data["active_products"] == 30
        assert data["pending_orders"] == 1
        assert data["total_suppliers"] == 4
        assert data["probe_adoption_rate"] == 0
        assert data["today_probe_requests"] == 0
        # 图表字段
        assert data["product_categories"] == [{"name": "toys", "value": 30}]
        assert data["order_trend"]["counts"] == [1, 2]

    def test_get_dashboard_zeros(self, test_client):
        from forge.infrastructure.persistence.repositories.order_repo import SQLAlchemyOrderRepository
        from forge.infrastructure.persistence.repositories.product_repo import SQLAlchemyProductRepository
        from forge.infrastructure.persistence.repositories.supplier_repo import SQLAlchemySupplierRepository
        from forge.infrastructure.persistence.repositories.user_repo import SQLAlchemyUserRepository

        empty_stats = {
            "total_orders": 0,
            "total_revenue": 0.0,
            "today_orders": 0,
            "today_gmv": 0.0,
            "pending_orders": 0,
            "procurement_errors": 0,
            "status_counts": {},
            "order_trend": {"dates": [], "counts": []},
        }

        _setup_auth(test_client)
        with (
            patch.object(SQLAlchemyUserRepository, "count", new_callable=AsyncMock, return_value=0),
            patch.object(SQLAlchemyProductRepository, "count", new_callable=AsyncMock, return_value=0),
            patch.object(SQLAlchemyProductRepository, "count_active", new_callable=AsyncMock, return_value=0),
            patch.object(
                SQLAlchemyProductRepository,
                "category_distribution",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch.object(SQLAlchemySupplierRepository, "count", new_callable=AsyncMock, return_value=0),
            patch.object(
                SQLAlchemyOrderRepository,
                "dashboard_stats",
                new_callable=AsyncMock,
                return_value=empty_stats,
            ),
        ):
            response = test_client.get("/api/admin/v1/dashboard")
        test_client.app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["total_orders"] == 0
        assert data["total_users"] == 0
        assert data["total_products"] == 0
        assert data["today_orders"] == 0
        assert data["today_gmv"] == 0.0
        assert data["product_categories"] == []

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
