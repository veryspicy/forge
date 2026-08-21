"""Admin - 定价引擎 API（P1：PricingRule CRUD + Promotion CRUD + 价格计算）。"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from forge.application.services.pricing_service import (
    PricingEngine,
    PricingService,
    PricingValidationError,
)
from forge.infrastructure.persistence.models import ORMPricingRule, ORMPromotion
from forge.infrastructure.persistence.repositories.pricing_repo import (
    SQLAlchemyPricingRuleRepository,
    SQLAlchemyPromotionRepository,
)
from forge.main.dependencies import get_db
from forge.main.rbac import require_permission

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic 模型
# ---------------------------------------------------------------------------
class PricingRuleCreate(BaseModel):
    name: str
    region: str = "GLOBAL"
    markup_multiplier: float = 1.4
    fixed_shipping_fee: float = 0.0
    priority: int = 0
    is_active: bool = True
    is_default: bool = False


class PricingRuleUpdate(BaseModel):
    name: str | None = None
    region: str | None = None
    markup_multiplier: float | None = None
    fixed_shipping_fee: float | None = None
    priority: int | None = None
    is_active: bool | None = None
    is_default: bool | None = None


class PromotionCreate(BaseModel):
    name: str
    type: str = "COUPON"
    applicable_regions: list[str] | None = None
    applicable_categories: list[str] | None = None
    start_date: str | None = None
    end_date: str | None = None
    is_active: bool = True
    stackable: bool = False
    priority: int = 0
    config: dict[str, Any] = {}


class PromotionUpdate(BaseModel):
    name: str | None = None
    type: str | None = None
    applicable_regions: list[str] | None = None
    applicable_categories: list[str] | None = None
    start_date: str | None = None
    end_date: str | None = None
    is_active: bool | None = None
    stackable: bool | None = None
    priority: int | None = None
    config: dict[str, Any] | None = None


class PricingListResponse(BaseModel):
    items: list[dict[str, Any]]
    total: int


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
def _coerce_uuid(value: str, field: str = "ID") -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效的{field}") from None


async def _get_rule_or_404(db: AsyncSession, raw_id: str) -> ORMPricingRule:
    rule_id = _coerce_uuid(raw_id, "规则 ID")
    rule = await SQLAlchemyPricingRuleRepository.get_by_id(db, rule_id)  # type: ignore[arg-type]
    if rule is None:
        raise HTTPException(status_code=404, detail="定价规则不存在")
    return rule


async def _get_promo_or_404(db: AsyncSession, raw_id: str) -> ORMPromotion:
    promo_id = _coerce_uuid(raw_id, "促销 ID")
    promo = await SQLAlchemyPromotionRepository.get_by_id(db, promo_id)  # type: ignore[arg-type]
    if promo is None:
        raise HTTPException(status_code=404, detail="促销活动不存在")
    return promo


def _clean_payload(data: dict[str, Any]) -> dict[str, Any]:
    """剔除 None 值字段，避免覆盖已有数据。"""
    return {k: v for k, v in data.items() if v is not None}


def _coerce_dates(data: dict[str, Any]) -> dict[str, Any]:
    """ISO 字符串时间转 datetime（保持 naive，与模型 timezone=False 一致）。"""
    for field in ("start_date", "end_date"):
        if field in data and data[field]:
            raw = str(data[field]).replace("Z", "+00:00")
            dt = datetime.fromisoformat(raw)
            if dt.tzinfo is not None:
                dt = dt.replace(tzinfo=None)
            data[field] = dt
    return data


# ---------------------------------------------------------------------------
# 1. PricingRule CRUD
# ---------------------------------------------------------------------------
@router.post("/rules", status_code=201)
async def create_rule(
    payload: PricingRuleCreate,
    admin: dict[str, Any] = Depends(require_permission("pricing", "manage")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")

    data = payload.model_dump()
    try:
        rule = await PricingService.create_rule(db, data)
    except PricingValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None

    await db.commit()
    await db.refresh(rule)
    return {"data": rule.to_dict()}


@router.get("/rules", response_model=PricingListResponse)
async def list_rules(
    admin: dict[str, Any] = Depends(require_permission("pricing", "view")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")

    rules = await SQLAlchemyPricingRuleRepository.list_rules(db)
    return {"items": [r.to_dict() for r in rules], "total": len(rules)}


@router.patch("/rules/{rule_id}")
async def update_rule(
    rule_id: str,
    payload: PricingRuleUpdate,
    admin: dict[str, Any] = Depends(require_permission("pricing", "manage")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")

    rule = await _get_rule_or_404(db, rule_id)
    data = _clean_payload(payload.model_dump())
    if not data:
        raise HTTPException(status_code=400, detail="无更新字段")

    try:
        rule = await PricingService.update_rule(db, rule, data)
    except PricingValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None

    await db.commit()
    await db.refresh(rule)
    return {"data": rule.to_dict()}


@router.delete("/rules/{rule_id}")
async def delete_rule(
    rule_id: str,
    admin: dict[str, Any] = Depends(require_permission("pricing", "view")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")

    rule = await _get_rule_or_404(db, rule_id)
    await SQLAlchemyPricingRuleRepository.delete(db, rule)
    await db.commit()
    return {"data": {"id": rule_id, "deleted": True}}


# ---------------------------------------------------------------------------
# 2. Promotion CRUD
# ---------------------------------------------------------------------------
@router.post("/promotions", status_code=201)
async def create_promotion(
    payload: PromotionCreate,
    admin: dict[str, Any] = Depends(require_permission("pricing", "manage")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")

    data = _coerce_dates(payload.model_dump())
    try:
        promo = await PricingService.create_promotion(db, data)
    except PricingValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None

    await db.commit()
    await db.refresh(promo)
    return {"data": promo.to_dict()}


@router.get("/promotions", response_model=PricingListResponse)
async def list_promotions(
    admin: dict[str, Any] = Depends(require_permission("pricing", "view")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")

    promotions = await SQLAlchemyPromotionRepository.list_promotions(db)
    return {"items": [p.to_dict() for p in promotions], "total": len(promotions)}


@router.patch("/promotions/{promo_id}")
async def update_promotion(
    promo_id: str,
    payload: PromotionUpdate,
    admin: dict[str, Any] = Depends(require_permission("pricing", "manage")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")

    promo = await _get_promo_or_404(db, promo_id)
    data = _coerce_dates(_clean_payload(payload.model_dump()))
    if not data:
        raise HTTPException(status_code=400, detail="无更新字段")

    try:
        promo = await PricingService.update_promotion(db, promo, data)
    except PricingValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None

    await db.commit()
    await db.refresh(promo)
    return {"data": promo.to_dict()}


@router.delete("/promotions/{promo_id}")
async def delete_promotion(
    promo_id: str,
    admin: dict[str, Any] = Depends(require_permission("pricing", "manage")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")

    promo = await _get_promo_or_404(db, promo_id)
    await SQLAlchemyPromotionRepository.delete(db, promo)
    await db.commit()
    return {"data": {"id": promo_id, "deleted": True}}


# ---------------------------------------------------------------------------
# 3. 价格计算引擎
# ---------------------------------------------------------------------------
@router.get("/calculate")
async def calculate_price(
    region: str = Query(default="GLOBAL"),
    cost_price: float = Query(..., ge=0),
    product_id: str | None = Query(default=None),
    override_price: float | None = Query(default=None, ge=0),
    admin: dict[str, Any] = Depends(require_permission("pricing", "view")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if not admin:
        raise HTTPException(status_code=401, detail="未登录")

    try:
        result = await PricingEngine.calculate(
            db,
            region=region,
            cost_price=cost_price,
            override_price=override_price,
            product_id=product_id,
        )
    except PricingValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None

    return {"data": result}
