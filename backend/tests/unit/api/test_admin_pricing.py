"""Unit tests for Admin Pricing API."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from forge.main import dependencies

RULE_ID = str(uuid4())
PROMO_ID = str(uuid4())


def _setup_auth(test_client):
    async def _fake_get_db():
        yield AsyncMock()
    async def _fake_user_id():
        from uuid import UUID
        return UUID("d290f1ee-6c54-4b01-90e6-d701748f0851")
    test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
    test_client.app.dependency_overrides[dependencies.get_current_user_id] = _fake_user_id


class TestAdminPricingAPI:
    """Test /api/admin/v1/pricing endpoints."""

    def _mock_service(self, test_client):
        from forge.api.admin.v1 import pricing as mod
        svc = MagicMock()
        _setup_auth(test_client)
        test_client.app.dependency_overrides[mod.get_pricing_service] = lambda: svc
        return svc

    # ---- Rules CRUD ----
    def test_list_rules_success(self, test_client):
        svc = self._mock_service(test_client)
        svc.list_rules = AsyncMock(return_value=[])
        try:
            resp = test_client.get("/api/admin/v1/pricing/rules")
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200

    def test_create_rule_success(self, test_client):
        svc = self._mock_service(test_client)
        svc.create_rule = AsyncMock(
            return_value=MagicMock(model_dump=lambda: {"id": RULE_ID, "region": "AE", "markup_multiplier": 1.5})
        )
        try:
            resp = test_client.post(
                "/api/admin/v1/pricing/rules",
                json={"name": "Test Rule", "region": "AE", "markup_multiplier": 1.5, "fixed_shipping_fee": 10.0},
            )
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 201

    def test_create_rule_validation_error(self, test_client):
        self._mock_service(test_client)
        try:
            resp = test_client.post("/api/admin/v1/pricing/rules", json={})
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 422

    def test_update_rule_success(self, test_client):
        svc = self._mock_service(test_client)
        svc.update_rule = AsyncMock(
            return_value=MagicMock(model_dump=lambda: {"id": RULE_ID, "region": "AE", "markup_multiplier": 2.0})
        )
        try:
            resp = test_client.patch(
                f"/api/admin/v1/pricing/rules/{RULE_ID}",
                json={"markup_multiplier": 2.0},
            )
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200

    def test_update_rule_not_found(self, test_client):
        svc = self._mock_service(test_client)
        svc.update_rule = AsyncMock(return_value=None)
        try:
            resp = test_client.patch(
                f"/api/admin/v1/pricing/rules/{RULE_ID}",
                json={"markup_multiplier": 2.0},
            )
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 404

    def test_delete_rule_success(self, test_client):
        svc = self._mock_service(test_client)
        svc.delete_rule = AsyncMock(return_value=True)
        try:
            resp = test_client.delete(f"/api/admin/v1/pricing/rules/{RULE_ID}")
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 204

    def test_delete_rule_not_found(self, test_client):
        svc = self._mock_service(test_client)
        svc.delete_rule = AsyncMock(return_value=False)
        try:
            resp = test_client.delete(f"/api/admin/v1/pricing/rules/{RULE_ID}")
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 404

    # ---- Promotions CRUD ----
    def test_list_promotions_success(self, test_client):
        svc = self._mock_service(test_client)
        svc.list_promotions = AsyncMock(return_value=[])
        try:
            resp = test_client.get("/api/admin/v1/pricing/promotions")
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200

    def test_create_promotion_success(self, test_client):
        svc = self._mock_service(test_client)
        svc.create_promotion = AsyncMock(
            return_value=MagicMock(model_dump=lambda: {"id": PROMO_ID, "name": "Sale"})
        )
        try:
            resp = test_client.post(
                "/api/admin/v1/pricing/promotions",
                json={"name": "Summer Sale", "type": "COUPON","config": {"discount_percent": 10.0},
                      "start_date": "2024-01-01T00:00:00Z", "end_date": "2025-01-01T00:00:00Z"},
            )
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 201

    def test_update_promotion_success(self, test_client):
        svc = self._mock_service(test_client)
        svc.update_promotion = AsyncMock(
            return_value=MagicMock(model_dump=lambda: {"id": PROMO_ID, "name": "Updated"})
        )
        try:
            resp = test_client.patch(
                f"/api/admin/v1/pricing/promotions/{PROMO_ID}",
                json={"name": "Updated Sale"},
            )
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200

    def test_delete_promotion_success(self, test_client):
        svc = self._mock_service(test_client)
        svc.delete_promotion = AsyncMock(return_value=True)
        try:
            resp = test_client.delete(f"/api/admin/v1/pricing/promotions/{PROMO_ID}")
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 204

    def test_delete_promotion_not_found(self, test_client):
        svc = self._mock_service(test_client)
        svc.delete_promotion = AsyncMock(return_value=False)
        try:
            resp = test_client.delete(f"/api/admin/v1/pricing/promotions/{PROMO_ID}")
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 404

    # ---- Calculate ----
    def test_calculate_price_success(self, test_client):
        svc = self._mock_service(test_client)
        svc.calculate_price = AsyncMock(
            return_value=MagicMock(model_dump=lambda: {"final_price": 15.0, "region": "AE", "cost_price": 10.0})
        )
        try:
            resp = test_client.get(f"/api/admin/v1/pricing/calculate?cost_price=10&region=AE")
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200

    def test_pricing_unauthorized(self, test_client):
        resp = test_client.get("/api/admin/v1/pricing/rules")
        assert resp.status_code == 401

    def test_pricing_forbidden_no_role(self, test_client):
        """非 ADMIN/OPERATOR 角色访问定价接口 → 403"""
        from fastapi import HTTPException

        async def _fake_user_id_403():
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        test_client.app.dependency_overrides[dependencies.get_current_user_id] = _fake_user_id_403
        try:
            resp = test_client.get("/api/admin/v1/pricing/rules")
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 403
