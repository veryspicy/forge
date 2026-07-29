"""Unit tests for Admin Dashboard API."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from forge.main import dependencies

FAKE_ADMIN_ID = "d290f1ee-6c54-4b01-90e6-d701748f0851"


@pytest.fixture
def fake_db_session():
    """Provide a mock AsyncSession for get_db override."""
    return AsyncMock()


@pytest.fixture
def override_auth(test_client, fake_db_session):
    """Override auth dependencies for admin tests."""

    async def _fake_get_db():
        yield fake_db_session

    async def _fake_user_id():
        return UUID(FAKE_ADMIN_ID)

    test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
    test_client.app.dependency_overrides[dependencies.get_current_user_id] = _fake_user_id

    yield

    test_client.app.dependency_overrides.clear()


class TestDashboardAPI:
    """Test /api/admin/v1/dashboard endpoint."""

    def test_get_dashboard_success(self, test_client, fake_db_session, override_auth):
        """Normal path: authenticated admin gets dashboard stats."""
        from forge.infrastructure.persistence.models import (
            ORMOrder,
            ORMProduct,
            SupplierModel,
            ORMConversation,
        )

        mock_result_orders = MagicMock()
        mock_result_orders.one.return_value = MagicMock(cnt=5, gmv=Decimal("1250.00"))

        mock_result_pending = MagicMock()
        mock_result_pending.scalar_one.return_value = 3

        mock_result_active = MagicMock()
        mock_result_active.scalar_one.return_value = 42

        mock_result_errors = MagicMock()
        mock_result_errors.scalar_one.return_value = 1

        mock_result_suppliers = MagicMock()
        mock_result_suppliers.scalar_one.return_value = 7

        mock_result_probe = MagicMock()
        mock_result_probe.scalar_one.return_value = 18

        mock_result_total_probes = MagicMock()
        mock_result_total_probes.scalar_one.return_value = 10

        mock_result_adopted = MagicMock()
        mock_result_adopted.scalar_one.return_value = 6

        fake_db_session.execute.side_effect = [
            mock_result_orders,
            mock_result_pending,
            mock_result_active,
            mock_result_errors,
            mock_result_suppliers,
            mock_result_probe,
            mock_result_total_probes,
            mock_result_adopted,
        ]

        response = test_client.get("/api/admin/v1/dashboard")

        assert response.status_code == 200
        data = response.json()
        assert data["today_orders"] == 5
        assert float(data["today_gmv"]) == 1250.00
        assert data["pending_orders"] == 3
        assert data["active_products"] == 42
        assert data["procurement_errors"] == 1
        assert data["total_suppliers"] == 7
        assert data["today_probe_requests"] == 18

    def test_get_dashboard_zeros(self, test_client, fake_db_session, override_auth):
        """Dashboard returns zeros when no data exists."""
        mock_result_orders = MagicMock()
        mock_result_orders.one.return_value = MagicMock(cnt=0, gmv=Decimal("0.00"))

        mock_zero = MagicMock()
        mock_zero.scalar_one.return_value = 0

        fake_db_session.execute.side_effect = [mock_result_orders] + [mock_zero] * 7

        response = test_client.get("/api/admin/v1/dashboard")

        assert response.status_code == 200
        data = response.json()
        assert data["today_orders"] == 0
        assert data["today_gmv"] == 0.0

    def test_get_dashboard_unauthorized(self, test_client):
        """No auth header returns 401."""
        response = test_client.get("/api/admin/v1/dashboard")
        assert response.status_code == 401
