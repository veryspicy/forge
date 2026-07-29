"""Unit tests for Pricing API endpoints."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException


FAKE_USER_ID = "d290f1ee-6c54-4b01-90e6-d701748f0851"


class TestPricingAPI:
    @patch("forge.main.dependencies.get_db")
    @patch("forge.main.dependencies.get_current_user_id")
    def test_get_pricing_rules(self, mock_user, mock_db, test_client):
        mock_user.return_value = FAKE_USER_ID
        mock_db.return_value = AsyncMock()

        from forge.domain.pricing.models import PricingRule
        from forge.infrastructure.persistence.repositories.pricing_repo import (
            SQLAlchemyPricingRuleRepository,
        )

        rule = PricingRule(
            name="UAE Standard",
            region="AE",
            markup_multiplier=Decimal("1.5"),
            fixed_shipping_fee=Decimal("10.0"),
        )
        rule.id = uuid4()

        with patch.object(
            SQLAlchemyPricingRuleRepository, "list_all", new_callable=AsyncMock
        ) as mock_list:
            mock_list.return_value = [rule]
            response = test_client.get("/api/v1/pricing/rules")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["name"] == "UAE Standard"

    def test_create_pricing_rule(self, test_client):
        from forge.main import dependencies
        from forge.infrastructure.persistence.repositories.pricing_repo import (
            SQLAlchemyPricingRuleRepository,
        )

        async def _fake_get_db():
            yield AsyncMock()

        async def _fake_user_id():
            from uuid import UUID
            return UUID(FAKE_USER_ID)

        test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
        test_client.app.dependency_overrides[dependencies.get_current_user_id] = _fake_user_id

        async def _fake_role(_=None):
            return "admin-001"

        test_client.app.dependency_overrides[
            dependencies.require_role
        ] = _fake_role

        try:
            with patch.object(
                SQLAlchemyPricingRuleRepository,
                "save",
                new_callable=AsyncMock,
            ) as mock_save:

                async def _fake_save(rule):
                    rule.id = uuid4()
                    return rule

                mock_save.side_effect = _fake_save

                payload = {
                    "name": "EU Rule",
                    "region": "EU",
                    "markup_multiplier": 1.2,
                    "fixed_shipping_fee": 5.0,
                    "priority": 5,
                }
                response = test_client.post(
                    "/api/v1/pricing/rules", json=payload
                )

            assert response.status_code == 201
            data = response.json()
            assert data["name"] == "EU Rule"
        finally:
            test_client.app.dependency_overrides.clear()

    @patch("forge.main.dependencies.get_db")
    @patch("forge.main.dependencies.get_current_user_id")
    def test_calculate_endpoint(self, mock_user, mock_db, test_client):
        mock_user.return_value = FAKE_USER_ID
        mock_db.return_value = AsyncMock()

        from forge.application.services.pricing_service import PricingService

        mock_result = MagicMock()
        mock_result.final_price = Decimal("145.00")
        mock_result.base_price = Decimal("140.00")
        mock_result.applied_rule = "GLOBAL_DEFAULT"
        mock_result.override_price = None
        mock_result.promotion_discount = Decimal("0.00")
        mock_result.applied_promotions = []

        with patch.object(
            PricingService, "calculate_price", new_callable=AsyncMock
        ) as mock_calc:
            mock_calc.return_value = mock_result

            response = test_client.get(
                "/api/v1/pricing/calculate?cost_price=100.0&region=US"
            )

        assert response.status_code == 200
        data = response.json()
        assert float(data["final_price"]) == 145.00

    def test_create_pricing_rule_validation_error(self, test_client):
        """Missing required fields returns 422."""
        from forge.main import dependencies

        async def _fake_get_db():
            yield AsyncMock()

        async def _fake_user_id():
            from uuid import UUID
            return UUID(FAKE_USER_ID)

        test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
        test_client.app.dependency_overrides[dependencies.get_current_user_id] = _fake_user_id

        try:
            payload = {}  # empty
            response = test_client.post("/api/v1/pricing/rules", json=payload)
        finally:
            test_client.app.dependency_overrides.clear()

        assert response.status_code == 422
