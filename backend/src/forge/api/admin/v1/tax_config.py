"""Admin 税费配置 API（A 方案静态税率表，运行期生效）。

- ``GET  /api/admin/v1/tax-config``        当前生效配置 + 可选计税引擎
- ``PUT  /api/admin/v1/tax-config``        保存税率表/开关/价内含税
- ``POST /api/admin/v1/tax-config/preview`` 计税预览（改完立刻看结果，不用下单）

配置写 ``app_settings.tax``，保存后快照立即失效，**不需要重新发布或重启容器**。
后续切换第三方税务引擎（B 方案）只需实现 ``tax_service.TaxProvider`` 并在本页
把 provider 切成对应值。
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from forge.application.services import tax_service
from forge.main.dependencies import get_db
from forge.main.rbac import require_permission

logger = logging.getLogger(__name__)

router = APIRouter()


class TaxConfigPayload(BaseModel):
    """税率表整体保存。"""

    provider: str = "static"
    enabled: bool = True
    prices_include_tax: bool = False
    default_rate: str = "0"
    rates: list[dict[str, Any]] = Field(default_factory=list)


class TaxPreviewPayload(BaseModel):
    """计税预览入参。"""

    country: str = Field(default="", max_length=2)
    region: str | None = Field(default=None, max_length=50)
    amount: str = "100"
    shipping: str = "0"
    category: str | None = Field(default=None, max_length=50)


def _actor_id(claims: dict[str, Any]) -> str | None:
    return str(claims.get("sub")) if claims.get("sub") else None


@router.get("")
async def get_tax_config(
    db: AsyncSession = Depends(get_db),
    claims: dict[str, Any] = Depends(require_permission("tax_config", "view")),
) -> dict[str, Any]:
    """当前税率配置（含可选引擎与默认兜底表）。"""
    await tax_service.refresh(db, force=True)
    return {
        "config": tax_service.current_config(),
        "providers": tax_service.available_providers(),
        "defaults": [dict(r) for r in tax_service.DEFAULT_RATES],
        "note": "税率修改保存后立即生效，无需发布；订单按收货地址辖区计税并落快照。",
    }


@router.put("")
async def update_tax_config(
    payload: TaxConfigPayload,
    db: AsyncSession = Depends(get_db),
    claims: dict[str, Any] = Depends(require_permission("tax_config", "manage")),
) -> dict[str, Any]:
    """整体保存税率表。"""
    saved = await tax_service.save_config(
        db,
        {
            "provider": payload.provider,
            "enabled": payload.enabled,
            "prices_include_tax": payload.prices_include_tax,
            "default_rate": payload.default_rate,
            "rates": payload.rates,
        },
        updated_by=_actor_id(claims),
    )
    await db.commit()
    await tax_service.refresh(db, force=True)
    logger.info("tax config updated by %s (%d rules)", _actor_id(claims), len(saved["rates"]))
    return {"config": saved}


@router.post("/preview")
async def preview_tax(
    payload: TaxPreviewPayload,
    db: AsyncSession = Depends(get_db),
    claims: dict[str, Any] = Depends(require_permission("tax_config", "view")),
) -> dict[str, Any]:
    """按当前税率表试算（不落库）。"""
    amount = Decimal(str(payload.amount or "0"))
    shipping = Decimal(str(payload.shipping or "0"))
    result = await tax_service.calculate_tax(
        db,
        country=payload.country or None,
        region=payload.region or None,
        lines=[(payload.category, amount)],
        shipping=shipping,
    )
    return {
        "tax": float(result.tax_amount),
        "rate": float(result.rate),
        "name": result.name,
        "label": result.label,
        "jurisdiction": result.jurisdiction,
        "taxable_amount": float(result.taxable_amount),
        "inclusive": result.inclusive,
        "total": float(amount + shipping if result.inclusive else amount + shipping + result.tax_amount),
    }
