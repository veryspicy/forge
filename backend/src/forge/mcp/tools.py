"""MCP Tools — 9 个对外暴露的工具。

每个工具为纯 async 函数，自建 DB session，返回可 JSON 序列化 dict。
鉴权与审计由 server.py 中的包装层统一处理。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, or_, select

from forge.infrastructure.persistence.models import ORMOrder, ORMProduct, ORMSupplier
from forge.main.dependencies import async_session_factory

# ---------------------------------------------------------------------------
# 内部 helper
# ---------------------------------------------------------------------------


async def _list_products(
    category: str | None = None,
    status: str | None = None,
    search: str | None = None,
    supplier_id: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    if page < 1:
        page = 1
    page_size = max(1, min(page_size, 100))
    filters = []
    if category:
        filters.append(ORMProduct.category == category)
    if status:
        filters.append(ORMProduct.status == status)
    if search:
        pattern = f"%{search}%"
        filters.append(or_(ORMProduct.name.ilike(pattern), ORMProduct.sku.ilike(pattern)))
    if supplier_id:
        filters.append(ORMProduct.supplier_id == supplier_id)

    async with async_session_factory() as session:
        total = (await session.execute(select(func.count(ORMProduct.id)).where(*filters))).scalar_one()
        result = await session.execute(
            select(ORMProduct)
            .where(*filters)
            .order_by(ORMProduct.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = [p.to_dict() for p in result.scalars().all()]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


async def _get_product(product_id: str) -> dict[str, Any] | None:
    async with async_session_factory() as session:
        result = await session.execute(select(ORMProduct).where(ORMProduct.id == product_id))
        p = result.scalar_one_or_none()
        return p.to_dict() if p else None


async def _create_product(
    name: str,
    category: str,
    price: float,
    cost: float = 0.0,
    sku: str | None = None,
    description: str | None = None,
    inventory: int = 0,
    images: list[str] | None = None,
    supplier_id: str | None = None,
    supplier_sku: str | None = None,
) -> dict[str, Any]:
    if not name or not category:
        raise ValueError("name and category are required")
    if price <= 0:
        raise ValueError("price must be positive")
    if cost < 0:
        raise ValueError("cost must be non-negative")
    if inventory < 0:
        raise ValueError("inventory must be non-negative")
    if len(images or []) > 20:
        raise ValueError("too many images (max 20)")

    sku = sku or f"MCP-{int(datetime.now().timestamp() * 1000)}"
    slug = f"{sku.lower()}-{int(datetime.now().timestamp())}"
    images_payload = [{"url": u} for u in (images or [])]

    async with async_session_factory() as session:
        product = ORMProduct(
            sku=sku,
            slug=slug,
            name=name,
            category=category,
            price=price,
            cost=cost,
            description=description,
            inventory=inventory,
            status="draft",  # 安全约束：创建商品强制 draft
            images=images_payload,
            supplier_id=supplier_id,
            supplier_sku=supplier_sku,
        )
        session.add(product)
        await session.commit()
        await session.refresh(product)
        return product.to_dict()


async def _update_product(product_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
    allowed = {
        "name",
        "description",
        "category",
        "price",
        "cost",
        "inventory",
        "status",
        "images",
        "supplier_id",
        "supplier_sku",
        "seo_title",
        "seo_description",
        "seo_keywords",
    }
    unknown = set(updates) - allowed
    if unknown:
        raise ValueError(f"unsupported fields: {sorted(unknown)}")

    async with async_session_factory() as session:
        result = await session.execute(select(ORMProduct).where(ORMProduct.id == product_id))
        product = result.scalar_one_or_none()
        if product is None:
            return None
        for k, v in updates.items():
            if k == "images" and isinstance(v, list):
                v = [{"url": u} if isinstance(u, str) else u for u in v]
            setattr(product, k, v)
        await session.commit()
        await session.refresh(product)
        return product.to_dict()


async def _update_product_price(product_id: str, price: float, cost: float | None = None) -> dict[str, Any] | None:
    if price <= 0:
        raise ValueError("price must be positive")
    updates: dict[str, Any] = {"price": price}
    if cost is not None:
        if cost < 0:
            raise ValueError("cost must be non-negative")
        updates["cost"] = cost
    return await _update_product(product_id, updates)


async def _set_product_status(product_id: str, status: str) -> dict[str, Any] | None:
    if status not in ("draft", "active", "inactive"):
        raise ValueError("status must be one of draft/active/inactive")
    return await _update_product(product_id, {"status": status})


async def _batch_create_products(products: list[dict[str, Any]]) -> dict[str, Any]:
    if not products:
        raise ValueError("products list is empty")
    if len(products) > 50:
        raise ValueError("batch limit is 50")

    created: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for i, item in enumerate(products):
        try:
            created.append(await _create_product(**item))
        except Exception as e:  # noqa: BLE001
            errors.append({"index": i, "error": str(e)})

    return {"created": len(created), "errors": errors, "items": created}


async def _list_suppliers(
    search: str | None = None,
    is_active: bool | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    if page < 1:
        page = 1
    page_size = max(1, min(page_size, 100))
    filters = []
    if search:
        filters.append(ORMSupplier.name.ilike(f"%{search}%"))
    if is_active is not None:
        filters.append(ORMSupplier.is_active == is_active)  # type: ignore[arg-type]

    async with async_session_factory() as session:
        total = (await session.execute(select(func.count(ORMSupplier.id)).where(*filters))).scalar_one()
        result = await session.execute(
            select(ORMSupplier)
            .where(*filters)
            .order_by(ORMSupplier.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = [s.to_dict() for s in result.scalars().all()]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


async def _get_supplier_products(supplier_id: str, page: int = 1, page_size: int = 20) -> dict[str, Any]:
    return await _list_products(supplier_id=supplier_id, page=page, page_size=page_size)


async def _get_sales_stats(days: int = 30, category: str | None = None) -> dict[str, Any]:
    """基于订单表的销售统计（简化实现：订单数/金额聚合）。"""
    if days < 1 or days > 365:
        raise ValueError("days must be between 1 and 365")
    since = datetime.now().replace(microsecond=0) - timedelta(days=days)

    filters = [ORMOrder.created_at >= since]

    async with async_session_factory() as session:
        count = (await session.execute(select(func.count(ORMOrder.id)).where(*filters))).scalar_one()
        total = (await session.execute(select(func.coalesce(func.sum(ORMOrder.total), 0)).where(*filters))).scalar_one()
        # 按状态分布
        rows = await session.execute(
            select(ORMOrder.status, func.count(ORMOrder.id)).where(*filters).group_by(ORMOrder.status)
        )
        by_status = {status: int(c) for status, c in rows.all()}
    return {
        "days": days,
        "order_count": int(count),
        "total_amount": float(total),
        "by_status": by_status,
        "category": category,
    }


# ---------------------------------------------------------------------------
# 工具注册表：name -> (fn, description)
# ---------------------------------------------------------------------------

TOOLS: dict[str, tuple[Any, str]] = {
    "create_product": (
        _create_product,
        "创建商品（草稿状态）。参数：name, category, price, cost, sku, description,"
        " inventory, images, supplier_id, supplier_sku",
    ),
    "update_product": (
        _update_product,
        "更新商品信息。参数：product_id + 任意可更新字段"
        "（name/description/category/price/cost/inventory/images/"
        "supplier_id/supplier_sku/seo_title/seo_description/seo_keywords）",
    ),
    "list_products": (
        _list_products,
        "查询商品列表。参数：category, status, search, supplier_id, page, page_size",
    ),
    "update_product_price": (
        _update_product_price,
        "更新商品定价。参数：product_id, price, cost(可选)",
    ),
    "set_product_status": (
        _set_product_status,
        "商品上下架。参数：product_id, status(draft/active/inactive)",
    ),
    "batch_create_products": (
        _batch_create_products,
        "批量创建商品（单次上限50）。参数：products 数组",
    ),
    "list_suppliers": (
        _list_suppliers,
        "查询供应商列表。参数：search, is_active, page, page_size",
    ),
    "get_supplier_products": (
        _get_supplier_products,
        "查询某供应商的商品。参数：supplier_id, page, page_size",
    ),
    "get_sales_stats": (
        _get_sales_stats,
        "获取销售统计。参数：days(1-365), category(可选)",
    ),
}
