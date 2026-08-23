"""Unit tests for PricingService (new static API: db + dict)."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from forge.application.services.pricing_service import (
    PricingEngine,
    PricingService,
    PricingValidationError,
)
from forge.infrastructure.persistence.models import ORMPricingRule, ORMPromotion


def _make_rule(**overrides: object) -> ORMPricingRule:
    rule = ORMPricingRule(
        name=overrides.get("name", "UAE Rule"),
        region=overrides.get("region", "AE"),
        markup_multiplier=overrides.get("markup_multiplier", 1.5),
        fixed_shipping_fee=overrides.get("fixed_shipping_fee", 10.0),
        priority=overrides.get("priority", 0),
        is_active=overrides.get("is_active", True),
        is_default=overrides.get("is_default", False),
    )
    rule.id = uuid4()
    return rule


def _make_promotion(**overrides: object) -> ORMPromotion:
    now = datetime.now()
    promo = ORMPromotion(
        name=overrides.get("name", "Holiday Sale"),
        type=overrides.get("type", "COUPON"),
        config=overrides.get("config", {"amount": 20}),
        start_date=overrides.get("start_date", now - timedelta(days=1)),
        end_date=overrides.get("end_date", now + timedelta(days=30)),
        is_active=overrides.get("is_active", True),
        stackable=overrides.get("stackable", False),
        priority=overrides.get("priority", 0),
    )
    promo.id = uuid4()
    return promo


class TestPricingService:
    @pytest.mark.asyncio
    async def test_create_rule(self, mock_db_session):
        async def _fake_create(db, payload):
            rule = _make_rule(**payload)
            return rule

        with patch(
            "forge.application.services.pricing_service.SQLAlchemyPricingRuleRepository.create",
            side_effect=_fake_create,
        ):
            result = await PricingService.create_rule(
                mock_db_session,
                {"name": "UAE Rule", "region": "AE", "markup_multiplier": 1.5, "fixed_shipping_fee": 10.0},
            )
        assert result.name == "UAE Rule"
        assert result.region == "AE"
        assert result.markup_multiplier == 1.5

    @pytest.mark.asyncio
    async def test_create_rule_invalid_multiplier(self, mock_db_session):
        with pytest.raises(PricingValidationError):
            await PricingService.create_rule(
                mock_db_session,
                {"name": "Bad Rule", "markup_multiplier": 1.0},
            )

    @pytest.mark.asyncio
    async def test_create_promotion(self, mock_db_session):
        now = datetime.now()

        async def _fake_create(db, payload):
            promo = _make_promotion(**payload)
            return promo

        with patch(
            "forge.application.services.pricing_service.SQLAlchemyPromotionRepository.create",
            side_effect=_fake_create,
        ):
            result = await PricingService.create_promotion(
                mock_db_session,
                {
                    "name": "Holiday Sale",
                    "type": "COUPON",
                    "config": {"amount": 20},
                    "start_date": now,
                    "end_date": now + timedelta(days=30),
                },
            )
        assert result.name == "Holiday Sale"
        assert result.type == "COUPON"

    @pytest.mark.asyncio
    async def test_create_promotion_invalid_type(self, mock_db_session):
        with pytest.raises(PricingValidationError):
            await PricingService.create_promotion(
                mock_db_session,
                {"name": "Bad Promo", "type": "UNKNOWN"},
            )


class TestPricingEngine:
    @pytest.mark.asyncio
    async def test_calculate_with_region_rule(self, mock_db_session):
        rule = _make_rule(name="UAE Rule", region="AE", markup_multiplier=1.5, fixed_shipping_fee=10.0)
        with (
            patch(
                "forge.application.services.pricing_service.SQLAlchemyPricingRuleRepository.list_rules",
                new_callable=AsyncMock,
                return_value=[rule],
            ),
            patch(
                "forge.application.services.pricing_service.SQLAlchemyPromotionRepository.list_promotions",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            result = await PricingEngine.calculate(mock_db_session, region="AE", cost_price=100.0)
        assert result["final_price"] == 150.0
        assert result["applied_rule"] == "UAE Rule"
        assert result["shipping_fee"] == 10.0

    @pytest.mark.asyncio
    async def test_calculate_manual_override_wins(self, mock_db_session):
        rule = _make_rule(name="US Rule", region="US", markup_multiplier=2.0)
        with (
            patch(
                "forge.application.services.pricing_service.SQLAlchemyPricingRuleRepository.list_rules",
                new_callable=AsyncMock,
                return_value=[rule],
            ),
            patch(
                "forge.application.services.pricing_service.SQLAlchemyPromotionRepository.list_promotions",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            result = await PricingEngine.calculate(mock_db_session, region="US", cost_price=100.0, override_price=88.0)
        assert result["final_price"] == 88.0
        assert result["applied_rule"] == "manual_override"

    @pytest.mark.asyncio
    async def test_calculate_promotion_applies(self, mock_db_session):
        rule = _make_rule(name="Global", region="GLOBAL", markup_multiplier=1.4)
        promo = _make_promotion(name="Sale", type="COUPON", config={"amount": 20})
        with (
            patch(
                "forge.application.services.pricing_service.SQLAlchemyPricingRuleRepository.list_rules",
                new_callable=AsyncMock,
                return_value=[rule],
            ),
            patch(
                "forge.application.services.pricing_service.SQLAlchemyPromotionRepository.list_promotions",
                new_callable=AsyncMock,
                return_value=[promo],
            ),
        ):
            result = await PricingEngine.calculate(mock_db_session, region="US", cost_price=100.0)
        assert result["final_price"] == 80.0
        assert result["applied_rule"] == "promotion:Sale"

    @pytest.mark.asyncio
    async def test_calculate_no_rule_raises(self, mock_db_session):
        with (
            patch(
                "forge.application.services.pricing_service.SQLAlchemyPricingRuleRepository.list_rules",
                new_callable=AsyncMock,
                return_value=[],
            ),
            pytest.raises(PricingValidationError),
        ):
            await PricingEngine.calculate(mock_db_session, region="US", cost_price=100.0)
