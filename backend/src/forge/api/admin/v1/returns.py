"""Admin Returns API - 售后（退货/退款申请 RMA）审批与执行。

- GET   /api/admin/v1/returns                 分页列表（?status=&keyword=）
- GET   /api/admin/v1/returns/stats           售后看板计数
- GET   /api/admin/v1/returns/{return_number} 详情
- POST  /api/admin/v1/returns/{return_number}/review   审核：通过则锁定应退金额 + 寄回截止时间；驳回即终结
- POST  /api/admin/v1/returns/{return_number}/receive  确认收到回寄商品（approved -> received）
- POST  /api/admin/v1/returns/{return_number}/refund   执行退款（委托 order_repo.admin_refund_order，唯一资金实现）
- POST  /api/admin/v1/returns/{return_number}/close    关闭申请单（人工，未退款成功前可用）

权限：沿用订单域权限 orders:view（读）/ orders:manage（写）。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from forge.api.errors import APIError, ErrorCode
from forge.infrastructure.persistence.repositories.return_repo import (
    DEFAULT_DEADLINE_DAYS,
    OPEN_RETURN_STATUSES,
    RETURN_TERMINAL_STATUSES,
    SQLAlchemyReturnRepository,
)
from forge.main.dependencies import get_db
from forge.main.rbac import require_permission

router = APIRouter()

VALID_RETURN_STATUSES = set(OPEN_RETURN_STATUSES) | set(RETURN_TERMINAL_STATUSES)


class AdminReturnReviewRequest(BaseModel):
    """审核退货申请：approved=false 时直接驳回终结。"""

    model_config = ConfigDict(extra="ignore")

    approved: bool
    note: str | None = Field(default=None, max_length=2000)
    restock: bool | None = None
    refund_shipping: bool | None = None
    deadline_days: int = Field(default=DEFAULT_DEADLINE_DAYS, ge=1, le=90)


class AdminReturnReceiveRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    note: str | None = Field(default=None, max_length=2000)


class AdminReturnRefundRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    note: str | None = Field(default=None, max_length=2000)


class AdminReturnCloseRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    reason: str | None = Field(default=None, max_length=200)


def _actor(admin: dict[str, object]) -> str:
    return str(admin.get("email") or admin.get("sub") or "admin")


async def _return_or_404(db: AsyncSession, return_number: str) -> Any:
    return await SQLAlchemyReturnRepository.get_return_request(db, return_number)


@router.get("/")
async def list_returns(
    admin: dict[str, object] = Depends(require_permission("orders", "view")),
    db: AsyncSession = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    keyword: str | None = Query(default=None, max_length=100),
) -> dict[str, Any]:
    """售后申请分页列表（?status= 过滤 + ?keyword= 按单号/原因模糊检索）。"""
    if status_filter and status_filter not in VALID_RETURN_STATUSES:
        raise APIError(ErrorCode.VALIDATION_ERROR, message=f"Invalid return status: {status_filter}")
    result = await SQLAlchemyReturnRepository.list_admin_returns(
        db, status=status_filter, keyword=keyword, page=page, page_size=page_size
    )
    return result


@router.get("/stats")
async def return_stats(
    admin: dict[str, object] = Depends(require_permission("orders", "view")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    """售后看板：待审 / 待收货 / 待退款 / 已完成等计数。"""
    return await SQLAlchemyReturnRepository.return_stats(db)


@router.get("/{return_number}")
async def get_return_detail(
    return_number: str,
    admin: dict[str, object] = Depends(require_permission("orders", "view")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """售后单详情。"""
    rr = await _return_or_404(db, return_number)
    return SQLAlchemyReturnRepository.to_dict(rr)


@router.post("/{return_number}/review")
async def review_return(
    return_number: str,
    payload: AdminReturnReviewRequest,
    admin: dict[str, object] = Depends(require_permission("orders", "manage")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """审核退货申请：通过则锁定应退金额与寄回截止时间；驳回则直接终结（不做资金动作）。"""
    rr = await _return_or_404(db, return_number)
    if not payload.approved and not (payload.note or "").strip():
        raise APIError(ErrorCode.VALIDATION_ERROR, message="Rejecting a return request requires a reason.")
    await SQLAlchemyReturnRepository.review_return_request(
        db,
        rr,
        approved=payload.approved,
        reviewed_by=_actor(admin),
        note=payload.note,
        restock=payload.restock,
        refund_shipping=payload.refund_shipping,
        deadline_days=payload.deadline_days,
    )
    await db.commit()
    await db.refresh(rr, attribute_names=["items"])
    return SQLAlchemyReturnRepository.to_dict(rr)


@router.post("/{return_number}/receive")
async def receive_return(
    return_number: str,
    payload: AdminReturnReceiveRequest | None = None,
    admin: dict[str, object] = Depends(require_permission("orders", "manage")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """确认收到回寄商品：approved -> received（进入待退款）。"""
    rr = await _return_or_404(db, return_number)
    await SQLAlchemyReturnRepository.mark_return_received(db, rr, note=(payload.note if payload else None))
    await db.commit()
    await db.refresh(rr, attribute_names=["items"])
    return SQLAlchemyReturnRepository.to_dict(rr)


@router.post("/{return_number}/refund")
async def refund_return(
    return_number: str,
    payload: AdminReturnRefundRequest | None = None,
    admin: dict[str, object] = Depends(require_permission("orders", "manage")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """执行退款：按审核锁定金额走行级退款（order_repo 唯一实现），并回写售后单为 refunded。"""
    rr = await _return_or_404(db, return_number)
    await SQLAlchemyReturnRepository.execute_return_refund(
        db, rr, refunded_by=_actor(admin), note=(payload.note if payload else None)
    )
    await db.commit()
    await db.refresh(rr, attribute_names=["items"])
    return SQLAlchemyReturnRepository.to_dict(rr)


@router.post("/{return_number}/close")
async def close_return(
    return_number: str,
    payload: AdminReturnCloseRequest | None = None,
    admin: dict[str, object] = Depends(require_permission("orders", "manage")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """关闭售后单（人工终止流程，未退款成功前可用）。"""
    rr = await _return_or_404(db, return_number)
    await SQLAlchemyReturnRepository.close_return_request(db, rr, reason=(payload.reason if payload else None))
    await db.commit()
    await db.refresh(rr, attribute_names=["items"])
    return SQLAlchemyReturnRepository.to_dict(rr)
