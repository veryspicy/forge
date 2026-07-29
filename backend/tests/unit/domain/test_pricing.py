"""Unit tests for PricingRule, Promotion, and Pricing Engine."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from forge.domain.pricing.engine import _find_best_pricing_rule, calculate_final_price
from forge.domain.pricing.models import PricingRule, Promotion, PromotionType

# ---------------------------------------------------------------------------
# PricingRule
# ---------------------------------------------------------------------------


class TestPricingRule:
    def test_pricing_rule_create(self):
        rule = PricingRule(
            name="UAE Standard",
            region="AE",
            markup_multiplier=1.5,
            fixed_shipping_fee=10.0,
            is_default=False,
            priority=10,
        )
        assert rule.name == "UAE Standard"
        assert rule.region == "AE"
        assert rule.markup_multiplier == 1.5
        assert rule.fixed_shipping_fee == 10.0
        assert rule.is_active is True
        assert rule.is_default is False
        assert rule.priority == 10

    def test_pricing_rule_calculate_price(self):
        rule = PricingRule(name="Global", region="GLOBAL", markup_multiplier=1.4, fixed_shipping_fee=5.0)
        price = rule.calculate_price(100.0)
        assert price == 145.0  # 100 * 1.4 + 5.0

    def test_pricing_rule_deactivate(self):
        rule = PricingRule(name="Test", region="GLOBAL")
        rule.deactivate()
        assert rule.is_active is False

    def test_pricing_rule_activate(self):
        rule = PricingRule(name="Test", region="GLOBAL", is_active=False)
        rule.activate()
        assert rule.is_active is True


# ---------------------------------------------------------------------------
# Promotion
# ---------------------------------------------------------------------------


def _future_dt(days: int = 30) -> datetime:
    return datetime.now() + timedelta(days=days)


def _past_dt(days: int = 30) -> datetime:
    return datetime.now() - timedelta(days=days)


class TestPromotion:
    def test_promotion_threshold_discount(self):
        promo = Promotion(
            name="Spend 100 get 20 off",
            type=PromotionType.THRESHOLD_DISCOUNT,
            config={"threshold": 100, "discount": 20},
            start_date=_past_dt(),
            end_date=_future_dt(),
        )
        assert promo.is_valid_now() is True
        assert promo.calculate_discount(150.0) == 20.0
        assert promo.calculate_discount(50.0) == 0.0

    def test_promotion_coupon_percent(self):
        promo = Promotion(
            name="10% off coupon",
            type=PromotionType.COUPON,
            config={"discount_percent": 10},
            start_date=_past_dt(),
            end_date=_future_dt(),
        )
        assert promo.calculate_discount(200.0) == 20.0

    def test_promotion_coupon_fixed_amount(self):
        promo = Promotion(
            name="$15 off coupon",
            type=PromotionType.COUPON,
            config={"fixed_amount": 15},
            start_date=_past_dt(),
            end_date=_future_dt(),
        )
        assert promo.calculate_discount(100.0) == 15.0
        assert promo.calculate_discount(10.0) == 10.0  # capped at original price

    def test_promotion_is_valid_now(self):
        promo = Promotion(
            name="Active Promo",
            type=PromotionType.COUPON,
            config={"fixed_amount": 10},
            start_date=_past_dt(10),
            end_date=_future_dt(10),
            is_active=True,
        )
        assert promo.is_valid_now() is True

    def test_promotion_expired(self):
        promo = Promotion(
            name="Expired",
            type=PromotionType.COUPON,
            config={"fixed_amount": 10},
            start_date=_past_dt(60),
            end_date=_past_dt(1),  # ended yesterday
            is_active=True,
        )
        assert promo.is_valid_now() is False
        assert promo.calculate_discount(100.0) == 0.0

    def test_promotion_inactive(self):
        promo = Promotion(
            name="Inactive",
            type=PromotionType.COUPON,
            config={"fixed_amount": 10},
            start_date=_past_dt(10),
            end_date=_future_dt(10),
            is_active=False,
        )
        assert promo.is_valid_now() is False

    def test_member_price(self):
        promo = Promotion(
            name="VIP 15% off",
            type=PromotionType.MEMBER_PRICE,
            config={"discount_percent": 15},
            start_date=_past_dt(),
            end_date=_future_dt(),
        )
        assert promo.calculate_discount(100.0) == 15.0


# ---------------------------------------------------------------------------
# Pricing Engine
# ---------------------------------------------------------------------------


class TestPricingEngine:
    def test_engine_default_global_rule(self):
        result = calculate_final_price(cost_price=100.0, region="US", pricing_rules=[])
        assert result["base_price"] == 145.0
        assert result["final_price"] == 145.0
        assert result["applied_rule"] == "GLOBAL_DEFAULT"

    def test_engine_region_specific_rule(self):
        rule = PricingRule(name="UAE", region="AE", markup_multiplier=1.6, fixed_shipping_fee=8.0, priority=10)
        result = calculate_final_price(cost_price=100.0, region="AE", pricing_rules=[rule])
        assert result["base_price"] == 168.0
        assert result["applied_rule"] == "UAE"

    def test_engine_override_price_has_highest_priority(self):
        rule = PricingRule(name="AE", region="AE", markup_multiplier=1.6, fixed_shipping_fee=8.0)
        result = calculate_final_price(
            cost_price=100.0,
            region="AE",
            pricing_rules=[rule],
            product_override_price=200.0,
        )
        assert result["override_price"] == 200.0
        assert result["final_price"] == 200.0
        assert result["promotion_discount"] == 0.0
        assert result["applied_promotions"] == []

    def test_engine_promotion_coupon(self):
        now = datetime.now()
        promo = Promotion(
            name="$10 off",
            type=PromotionType.COUPON,
            config={"fixed_amount": 10},
            start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=30),
        )
        result = calculate_final_price(cost_price=100.0, region="US", active_promotions=[promo])
        assert result["final_price"] == 135.0  # 145 - 10
        assert result["promotion_discount"] == 10.0
        assert "$10 off" in result["applied_promotions"]

    def test_engine_threshold_discount(self):
        now = datetime.now()
        promo = Promotion(
            name="Spend 100 get 30 off",
            type=PromotionType.THRESHOLD_DISCOUNT,
            config={"threshold": 100, "discount": 30},
            start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=30),
        )
        result = calculate_final_price(cost_price=100.0, region="US", active_promotions=[promo])
        # base=145, threshold discount appplies on base (145 >= 100) -> 145-30=115
        assert result["final_price"] == 115.0
        assert result["promotion_discount"] == 30.0

    def test_engine_threshold_not_met(self):
        now = datetime.now()
        promo = Promotion(
            name="Spend 200 get 50 off",
            type=PromotionType.THRESHOLD_DISCOUNT,
            config={"threshold": 200, "discount": 50},
            start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=30),
        )
        result = calculate_final_price(cost_price=100.0, region="US", active_promotions=[promo])
        # base=145 < threshold 200, no discount
        assert result["final_price"] == 145.0
        assert result["promotion_discount"] == 0.0

    def test_engine_no_rules_returns_cost_price(self):
        result = calculate_final_price(cost_price=50.0, region="XX")
        assert result["base_price"] == 75.0  # 50*1.4+5
        assert result["final_price"] == 75.0

    def test_engine_expired_promo_ignored(self):
        now = datetime.now()
        promo = Promotion(
            name="Expired",
            type=PromotionType.COUPON,
            config={"fixed_amount": 100},
            start_date=now - timedelta(days=60),
            end_date=now - timedelta(days=1),
        )
        result = calculate_final_price(cost_price=100.0, region="US", active_promotions=[promo])
        assert result["applied_promotions"] == []
        assert result["promotion_discount"] == 0.0

    def test_engine_global_fallback_when_active_rules_inactive(self):
        rule = PricingRule(name="AE", region="AE", is_active=False)
        result = calculate_final_price(cost_price=100.0, region="AE", pricing_rules=[rule])
        assert result["applied_rule"] == "GLOBAL_DEFAULT"

    def test_engine_priority_sorts_rules(self):
        low_priority = PricingRule(name="Low", region="GLOBAL", priority=1)
        high_priority = PricingRule(name="High", region="GLOBAL", priority=100)
        # Both GLOBAL, higher priority should win
        result = calculate_final_price(
            cost_price=100.0, region="US", pricing_rules=[low_priority, high_priority]
        )
        assert result["applied_rule"] == "High"

    def test_engine_member_price_and_threshold_combined(self):
        now = datetime.now()
        member = Promotion(
            name="VIP 20%",
            type=PromotionType.MEMBER_PRICE,
            config={"discount_percent": 20},
            start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=30),
            priority=10,
        )
        threshold = Promotion(
            name="Over 100 get 10 off",
            type=PromotionType.THRESHOLD_DISCOUNT,
            config={"threshold": 100, "discount": 10},
            start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=30),
        )
        result = calculate_final_price(
            cost_price=100.0, region="US", active_promotions=[member, threshold]
        )
        # base=145, member 20% off: 145-29=116, threshold applies: 116>=100 -> 116-10=106
        assert result["final_price"] == 106.0
        assert "VIP 20%" in result["applied_promotions"]
        assert "Over 100 get 10 off" in result["applied_promotions"]


# ---------------------------------------------------------------------------
# _find_best_pricing_rule helper
# ---------------------------------------------------------------------------


class TestFindBestPricingRule:
    def test_exact_region_match_wins(self):
        global_rule = PricingRule(name="Global", region="GLOBAL", priority=10)
        ae_rule = PricingRule(name="UAE", region="AE", priority=1)
        result = _find_best_pricing_rule("AE", [global_rule, ae_rule])
        assert result.name == "UAE"

    def test_fallback_to_global(self):
        global_rule = PricingRule(name="Global", region="GLOBAL")
        result = _find_best_pricing_rule("JP", [global_rule])
        assert result.name == "Global"

    def test_no_active_rules_returns_none(self):
        inactive = PricingRule(name="Disabled", region="GLOBAL", is_active=False)
        result = _find_best_pricing_rule("US", [inactive])
        assert result is None
