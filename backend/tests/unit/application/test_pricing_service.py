"""Unit tests for PricingService (mock repositories)."""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from forge.application.dtos.pricing_dtos import PricingRuleCreateDTO, PromotionCreateDTO
from forge.application.services.pricing_service import PricingService
from forge.domain.pricing.models import PricingRule, Promotion, PromotionType


@pytest.fixture
def pricing_service(mock_pricing_rule_repo, mock_promotion_repo):
    return PricingService(rule_repo=mock_pricing_rule_repo, promotion_repo=mock_promotion_repo)


class TestPricingService:
    @pytest.mark.asyncio
    async def test_create_pricing_rule(self, pricing_service, mock_pricing_rule_repo):
        dto = PricingRuleCreateDTO(
            name="UAE Rule",
            region="AE",
            markup_multiplier=1.5,
            fixed_shipping_fee=10.0,
        )

        async def _fake_save(rule):
            rule.id = uuid4()
            return rule

        mock_pricing_rule_repo.save.side_effect = _fake_save

        result = await pricing_service.create_rule(dto)
        assert result.name == "UAE Rule"
        assert result.region == "AE"
        assert result.markup_multiplier == 1.5
        mock_pricing_rule_repo.save.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_calculate_price_for_product(self, pricing_service, mock_pricing_rule_repo, mock_promotion_repo):
        rule = PricingRule(name="Global", region="GLOBAL", markup_multiplier=1.4, fixed_shipping_fee=5.0)
        mock_pricing_rule_repo.list_active_rules.return_value = [rule]
        mock_promotion_repo.list_active.return_value = []

        result = await pricing_service.calculate_price(cost_price=100.0, region="US")
        assert result.final_price == 145.0
        assert result.applied_rule == "Global"

    @pytest.mark.asyncio
    async def test_create_promotion(self, pricing_service, mock_promotion_repo):
        now = datetime.now()
        dto = PromotionCreateDTO(
            name="Holiday Sale",
            type="COUPON",
            config={"fixed_amount": 20},
            start_date=now,
            end_date=now + timedelta(days=30),
        )

        async def _fake_save(promo):
            promo.id = uuid4()
            return promo

        mock_promotion_repo.save.side_effect = _fake_save

        result = await pricing_service.create_promotion(dto)
        assert result.name == "Holiday Sale"
        assert result.type == "COUPON"
        mock_promotion_repo.save.assert_awaited_once()
