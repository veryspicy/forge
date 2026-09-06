"""C-end Reviews API - 商品评价（提交/我的/删除/商品公开列表与聚合）。

- 提交：POST /api/v1/reviews {order_number, order_item_id, rating, title?, content?, images?}
  - 仅本人 delivered 未删除订单可评；同一 order_item 至多一条
  - product_id 由订单商品项推导（防刷分）
- 我的：GET /api/v1/reviews/mine
- 删除：DELETE /api/v1/reviews/{id}（仅作者）
- 商品公开：GET /api/v1/products/{product_id}/reviews（含 summary 聚合）
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from forge.api.errors import APIError, ErrorCode
from forge.api.v1.auth import get_current_user
from forge.api.v1.orders import _current_owner_id, _owned_order_or_404
from forge.infrastructure.persistence.repositories.review_repo import SQLAlchemyReviewRepository
from forge.main.dependencies import get_db

router = APIRouter(prefix="/reviews", tags=["C-end Reviews"])


class ReviewCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    order_number: str = Field(min_length=1, max_length=50)
    order_item_id: str = Field(min_length=1, max_length=64)
    rating: int = Field(ge=1, le=5)
    title: str | None = Field(default=None, max_length=200)
    content: str | None = Field(default=None, max_length=5000)
    images: list[str] | None = None


@router.post("")
async def create_review(
    payload: ReviewCreate,
    user_claims: dict[str, object] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """提交商品评价（订单须已完结 delivered 且未被删除）。"""
    owner_id = await _current_owner_id(user_claims, db)
    order = await _owned_order_or_404(db, owner_id, payload.order_number)
    if order.deleted_at is not None:
        raise APIError(ErrorCode.REVIEW_NOT_ELIGIBLE, message="Order is archived and cannot be reviewed.")
    try:
        item_uuid = UUID(payload.order_item_id)
    except ValueError as exc:
        raise APIError(ErrorCode.INVALID_ID, message="order_item_id is not a valid UUID.") from exc
    order_item = next((i for i in (order.items or []) if i.id == item_uuid), None)
    if order_item is None:
        raise APIError(ErrorCode.VALIDATION_ERROR, message="Order item does not belong to this order.")
    review = await SQLAlchemyReviewRepository.create(
        db,
        order,
        order_item,
        owner_id,
        payload.rating,
        payload.title,
        payload.content,
        payload.images,
    )
    await db.commit()
    return {
        "id": str(review.id),
        "product_id": int(review.product_id) if review.product_id is not None else None,
        "rating": review.rating,
        "title": review.title,
        "content": review.content,
        "images": review.images or [],
        "created_at": review.created_at.isoformat() if review.created_at else None,
        "summary": await SQLAlchemyReviewRepository.aggregate(db, int(review.product_id)),
    }


@router.get("/mine")
async def my_reviews(
    user_claims: dict[str, object] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
) -> dict[str, Any]:
    owner_id = await _current_owner_id(user_claims, db)
    return await SQLAlchemyReviewRepository.list_by_user(db, owner_id, page=page, page_size=page_size)


@router.delete("/{review_id}")
async def delete_review(
    review_id: str,
    user_claims: dict[str, object] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    owner_id = await _current_owner_id(user_claims, db)
    try:
        rid = UUID(review_id)
    except ValueError as exc:
        raise APIError(ErrorCode.INVALID_ID, message="review_id is not a valid UUID.") from exc
    review = await SQLAlchemyReviewRepository.get_by_id(db, rid)
    if review is None or review.user_id != owner_id:
        raise APIError(ErrorCode.REVIEW_NOT_FOUND, message="Review does not exist.")
    await SQLAlchemyReviewRepository.delete(db, review)
    await db.commit()
    return {"deleted": "true"}


# 公开商品评价聚合列表挂在 /products/{id}/reviews（独立 router，无鉴权）
public_reviews_router = APIRouter(prefix="/products", tags=["C-end Product Reviews"])


@public_reviews_router.get("/{product_id}/reviews")
async def list_product_reviews(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
) -> dict[str, Any]:
    result = await SQLAlchemyReviewRepository.list_by_product(db, product_id, page=page, page_size=page_size)
    summary = await SQLAlchemyReviewRepository.aggregate(db, product_id)
    result["summary"] = summary
    return result
