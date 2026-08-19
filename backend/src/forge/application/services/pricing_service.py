"""Pricing — Application Service（PricingRule + Promotion + PricingEngine）。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from forge.infrastructure.persistence.models import ORMPricingRule, ORMPromotion
from forge.infrastructure.persistence.repositories.pricing_repo import (
    SQLAlchemyPricingRuleRepository,
    SQLAlchemyPromotionRepository,
)

VALID_PROMO_TYPES = {"COUPON", "DISCOUNT", "BUNDLE"}


class PricingValidationError(ValueError):
    """业务校验失败，携带字段级错误明细。"""

    def __init__(self, message: str, errors: dict[str, str] | None = None):
        super().__init__(message)
        self.errors = errors or {}


class PricingRuleNotFoundError(ValueError):
    pass


class PromotionNotFoundError(ValueError):
    pass


class PricingService:
    """定价规则与促销活动业务规则层。"""

    # ---------- PricingRule ----------

    @staticmethod
    async def create_rule(db: AsyncSession, data: dict[str, Any]) -> ORMPricingRule:
        errors = PricingService._validate_rule(data)
        if errors:
            raise PricingValidationError("定价规则参数校验失败", errors)

        payload = dict(data)
        payload.setdefault("region", "GLOBAL")
        payload.setdefault("markup_multiplier", 1.4)
        payload.setdefault("fixed_shipping_fee", 0.0)
        payload.setdefault("priority", 0)
        payload.setdefault("is_active", True)
        payload.setdefault("is_default", False)
        return await SQLAlchemyPricingRuleRepository.create(db, payload)

    @staticmethod
    async def update_rule(db: AsyncSession, rule: ORMPricingRule, data: dict[str, Any]) -> ORMPricingRule:
        errors = PricingService._validate_rule(data, partial=True)
        if errors:
            raise PricingValidationError("定价规则参数校验失败", errors)
        return await SQLAlchemyPricingRuleRepository.update(db, rule, data)

    # ---------- Promotion ----------

    @staticmethod
    async def create_promotion(db: AsyncSession, data: dict[str, Any]) -> ORMPromotion:
        errors = PricingService._validate_promotion(data)
        if errors:
            raise PricingValidationError("促销活动参数校验失败", errors)

        payload = dict(data)
        payload.setdefault("type", "COUPON")
        payload.setdefault("is_active", True)
        payload.setdefault("stackable", False)
        payload.setdefault("priority", 0)
        payload.setdefault("config", {})
        return await SQLAlchemyPromotionRepository.create(db, payload)

    @staticmethod
    async def update_promotion(db: AsyncSession, promo: ORMPromotion, data: dict[str, Any]) -> ORMPromotion:
        errors = PricingService._validate_promotion(data, partial=True)
        if errors:
            raise PricingValidationError("促销活动参数校验失败", errors)
        return await SQLAlchemyPromotionRepository.update(db, promo, data)

    # ---------- 校验 ----------

    @staticmethod
    def _validate_rule(data: dict[str, Any], partial: bool = False) -> dict[str, str]:
        errors: dict[str, str] = {}

        if "name" in data or not partial:
            name = data.get("name")
            if not name or not str(name).strip():
                errors["name"] = "名称不能为空"

        if "markup_multiplier" in data:
            multiplier = data["markup_multiplier"]
            if multiplier is not None and float(multiplier) <= 1.0:
                errors["markup_multiplier"] = "倍率必须大于 1.0"

        if "fixed_shipping_fee" in data:
            fee = data["fixed_shipping_fee"]
            if fee is not None and float(fee) < 0:
                errors["fixed_shipping_fee"] = "固定运费不能为负"

        return errors

    @staticmethod
    def _validate_promotion(data: dict[str, Any], partial: bool = False) -> dict[str, str]:
        errors: dict[str, str] = {}

        if "name" in data or not partial:
            name = data.get("name")
            if not name or not str(name).strip():
                errors["name"] = "名称不能为空"

        if "type" in data and data["type"] not in VALID_PROMO_TYPES:
            errors["type"] = f"type 必须为 {sorted(VALID_PROMO_TYPES)} 之一"

        start = data.get("start_date")
        end = data.get("end_date")
        if start and end:
            try:
                start_dt = datetime.fromisoformat(str(start).replace("Z", "+00:00"))
                end_dt = datetime.fromisoformat(str(end).replace("Z", "+00:00"))
                if end_dt <= start_dt:
                    errors["end_date"] = "结束时间必须晚于开始时间"
            except ValueError:
                errors["start_date"] = "时间格式无效（需 ISO8601）"

        return errors


class PricingEngine:
    """四级优先级定价引擎：手动覆盖 > 促销 > 区域规则 > 全局默认。"""

    @staticmethod
    async def calculate(
        db: AsyncSession,
        *,
        region: str,
        cost_price: float,
        override_price: float | None = None,
        product_id: str | None = None,
    ) -> dict[str, Any]:
        if cost_price is None or cost_price < 0:
            raise PricingValidationError("成本价不能为负", {"cost_price": "成本价不能为负"})

        rules = await SQLAlchemyPricingRuleRepository.list_rules(db)
        active_rules = [r for r in rules if r.is_active]
        if not active_rules:
            raise PricingValidationError("暂无可用定价规则", {"rules": "请先创建定价规则"})

        # 1. 手动覆盖（最高优先级）
        if override_price is not None:
            return PricingEngine._result(
                cost_price=cost_price,
                final_price=float(override_price),
                applied_rule="manual_override",
                reason="手动覆盖价格",
                shipping_fee=0.0,
            )

        # 2. 促销活动（匹配区域与时间窗，选最优）
        now = datetime.now()
        promotions = await SQLAlchemyPromotionRepository.list_promotions(db)
        applicable: list[ORMPromotion] = []
        for p in promotions:
            if not p.is_active:
                continue
            if p.start_date and p.start_date > now:
                continue
            if p.end_date and p.end_date < now:
                continue
            regions = p.applicable_regions or []
            if regions and region not in regions:
                continue
            applicable.append(p)

        if applicable:
            best = min(applicable, key=lambda p: (p.priority, p.created_at))
            promo_price = PricingEngine._apply_promo_price(cost_price, best)
            if promo_price is not None and promo_price < cost_price * 1.0:
                return PricingEngine._result(
                    cost_price=cost_price,
                    final_price=promo_price,
                    applied_rule=f"promotion:{best.name}",
                    reason=f"促销活动 {best.name}（{best.type}）",
                    shipping_fee=0.0,
                )

        # 3. 区域定价规则
        region_rule = next((r for r in active_rules if r.region == region), None)
        if region_rule is not None:
            return PricingEngine._result(
                cost_price=cost_price,
                final_price=float(cost_price) * float(region_rule.markup_multiplier),
                applied_rule=region_rule.name,
                reason=f"区域定价 {region}（x{float(region_rule.markup_multiplier)}）",
                shipping_fee=float(region_rule.fixed_shipping_fee),
            )

        # 4. 全局默认规则
        default_rule = next((r for r in active_rules if r.is_default), None)
        if default_rule is None:
            default_rule = next((r for r in active_rules if r.region == "GLOBAL"), None)
        if default_rule is None:
            raise PricingValidationError(
                "该区域无定价规则且无全局默认规则",
                {"region": "请为该区域创建规则或设置全局默认规则"},
            )
        return PricingEngine._result(
            cost_price=cost_price,
            final_price=float(cost_price) * float(default_rule.markup_multiplier),
            applied_rule=default_rule.name,
            reason=f"全局默认（x{float(default_rule.markup_multiplier)}）",
            shipping_fee=float(default_rule.fixed_shipping_fee),
        )

    @staticmethod
    def _apply_promo_price(cost_price: float, promo: ORMPromotion) -> float | None:
        """按促销类型计算折扣价；返回 None 表示不适用。"""
        config = promo.config or {}
        ptype = (promo.type or "").upper()
        if ptype == "COUPON":
            amount = float(config.get("amount") or 0)
            return max(cost_price - amount, 0.0)
        if ptype == "DISCOUNT":
            percent = float(config.get("percent") or 0)
            if percent <= 0 or percent >= 100:
                return None
            return cost_price * (1 - percent / 100)
        if ptype == "BUNDLE":
            # 捆绑价：配置的 bundle_price 直接作为售价
            bundle_price = config.get("bundle_price")
            if bundle_price is None:
                return None
            return float(bundle_price)
        return None

    @staticmethod
    def _result(
        cost_price: float,
        final_price: float,
        applied_rule: str,
        reason: str,
        shipping_fee: float,
    ) -> dict[str, Any]:
        return {
            "cost_price": round(cost_price, 2),
            "final_price": round(final_price, 2),
            "applied_rule": applied_rule,
            "reason": reason,
            "shipping_fee": round(shipping_fee, 2),
        }
