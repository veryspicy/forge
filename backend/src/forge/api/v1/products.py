"""Public - 商城商品列表 API（C 端）。

只暴露上架商品（status=active），支持分类/搜索/多档排序/分页；
排序默认档从站点配置 `products.default_sort` 读取（Admin 可配置）。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from forge.infrastructure.persistence.models import ORMProduct
from forge.infrastructure.persistence.repositories.product_repo import SQLAlchemyProductRepository
from forge.infrastructure.persistence.repositories.site_profile_repo import SQLAlchemySiteProfileRepository
from forge.main.dependencies import get_db

router = APIRouter()

# 前台排序档位 → 后端排序键（popular 为综合默认档，rating 按评分降序）
_SORT_ALIASES: dict[str, str] = {
    "popular": "default",
    "rating": "rating",
}

# 商城对外可见字段（裁剪内部字段）
_PUBLIC_FIELDS = [
    "id",
    "slug",
    "name",
    "description",
    "name_translations",
    "price",
    "category",
    "breed_groups",
    "suitable_for",
    "tags",
    "images",
    "inventory",
    "is_new",
    "is_recommend",
    "sales",
    "rating",
    "review_count",
    "region_availability",
    "created_at",
]


def _public_item(item: dict[str, Any]) -> dict[str, Any]:
    data = {k: item.get(k) for k in _PUBLIC_FIELDS}
    # C 端前端约定 images 为 URL 字符串数组（ProductCard 用 images[0] 直接作 src）
    images = data.get("images") or []
    data["images"] = [img["url"] for img in images if isinstance(img, dict) and img.get("url")]
    return data


def _sort_key(sort: str) -> str:
    return _SORT_ALIASES.get(sort, sort)


@router.get("/products")
async def list_public_products(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=24, ge=1, le=100),
    category: str | None = Query(default=None),
    search: str | None = Query(default=None),
    sort: str = Query(default="popular", description="排序：popular/sales/newest/price_asc/price_desc/rating"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    # 默认档可配置：Admin 站点配置 products.default_sort 覆盖 popular 默认行为
    if sort == "popular":
        profile = await SQLAlchemySiteProfileRepository.get_active(db)
        config: dict[str, Any] = dict((profile.config or {}) if profile else {})
        default_sort = (config.get("products") or {}).get("default_sort", "default")
        sort_by = _SORT_ALIASES.get(default_sort, default_sort)
    else:
        sort_by = _sort_key(sort)

    if sort_by == "rating":
        # 评分档走独立排序（repo 默认档位不包含 rating）
        result = await _list_rating_sorted(db, page, page_size, category, search)
    else:
        result = await SQLAlchemyProductRepository.list_products(
            db,
            page=page,
            page_size=page_size,
            category=category,
            search=search,
            status="active",
            sort_by=sort_by,
        )
    result["items"] = [_public_item(p) for p in result["items"]]
    return result


async def _list_rating_sorted(
    db: AsyncSession,
    page: int,
    page_size: int,
    category: str | None,
    search: str | None,
) -> dict[str, Any]:
    from sqlalchemy import func, or_, select

    filters = [ORMProduct.status == "active"]
    if category:
        filters.append(ORMProduct.category == category)
    if search:
        pattern = f"%{search}%"
        filters.append(or_(ORMProduct.name.ilike(pattern), ORMProduct.sku.ilike(pattern)))

    total = (await db.execute(select(func.count(ORMProduct.id)).where(*filters))).scalar_one()
    rows = (
        (
            await db.execute(
                select(ORMProduct)
                .where(*filters)
                .order_by(ORMProduct.rating.desc(), ORMProduct.review_count.desc(), ORMProduct.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        .scalars()
        .all()
    )
    return {
        "items": [p.to_dict() for p in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/products/{product_id}")
async def get_public_product(
    product_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """C 端商品详情：支持按 slug 或数字 id 查询，仅返回上架商品。"""
    product = await SQLAlchemyProductRepository.get_by_slug(db, product_id)
    if product is None:
        try:
            pid = int(product_id)
        except ValueError:
            pid = -1
        if pid > 0:
            product = await SQLAlchemyProductRepository.get_by_id(db, pid)
    if product is None or product.status != "active":
        raise HTTPException(status_code=404, detail="Product not found")
    return _public_item(product.to_dict())
