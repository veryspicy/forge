"""Pricing — SQLAlchemy Repository（PricingRule + Promotion）。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from forge.infrastructure.persistence.models import ORMPricingRule, ORMPromotion


def _now() -> datetime:
    return datetime.now()


class SQLAlchemyPricingRuleRepository:
    """定价规则数据库访问封装。"""

    @staticmethod
    async def list_rules(db: AsyncSession) -> list[ORMPricingRule]:
        result = await db.execute(
            select(ORMPricingRule).order_by(ORMPricingRule.priority.asc(), ORMPricingRule.created_at.asc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_by_id(db: AsyncSession, rule_id: str) -> ORMPricingRule | None:
        result = await db.execute(select(ORMPricingRule).where(ORMPricingRule.id == rule_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def create(db: AsyncSession, data: dict[str, Any]) -> ORMPricingRule:
        rule = ORMPricingRule(**data)
        db.add(rule)
        await db.flush()
        await db.refresh(rule)
        return rule

    @staticmethod
    async def update(db: AsyncSession, rule: ORMPricingRule, data: dict[str, Any]) -> ORMPricingRule:
        for key, value in data.items():
            if hasattr(rule, key):
                setattr(rule, key, value)
        rule.updated_at = _now()  # type: ignore[assignment]
        await db.flush()
        await db.refresh(rule)
        return rule

    @staticmethod
    async def delete(db: AsyncSession, rule: ORMPricingRule) -> None:
        await db.delete(rule)
        await db.flush()

    @staticmethod
    async def count(db: AsyncSession) -> int:
        result = await db.execute(select(func.count(ORMPricingRule.id)))
        return result.scalar_one()


class SQLAlchemyPromotionRepository:
    """促销活动数据库访问封装。"""

    @staticmethod
    async def list_promotions(db: AsyncSession) -> list[ORMPromotion]:
        result = await db.execute(
            select(ORMPromotion).order_by(ORMPromotion.priority.asc(), ORMPromotion.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_by_id(db: AsyncSession, promo_id: str) -> ORMPromotion | None:
        result = await db.execute(select(ORMPromotion).where(ORMPromotion.id == promo_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def create(db: AsyncSession, data: dict[str, Any]) -> ORMPromotion:
        promo = ORMPromotion(**data)
        db.add(promo)
        await db.flush()
        await db.refresh(promo)
        return promo

    @staticmethod
    async def update(db: AsyncSession, promo: ORMPromotion, data: dict[str, Any]) -> ORMPromotion:
        for key, value in data.items():
            if hasattr(promo, key):
                setattr(promo, key, value)
        promo.updated_at = _now()  # type: ignore[assignment]
        await db.flush()
        await db.refresh(promo)
        return promo

    @staticmethod
    async def delete(db: AsyncSession, promo: ORMPromotion) -> None:
        await db.delete(promo)
        await db.flush()

    @staticmethod
    async def count(db: AsyncSession) -> int:
        result = await db.execute(select(func.count(ORMPromotion.id)))
        return result.scalar_one()
