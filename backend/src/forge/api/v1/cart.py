"""C-end Cart API - 购物车（列表/加购/改数量/删除/清空）。

- 依赖 C 端 JWT（auth.get_current_user），owner 由 token 内 email 反查 users.id
- 前端契约（portal-web useApi / stores/cart）：
  GET    /cart/items          -> {items: [...]}
  POST   /cart/items          -> cart item（同商品重复加购自动合并数量）
  PUT    /cart/items/{id}     -> cart item（quantity 1..999）
  DELETE /cart/items/{id}     -> 204
  DELETE /cart/items          -> 204（清空）
"""

from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from forge.api.errors import APIError, ErrorCode
from forge.api.v1.auth import get_current_user
from forge.infrastructure.persistence.models import ORMCartItem, ORMProduct
from forge.infrastructure.persistence.repositories.cart_repo import SQLAlchemyCartRepository
from forge.infrastructure.persistence.repositories.product_repo import SQLAlchemyProductRepository
from forge.infrastructure.persistence.repositories.user_repo import SQLAlchemyUserRepository
from forge.main.dependencies import get_db

router = APIRouter(prefix="/cart", tags=["C-end Cart"])

FREE_SHIPPING_THRESHOLD = 50
FLAT_SHIPPING = 5
CURRENCY = "USD"
MAX_QUANTITY = 999


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class CartItemIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    product_id: int = Field(gt=0)
    quantity: int = Field(default=1, ge=1, le=MAX_QUANTITY)
    name: str | None = Field(default=None, max_length=500)
    price: float | None = None
    image: str | None = Field(default=None, max_length=1000)


class CartItemUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    quantity: int = Field(ge=1, le=MAX_QUANTITY)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _current_owner_id(
    claims: dict[str, object],
    db: AsyncSession,
) -> UUID:
    """按 token email 反查 users.id；用户不存在视为未授权。"""
    email = str(claims.get("sub") or "")
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="UNAUTHORIZED")
    user = await SQLAlchemyUserRepository.get_by_email(db, email)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="UNAUTHORIZED")
    return cast(UUID, user.id)


def _product_image(product: ORMProduct) -> str | None:
    images: list[Any] = cast(list[Any], product.images or [])
    if not images:
        return None
    first = images[0]
    if isinstance(first, dict):
        return str(first.get("url") or "")
    return str(first)


def _cart_item_dict(item: ORMCartItem) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "product_id": int(item.product_id),
        "name": item.name,
        "price": float(item.price),
        "quantity": item.quantity,
        "image": item.image,
        "subtotal": round(float(item.price) * int(item.quantity), 2),
    }


def _cart_summary(items: list[ORMCartItem]) -> dict[str, Any]:
    subtotal = round(sum(float(i.price) * int(i.quantity) for i in items), 2)
    shipping_cost = 0.0 if subtotal > FREE_SHIPPING_THRESHOLD else float(FLAT_SHIPPING)
    total = round(subtotal + shipping_cost, 2)
    return {
        "items": [_cart_item_dict(i) for i in items],
        "subtotal": subtotal,
        "shipping_cost": shipping_cost,
        "tax": 0.0,
        "total": total,
        "currency": CURRENCY,
        "item_count": sum(int(i.quantity) for i in items),
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/items")
async def get_cart(
    user_claims: dict[str, object] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """当前用户购物车内容与金额汇总。"""
    owner_id = await _current_owner_id(user_claims, db)
    items = await SQLAlchemyCartRepository.list_by_user(db, owner_id)
    return _cart_summary(items)


@router.post("/items")
async def add_cart_item(
    payload: CartItemIn,
    user_claims: dict[str, object] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """加购：价格/名称/主图以服务端商品快照为准，重复商品自动累加数量。"""
    owner_id = await _current_owner_id(user_claims, db)
    product = await SQLAlchemyProductRepository.get_by_id(db, payload.product_id)
    if product is None or (product.status or "").lower() != "active":
        raise APIError(ErrorCode.PRODUCT_UNAVAILABLE, message="Product is not available for purchase.")
    item = await SQLAlchemyCartRepository.add_item(
        db,
        owner_id,
        {
            "id": int(product.id),
            "name": product.name,
            "price": float(product.price),
            "image": _product_image(product),
        },
        payload.quantity,
    )
    await db.commit()
    return _cart_item_dict(item)


@router.put("/items/{item_id}")
async def update_cart_item(
    item_id: str,
    payload: CartItemUpdate,
    user_claims: dict[str, object] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    owner_id = await _current_owner_id(user_claims, db)
    try:
        parsed = UUID(item_id)
    except ValueError:
        raise APIError(ErrorCode.CART_ITEM_NOT_FOUND, message="Cart item does not exist.") from None
    item = await SQLAlchemyCartRepository.get_for_user(db, owner_id, parsed)
    if item is None:
        raise APIError(ErrorCode.CART_ITEM_NOT_FOUND, message="Cart item does not exist.")
    updated = await SQLAlchemyCartRepository.update_quantity(db, owner_id, parsed, payload.quantity)
    if updated is None:
        raise APIError(ErrorCode.CART_ITEM_NOT_FOUND, message="Cart item does not exist.")
    await db.commit()
    return _cart_item_dict(updated)


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_cart_item(
    item_id: str,
    user_claims: dict[str, object] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    owner_id = await _current_owner_id(user_claims, db)
    try:
        parsed = UUID(item_id)
    except ValueError:
        raise APIError(ErrorCode.CART_ITEM_NOT_FOUND, message="Cart item does not exist.") from None
    item = await SQLAlchemyCartRepository.get_for_user(db, owner_id, parsed)
    if item is None:
        raise APIError(ErrorCode.CART_ITEM_NOT_FOUND, message="Cart item does not exist.")
    await SQLAlchemyCartRepository.remove(db, owner_id, parsed)
    await db.commit()


@router.delete("/items", status_code=status.HTTP_204_NO_CONTENT)
async def clear_cart(
    user_claims: dict[str, object] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    owner_id = await _current_owner_id(user_claims, db)
    await SQLAlchemyCartRepository.clear_for_user(db, owner_id)
    await db.commit()
