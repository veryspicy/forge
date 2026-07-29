"""Unit tests for Admin router."""

from __future__ import annotations

import pytest


class TestAdminRouter:
    def test_admin_health_no_auth_required(self, test_client):
        response = test_client.get("/api/admin/v1/health")
        assert response.status_code == 404

    def test_admin_dashboard_public_currently(self, test_client):
        """Dashboard now requires authentication."""
        response = test_client.get("/api/admin/v1/dashboard")
        assert response.status_code == 401
