"""Unit tests for Admin Pricing API (new static-service architecture)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

from forge.main import dependencies

RULE_ID = str(uuid4())
PROMO_ID = str(uuid4())


def _setup_auth(test_client):
    async def _fake_get_db():
        yield AsyncMock()

    async def _fake_admin():
        return {"id": UUID("d290f1ee-6c54-4b01-90e6-d701748f0851"), "role": "super_admin", "roles": ["super_admin"]}

    test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
    test_client.app.dependency_overrides[dependencies.get_current_admin] = _fake_admin


def _make_rule(region="AE", multiplier=1.5):
    rule = MagicMock()
    rule.to_dict.return_value = {
        "id": RULE_ID,
        "name": "Test Rule",
        "region": region,
        "markup_multiplier": multiplier,
        "fixed_shipping_fee": 10.0,
    }
    return rule


def _make_promo(name="Sale"):
    promo = MagicMock()
    promo.to_dict.return_value = {
        "id": PROMO_ID,
        "name": name,
        "type": "COUPON",
        "config": {"discount_percent": 10.0},
        "is_active": True,
    }
    return promo


class TestAdminPricingAPI:
    """Test /api/admin/v1/pricing endpoints."""

    # ---- Rules CRUD ----
    def test_list_rules_success(self, test_client):
        from forge.infrastructure.persistence.repositories.pricing_repo import (
            SQLAlchemyPricingRuleRepository,
        )

        _setup_auth(test_client)
        with patch.object(
            SQLAlchemyPricingRuleRepository,
            "list_rules",
            new_callable=AsyncMock,
            return_value=[_make_rule()],
        ):
            resp = test_client.get("/api/admin/v1/pricing/rules")
        test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_create_rule_success(self, test_client):
        from forge.application.services.pricing_service import PricingService

        _setup_auth(test_client)
        with patch.object(
            PricingService,
            "create_rule",
            new_callable=AsyncMock,
            return_value=_make_rule(multiplier=1.5),
        ):
            resp = test_client.post(
                "/api/admin/v1/pricing/rules",
                json={"name": "Test Rule", "region": "AE", "markup_multiplier": 1.5, "fixed_shipping_fee": 10.0},
            )
        test_client.app.dependency_overrides.clear()
        assert resp.status_code == 201
        assert resp.json()["data"]["region"] == "AE"

    def test_create_rule_validation_error(self, test_client):
        _setup_auth(test_client)
        try:
            resp = test_client.post("/api/admin/v1/pricing/rules", json={})
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 422

    def test_update_rule_success(self, test_client):
        from forge.application.services.pricing_service import PricingService
        from forge.infrastructure.persistence.repositories.pricing_repo import (
            SQLAlchemyPricingRuleRepository,
        )

        _setup_auth(test_client)
        with (
            patch.object(
                SQLAlchemyPricingRuleRepository,
                "get_by_id",
                new_callable=AsyncMock,
                return_value=_make_rule(),
            ),
            patch.object(
                PricingService,
                "update_rule",
                new_callable=AsyncMock,
                return_value=_make_rule(multiplier=2.0),
            ),
        ):
            resp = test_client.patch(
                f"/api/admin/v1/pricing/rules/{RULE_ID}",
                json={"markup_multiplier": 2.0},
            )
        test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert resp.json()["data"]["markup_multiplier"] == 2.0

    def test_update_rule_not_found(self, test_client):
        from forge.infrastructure.persistence.repositories.pricing_repo import (
            SQLAlchemyPricingRuleRepository,
        )

        _setup_auth(test_client)
        with patch.object(SQLAlchemyPricingRuleRepository, "get_by_id", new_callable=AsyncMock, return_value=None):
            resp = test_client.patch(
                f"/api/admin/v1/pricing/rules/{RULE_ID}",
                json={"markup_multiplier": 2.0},
            )
        test_client.app.dependency_overrides.clear()
        assert resp.status_code == 404

    def test_delete_rule_success(self, test_client):
        from forge.infrastructure.persistence.repositories.pricing_repo import (
            SQLAlchemyPricingRuleRepository,
        )

        _setup_auth(test_client)
        with (
            patch.object(
                SQLAlchemyPricingRuleRepository,
                "get_by_id",
                new_callable=AsyncMock,
                return_value=_make_rule(),
            ),
            patch.object(SQLAlchemyPricingRuleRepository, "delete", new_callable=AsyncMock),
        ):
            resp = test_client.delete(f"/api/admin/v1/pricing/rules/{RULE_ID}")
        test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert resp.json()["data"]["deleted"] is True

    def test_delete_rule_not_found(self, test_client):
        from forge.infrastructure.persistence.repositories.pricing_repo import (
            SQLAlchemyPricingRuleRepository,
        )

        _setup_auth(test_client)
        with patch.object(SQLAlchemyPricingRuleRepository, "get_by_id", new_callable=AsyncMock, return_value=None):
            resp = test_client.delete(f"/api/admin/v1/pricing/rules/{RULE_ID}")
        test_client.app.dependency_overrides.clear()
        assert resp.status_code == 404

    # ---- Promotions CRUD ----
    def test_list_promotions_success(self, test_client):
        from forge.infrastructure.persistence.repositories.pricing_repo import (
            SQLAlchemyPromotionRepository,
        )

        _setup_auth(test_client)
        with patch.object(
            SQLAlchemyPromotionRepository,
            "list_promotions",
            new_callable=AsyncMock,
            return_value=[_make_promo()],
        ):
            resp = test_client.get("/api/admin/v1/pricing/promotions")
        test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_create_promotion_success(self, test_client):
        from forge.application.services.pricing_service import PricingService

        _setup_auth(test_client)
        with patch.object(
            PricingService,
            "create_promotion",
            new_callable=AsyncMock,
            return_value=_make_promo(name="Summer Sale"),
        ):
            resp = test_client.post(
                "/api/admin/v1/pricing/promotions",
                json={
                    "name": "Summer Sale",
                    "type": "COUPON",
                    "config": {"discount_percent": 10.0},
                    "start_date": "2024-01-01T00:00:00Z",
                    "end_date": "2025-01-01T00:00:00Z",
                },
            )
        test_client.app.dependency_overrides.clear()
        assert resp.status_code == 201
        assert resp.json()["data"]["name"] == "Summer Sale"

    def test_update_promotion_success(self, test_client):
        from forge.application.services.pricing_service import PricingService
        from forge.infrastructure.persistence.repositories.pricing_repo import (
            SQLAlchemyPromotionRepository,
        )

        _setup_auth(test_client)
        with (
            patch.object(
                SQLAlchemyPromotionRepository,
                "get_by_id",
                new_callable=AsyncMock,
                return_value=_make_promo(),
            ),
            patch.object(
                PricingService,
                "update_promotion",
                new_callable=AsyncMock,
                return_value=_make_promo(name="Updated"),
            ),
        ):
            resp = test_client.patch(
                f"/api/admin/v1/pricing/promotions/{PROMO_ID}",
                json={"name": "Updated Sale"},
            )
        test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "Updated"

    def test_delete_promotion_success(self, test_client):
        from forge.infrastructure.persistence.repositories.pricing_repo import (
            SQLAlchemyPromotionRepository,
        )

        _setup_auth(test_client)
        with (
            patch.object(
                SQLAlchemyPromotionRepository,
                "get_by_id",
                new_callable=AsyncMock,
                return_value=_make_promo(),
            ),
            patch.object(SQLAlchemyPromotionRepository, "delete", new_callable=AsyncMock),
        ):
            resp = test_client.delete(f"/api/admin/v1/pricing/promotions/{PROMO_ID}")
        test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert resp.json()["data"]["deleted"] is True

    def test_delete_promotion_not_found(self, test_client):
        from forge.infrastructure.persistence.repositories.pricing_repo import (
            SQLAlchemyPromotionRepository,
        )

        _setup_auth(test_client)
        with patch.object(SQLAlchemyPromotionRepository, "get_by_id", new_callable=AsyncMock, return_value=None):
            resp = test_client.delete(f"/api/admin/v1/pricing/promotions/{PROMO_ID}")
        test_client.app.dependency_overrides.clear()
        assert resp.status_code == 404

    # ---- Calculate ----
    def test_calculate_price_success(self, test_client):
        from forge.application.services.pricing_service import PricingEngine

        _setup_auth(test_client)
        with patch.object(
            PricingEngine,
            "calculate",
            new_callable=AsyncMock,
            return_value={"final_price": 15.0, "region": "AE", "cost_price": 10.0},
        ):
            resp = test_client.get("/api/admin/v1/pricing/calculate?cost_price=10&region=AE")
        test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert resp.json()["data"]["final_price"] == 15.0

    def test_pricing_unauthorized(self, test_client):
        resp = test_client.get("/api/admin/v1/pricing/rules")
        assert resp.status_code == 401

    def test_pricing_forbidden_no_role(self, test_client):
        """非 ADMIN/OPERATOR 角色访问定价接口 → 403"""
        from fastapi import HTTPException

        async def _fake_admin_403():
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        test_client.app.dependency_overrides[dependencies.get_current_admin] = _fake_admin_403
        try:
            resp = test_client.get("/api/admin/v1/pricing/rules")
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 403
