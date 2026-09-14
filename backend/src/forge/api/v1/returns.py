"""C-end Returns API - 售后服务（退货/退款申请 RMA）。

- 依赖 C 端 JWT（auth.get_current_user），售后单严格按当前用户隔离
- 前端契约（portal-web）：
  GET    /returns/eligibility?order_number=  -> {eligible, items[{returnable_quantity}], refundable_amount}
  POST   /returns                            -> return（body: {order_number, items, reason, note?}）
  GET    /returns                            -> {items, total, page, page_size}（?status= 过滤）
  GET    /returns/{return_number}            -> return detail
  POST   /returns/{return_number}/cancel     -> return（requested/approved/received 可撤销）
  POST   /returns/{return_number}/shipment   -> return（approved 后回填寄回承运商+快递单号，供物流追踪）
- 状态机（与 Admin 端共用 return_repo）：requested -> approved -> received -> refunded
  旁支终态：rejected（驳回）/ cancelled（客户撤销）/ closed（超时关闭）
- 资金动作不在 C 端触发：审核通过并收到回寄商品后由 Admin 执行退款，金额沿用审核锁定值
"""

from __future__ import annotations

import re
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from forge.api.errors import APIError, ErrorCode
from forge.api.v1.auth import get_current_user
from forge.api.v1.orders import _current_owner_id, _owned_order_or_404
from forge.infrastructure.persistence.repositories.return_repo import (
    OPEN_RETURN_STATUSES,
    RETURN_TERMINAL_STATUSES,
    SQLAlchemyReturnRepository,
)
from forge.main.dependencies import get_db

router = APIRouter(prefix="/returns", tags=["C-end Returns"])

VALID_RETURN_STATUSES = set(OPEN_RETURN_STATUSES) | set(RETURN_TERMINAL_STATUSES)
VALID_REFUND_METHODS = {"original", "store_credit", "manual"}
MAX_REASON_LENGTH = 100
MAX_CARRIER_LENGTH = 100
MAX_TRACKING_LENGTH = 64
# 快递单号：字母数字开头，允许字母数字/连字符/下划线/空格（覆盖主流承运商单号格式）
TRACKING_NUMBER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9\-_ ]{3,63}$")


class ReturnItemCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    order_item_id: str = Field(min_length=1)
    quantity: int = Field(gt=0)


class ReturnCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    order_number: str = Field(min_length=1, max_length=50)
    items: list[ReturnItemCreate] = Field(min_length=1)
    reason: str = Field(min_length=1, max_length=MAX_REASON_LENGTH)
    note: str | None = Field(default=None, max_length=2000)
    refund_method: str | None = Field(default=None, max_length=20)


class ReturnCancel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    reason: str | None = Field(default=None, max_length=2000)


class ReturnShipmentCreate(BaseModel):
    """客户寄回物流：承运商 + 快递单号。"""

    model_config = ConfigDict(extra="ignore")

    carrier: str = Field(min_length=1, max_length=MAX_CARRIER_LENGTH)
    tracking_number: str = Field(min_length=1, max_length=MAX_TRACKING_LENGTH)


async def _owned_return(db: AsyncSession, owner_id: UUID, return_number: str) -> Any:
    """按单号取当前用户售后单，非本人一律 404（不泄露他人单据是否存在）。"""
    rr = await SQLAlchemyReturnRepository.get_return_request(db, return_number)
    if str(rr.user_id) != str(owner_id):
        raise APIError(ErrorCode.RETURN_NOT_FOUND, message="Return request does not exist.")
    return rr


@router.get("")
async def list_returns(
    user_claims: dict[str, object] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    order_number: str | None = Query(default=None, max_length=50),
) -> dict[str, Any]:
    """当前用户退货申请分页列表；?status= / ?order_number= 可选过滤。"""
    owner_id = await _current_owner_id(user_claims, db)
    if status_filter and status_filter not in VALID_RETURN_STATUSES:
        raise APIError(ErrorCode.VALIDATION_ERROR, message=f"Invalid return status: {status_filter}")
    result = await SQLAlchemyReturnRepository.list_customer_returns(
        db,
        user_id=owner_id,
        status=status_filter,
        order_number=order_number,
        page=page,
        page_size=page_size,
    )
    return result


@router.post("")
async def create_return(
    payload: ReturnCreate,
    user_claims: dict[str, object] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """提交退货申请：校验订单可退性 + 行级剩余可退数量（已扣除在途申请占用）。"""
    owner_id = await _current_owner_id(user_claims, db)
    order = await _owned_order_or_404(db, owner_id, payload.order_number)
    refund_method = payload.refund_method or "original"
    if refund_method not in VALID_REFUND_METHODS:
        raise APIError(ErrorCode.VALIDATION_ERROR, message=f"Invalid refund method: {refund_method}")
    rr = await SQLAlchemyReturnRepository.create_return_request(
        db,
        order,
        user_id=owner_id,
        items=[item.model_dump() for item in payload.items],
        reason=payload.reason.strip(),
        note=payload.note,
        refund_method=refund_method,
    )
    await db.commit()
    await db.refresh(rr, attribute_names=["items"])
    return SQLAlchemyReturnRepository.to_dict(rr)


@router.get("/eligibility")
async def return_eligibility(
    order_number: str = Query(min_length=1, max_length=50),
    user_claims: dict[str, object] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """查询订单可退性：是否可申请 + 各行剩余可退数量 + 剩余可退金额。"""
    owner_id = await _current_owner_id(user_claims, db)
    order = await _owned_order_or_404(db, owner_id, order_number)
    return await SQLAlchemyReturnRepository.return_eligibility(db, order)


@router.get("/{return_number}")
async def get_return(
    return_number: str,
    user_claims: dict[str, object] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """售后单详情（仅本人可见）。"""
    owner_id = await _current_owner_id(user_claims, db)
    rr = await _owned_return(db, owner_id, return_number)
    return SQLAlchemyReturnRepository.to_dict(rr)


@router.post("/{return_number}/cancel")
async def cancel_return(
    return_number: str,
    payload: ReturnCancel | None = None,
    user_claims: dict[str, object] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """撤销退货申请（退款完成/驳回/关闭后不可撤销）。"""
    owner_id = await _current_owner_id(user_claims, db)
    rr = await _owned_return(db, owner_id, return_number)
    await SQLAlchemyReturnRepository.cancel_return_request(db, rr, reason=(payload.reason if payload else None))
    await db.commit()
    await db.refresh(rr, attribute_names=["items"])
    return SQLAlchemyReturnRepository.to_dict(rr)


@router.post("/{return_number}/shipment")
async def submit_return_shipment(
    return_number: str,
    payload: ReturnShipmentCreate,
    user_claims: dict[str, object] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """上传退货快递单号（审核通过后寄回）：仅本人、仅 approved、未超期，重复提交覆盖。"""
    owner_id = await _current_owner_id(user_claims, db)
    rr = await _owned_return(db, owner_id, return_number)
    carrier = payload.carrier.strip()
    tracking_number = payload.tracking_number.strip()
    if not carrier or not tracking_number:
        raise APIError(ErrorCode.VALIDATION_ERROR, message="Carrier and tracking number are required.")
    if not TRACKING_NUMBER_PATTERN.match(tracking_number):
        raise APIError(ErrorCode.VALIDATION_ERROR, message="Invalid tracking number format.")
    await SQLAlchemyReturnRepository.submit_return_shipment(db, rr, carrier=carrier, tracking_number=tracking_number)
    await db.commit()
    await db.refresh(rr, attribute_names=["items"])
    return SQLAlchemyReturnRepository.to_dict(rr)
