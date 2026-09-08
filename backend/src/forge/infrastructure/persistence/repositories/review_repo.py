"""Product reviews — SQLAlchemy Repository.

规则（行业对齐）：
- 仅已完结订单（order.status=delivered）可评价；
- 同一订单商品项（order_item）至多一条评价（order_item_id 唯一约束兜底）；
- product_id 以订单商品项为准，不允许客户端指定任意商品（防刷分）；
- 商品页聚合评分实时计算：avg = Σ(rating*count)/total，直接读 product_reviews 表。
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from forge.api.errors import APIError, ErrorCode
from forge.infrastructure.persistence.models import ORMOrder, ORMOrderItem, ORMProductReview


def _review_to_dict(review: ORMProductReview) -> dict[str, Any]:
    return {
        "id": str(review.id),
        "order_id": str(review.order_id),
        "order_item_id": str(review.order_item_id),
        "user_id": str(review.user_id),
        "product_id": int(review.product_id) if review.product_id is not None else None,
        "rating": review.rating,
        "title": review.title,
        "content": review.content,
        "images": review.images or [],
        "admin_reply": review.admin_reply,
        "created_at": review.created_at.isoformat() if review.created_at else None,
        "updated_at": review.updated_at.isoformat() if review.updated_at else None,
    }


class SQLAlchemyReviewRepository:
    """Review persistence and aggregation helpers."""

    @staticmethod
    async def create(
        db: AsyncSession,
        order: ORMOrder,
        order_item: ORMOrderItem,
        user_id: UUID,
        rating: int,
        title: str | None,
        content: str | None,
        images: list[str] | None,
    ) -> ORMProductReview:
        if order.status != "delivered":
            raise APIError(
                ErrorCode.REVIEW_NOT_ELIGIBLE,
                message="Order must be delivered before writing a review.",
            )
        exists = (
            await db.execute(select(ORMProductReview.id).where(ORMProductReview.order_item_id == order_item.id))
        ).scalar_one_or_none()
        if exists is not None:
            raise APIError(
                ErrorCode.REVIEW_ALREADY_EXISTS,
                message="You have already reviewed this item.",
            )
        review = ORMProductReview(
            order_id=order.id,
            order_item_id=order_item.id,
            user_id=user_id,
            product_id=order_item.product_id,
            rating=rating,
            title=title,
            content=content,
            images=images or [],
        )
        db.add(review)
        await db.flush()
        return review

    @staticmethod
    async def get_by_id(db: AsyncSession, review_id: UUID) -> ORMProductReview | None:
        return (await db.execute(select(ORMProductReview).where(ORMProductReview.id == review_id))).scalar_one_or_none()

    @staticmethod
    async def delete(db: AsyncSession, review: ORMProductReview) -> None:
        await db.delete(review)
        await db.flush()

    @staticmethod
    async def list_by_product(
        db: AsyncSession,
        product_id: int,
        page: int = 1,
        page_size: int = 10,
    ) -> dict[str, Any]:
        base = select(ORMProductReview).where(ORMProductReview.product_id == product_id)
        count_stmt = select(func.count()).select_from(ORMProductReview).where(ORMProductReview.product_id == product_id)
        total = int((await db.execute(count_stmt)).scalar_one())
        rows = (
            (
                await db.execute(
                    base.order_by(ORMProductReview.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
                )
            )
            .scalars()
            .all()
        )
        return {
            "items": [_review_to_dict(r) for r in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @staticmethod
    async def aggregate(db: AsyncSession, product_id: int) -> dict[str, Any]:
        """实时评分聚合：均值 / 总数 / 星级分布。"""
        rows = (
            await db.execute(
                select(ORMProductReview.rating, func.count())
                .where(ORMProductReview.product_id == product_id)
                .group_by(ORMProductReview.rating)
            )
        ).all()
        distribution = {str(rating): count for rating, count in rows}
        total = sum(int(v) for v in distribution.values())
        avg = round(sum(int(r) * int(c) for r, c in rows) / total, 1) if total else 0.0
        return {
            "product_id": product_id,
            "average_rating": avg,
            "review_count": total,
            "distribution": distribution,
        }

    @staticmethod
    async def list_by_user(
        db: AsyncSession,
        user_id: UUID,
        page: int = 1,
        page_size: int = 10,
    ) -> dict[str, Any]:
        total = int(
            (
                await db.execute(
                    select(func.count()).select_from(ORMProductReview).where(ORMProductReview.user_id == user_id)
                )
            ).scalar_one()
        )
        rows = (
            (
                await db.execute(
                    select(ORMProductReview)
                    .where(ORMProductReview.user_id == user_id)
                    .order_by(ORMProductReview.created_at.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            )
            .scalars()
            .all()
        )
        return {
            "items": [_review_to_dict(r) for r in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
