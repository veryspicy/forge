"""Admin - 商品目录 API（分类树 / 轻量品牌 / 商品类型规格模板）。

商品体系改造（PRODUCT-CATALOG-REFACTOR）新增目录侧管理接口。
权限点复用 products 资源（view/create/edit/delete）。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from forge.infrastructure.persistence.repositories.catalog_repo import (
    BrandRepository,
    CategoryRepository,
    ProductTypeRepository,
)
from forge.main.dependencies import get_db
from forge.main.rbac import require_permission

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic 模型
# ---------------------------------------------------------------------------
class CategoryCreate(BaseModel):
    name: str
    slug: str | None = None
    parent_id: int | None = None
    icon: str | None = None
    sort: int | None = 0
    status: str | None = "active"


class CategoryUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    parent_id: int | None = None
    icon: str | None = None
    sort: int | None = None
    status: str | None = None


class BrandCreate(BaseModel):
    name: str
    logo: str | None = None
    show_status: bool | None = True
    sort: int | None = 0


class BrandUpdate(BaseModel):
    name: str | None = None
    logo: str | None = None
    show_status: bool | None = None
    sort: int | None = None


class ProductTypeSpecIn(BaseModel):
    spec_key: str
    sort: int | None = 0


class ProductTypeCreate(BaseModel):
    name: str
    status: str | None = "active"
    sort: int | None = 0
    specs: list[ProductTypeSpecIn] | None = None


class ProductTypeUpdate(BaseModel):
    name: str | None = None
    status: str | None = None
    sort: int | None = None
    specs: list[ProductTypeSpecIn] | None = None


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
def _coerce_catalog_id(value: str, field: str = "ID") -> int:
    try:
        return int(str(value))
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail=f"无效的{field}") from None


def _clean_payload(data: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in data.items() if v is not None}


async def _unique_category_slug(db: AsyncSession, base: str) -> str:
    candidate = base
    suffix = 2
    while True:
        existing = await CategoryRepository.get_by_slug(db, candidate)
        if existing is None:
            return candidate
        candidate = f"{base}-{suffix}"
        suffix += 1


# ---------------------------------------------------------------------------
# 1. 分类树
# ---------------------------------------------------------------------------
def _build_category_tree(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """按 parent_id 组装二级树（parent_id=None 为一级；其余挂到父节点 children）。"""
    nodes: dict[int, dict[str, Any]] = {int(i["id"]): dict(i) for i in items}
    for node in nodes.values():
        node["children"] = []
    roots: list[dict[str, Any]] = []
    for node in nodes.values():
        pid = node.get("parent_id")
        if pid is not None and int(pid) in nodes:
            nodes[int(pid)]["children"].append(node)
        else:
            roots.append(node)
    return roots


@router.get("/categories")
async def list_categories(
    admin: dict[str, Any] = Depends(require_permission("products", "view")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    categories = await CategoryRepository.list_all(db)
    tree = _build_category_tree([c.to_dict() for c in categories])
    return {"data": tree, "total": len(categories)}


@router.post("/categories", status_code=201)
async def create_category(
    payload: CategoryCreate,
    admin: dict[str, Any] = Depends(require_permission("products", "create")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    data = payload.model_dump()
    name = str(data["name"]).strip()
    if not name:
        raise HTTPException(status_code=400, detail="分类名称不能为空")
    if data.get("parent_id") is not None:
        parent = await CategoryRepository.get_by_id(db, int(data["parent_id"]))
        if parent is None:
            raise HTTPException(status_code=400, detail="父分类不存在")
        data["level"] = 2
    else:
        data["parent_id"] = None
        data["level"] = 1

    slug = str(data.get("slug") or "").strip()
    if not slug:
        from forge.application.services.product_service import ProductService

        slug = await _unique_category_slug(db, ProductService.slugify(name))
    elif await CategoryRepository.get_by_slug(db, slug):
        raise HTTPException(status_code=400, detail=f"分类 slug 已存在: {slug}")
    data["slug"] = slug

    category = await CategoryRepository.create(db, {k: v for k, v in data.items() if k != "children"})
    await db.commit()
    return {"data": category.to_dict()}


@router.patch("/categories/{category_id}")
async def update_category(
    category_id: str,
    payload: CategoryUpdate,
    admin: dict[str, Any] = Depends(require_permission("products", "edit")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    cid = _coerce_catalog_id(category_id, "分类 ID")
    category = await CategoryRepository.get_by_id(db, cid)
    if category is None:
        raise HTTPException(status_code=404, detail="分类不存在")

    data = _clean_payload(payload.model_dump())
    if not data:
        raise HTTPException(status_code=400, detail="无更新字段")

    if "name" in data:
        data["name"] = str(data["name"]).strip()
        if not data["name"]:
            raise HTTPException(status_code=400, detail="分类名称不能为空")

    if "slug" in data and data["slug"]:
        slug = str(data["slug"]).strip()
        existing = await CategoryRepository.get_by_slug(db, slug)
        if existing and int(existing.id) != cid:
            raise HTTPException(status_code=400, detail=f"分类 slug 已存在: {slug}")
        data["slug"] = slug

    if "parent_id" in data:
        if data["parent_id"] is not None:
            if int(data["parent_id"]) == cid:
                raise HTTPException(status_code=400, detail="父分类不能是自己")
            parent = await CategoryRepository.get_by_id(db, int(data["parent_id"]))
            if parent is None:
                raise HTTPException(status_code=400, detail="父分类不存在")
            data["level"] = 2
        else:
            data["level"] = 1

    category = await CategoryRepository.update(db, category, data)
    await db.commit()
    return {"data": category.to_dict()}


@router.delete("/categories/{category_id}")
async def delete_category(
    category_id: str,
    admin: dict[str, Any] = Depends(require_permission("products", "delete")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    cid = _coerce_catalog_id(category_id, "分类 ID")
    category = await CategoryRepository.get_by_id(db, cid)
    if category is None:
        raise HTTPException(status_code=404, detail="分类不存在")
    children = await CategoryRepository.count_children(db, cid)
    if children > 0:
        raise HTTPException(status_code=400, detail="存在子分类，请先删除或移动子分类")

    # 商品引用保护：分类被商品引用时禁止删除
    from sqlalchemy import func, select

    from forge.infrastructure.persistence.models import ORMProduct

    ref_count = (
        await db.execute(select(func.count(ORMProduct.id)).where(ORMProduct.category_id == cid))
    ).scalar_one()
    if ref_count > 0:
        raise HTTPException(status_code=400, detail=f"仍有 {ref_count} 个商品使用该分类，请先调整商品分类")

    await db.delete(category)
    await db.commit()
    return {"data": {"id": cid, "deleted": True}}


# ---------------------------------------------------------------------------
# 2. 轻量品牌
# ---------------------------------------------------------------------------
@router.get("/brands")
async def list_brands(
    admin: dict[str, Any] = Depends(require_permission("products", "view")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    brands = await BrandRepository.list_all(db)
    return {"data": [b.to_dict() for b in brands]}


@router.post("/brands", status_code=201)
async def create_brand(
    payload: BrandCreate,
    admin: dict[str, Any] = Depends(require_permission("products", "create")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    data = payload.model_dump()
    name = str(data["name"]).strip()
    if not name:
        raise HTTPException(status_code=400, detail="品牌名称不能为空")
    if await BrandRepository.get_by_name(db, name):
        raise HTTPException(status_code=400, detail=f"品牌已存在: {name}")
    data["name"] = name

    brand = await BrandRepository.create(db, data)
    await db.commit()
    return {"data": brand.to_dict()}


@router.patch("/brands/{brand_id}")
async def update_brand(
    brand_id: str,
    payload: BrandUpdate,
    admin: dict[str, Any] = Depends(require_permission("products", "edit")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    bid = _coerce_catalog_id(brand_id, "品牌 ID")
    brand = await BrandRepository.get_by_id(db, bid)
    if brand is None:
        raise HTTPException(status_code=404, detail="品牌不存在")

    data = _clean_payload(payload.model_dump())
    if not data:
        raise HTTPException(status_code=400, detail="无更新字段")

    if "name" in data:
        name = str(data["name"]).strip()
        if not name:
            raise HTTPException(status_code=400, detail="品牌名称不能为空")
        existing = await BrandRepository.get_by_name(db, name)
        if existing and int(existing.id) != bid:
            raise HTTPException(status_code=400, detail=f"品牌已存在: {name}")
        data["name"] = name

    brand = await BrandRepository.update(db, brand, data)
    await db.commit()
    return {"data": brand.to_dict()}


@router.delete("/brands/{brand_id}")
async def delete_brand(
    brand_id: str,
    admin: dict[str, Any] = Depends(require_permission("products", "delete")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    bid = _coerce_catalog_id(brand_id, "品牌 ID")
    brand = await BrandRepository.get_by_id(db, bid)
    if brand is None:
        raise HTTPException(status_code=404, detail="品牌不存在")

    from sqlalchemy import func, select

    from forge.infrastructure.persistence.models import ORMProduct

    ref_count = (
        await db.execute(select(func.count(ORMProduct.id)).where(ORMProduct.brand_id == bid))
    ).scalar_one()
    if ref_count > 0:
        raise HTTPException(status_code=400, detail=f"仍有 {ref_count} 个商品使用该品牌，请先调整商品品牌")

    await db.delete(brand)
    await db.commit()
    return {"data": {"id": bid, "deleted": True}}


# ---------------------------------------------------------------------------
# 3. 商品类型 + 规格模板
# ---------------------------------------------------------------------------
async def _serialize_product_type(db: AsyncSession, product_type: Any) -> dict[str, Any]:
    data: dict[str, Any] = dict(product_type.to_dict())
    specs = await ProductTypeRepository.list_specs(db, int(product_type.id))
    data["specs"] = [s.to_dict() for s in specs]
    return data


@router.get("/product-types")
async def list_product_types(
    admin: dict[str, Any] = Depends(require_permission("products", "view")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    types = await ProductTypeRepository.list_all(db)
    items = []
    for pt in types:
        items.append(await _serialize_product_type(db, pt))
    return {"data": items, "total": len(items)}


@router.post("/product-types", status_code=201)
async def create_product_type(
    payload: ProductTypeCreate,
    admin: dict[str, Any] = Depends(require_permission("products", "create")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    data = payload.model_dump()
    name = str(data["name"]).strip()
    if not name:
        raise HTTPException(status_code=400, detail="类型名称不能为空")
    if await ProductTypeRepository.get_by_name(db, name):
        raise HTTPException(status_code=400, detail=f"商品类型已存在: {name}")
    data["name"] = name

    specs = data.pop("specs") or []
    product_type = await ProductTypeRepository.create(db, data)
    if specs:
        await ProductTypeRepository.replace_specs(db, int(product_type.id), specs)
    await db.commit()
    return {"data": await _serialize_product_type(db, product_type)}


@router.patch("/product-types/{type_id}")
async def update_product_type(
    type_id: str,
    payload: ProductTypeUpdate,
    admin: dict[str, Any] = Depends(require_permission("products", "edit")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    tid = _coerce_catalog_id(type_id, "类型 ID")
    product_type = await ProductTypeRepository.get_by_id(db, tid)
    if product_type is None:
        raise HTTPException(status_code=404, detail="商品类型不存在")

    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="无更新字段")

    specs = data.pop("specs", None)
    if "name" in data:
        name = str(data["name"]).strip()
        if not name:
            raise HTTPException(status_code=400, detail="类型名称不能为空")
        existing = await ProductTypeRepository.get_by_name(db, name)
        if existing and int(existing.id) != tid:
            raise HTTPException(status_code=400, detail=f"商品类型已存在: {name}")
        data["name"] = name

    product_type = await ProductTypeRepository.update(db, product_type, data)
    if specs is not None:
        await ProductTypeRepository.replace_specs(db, tid, specs)
    await db.commit()
    return {"data": await _serialize_product_type(db, product_type)}


@router.delete("/product-types/{type_id}")
async def delete_product_type(
    type_id: str,
    admin: dict[str, Any] = Depends(require_permission("products", "delete")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    tid = _coerce_catalog_id(type_id, "类型 ID")
    product_type = await ProductTypeRepository.get_by_id(db, tid)
    if product_type is None:
        raise HTTPException(status_code=404, detail="商品类型不存在")

    from sqlalchemy import func, select

    from forge.infrastructure.persistence.models import ORMProduct

    ref_count = (
        await db.execute(select(func.count(ORMProduct.id)).where(ORMProduct.product_type_id == tid))
    ).scalar_one()
    if ref_count > 0:
        raise HTTPException(status_code=400, detail=f"仍有 {ref_count} 个商品使用该类型，请先调整商品类型")

    await db.delete(product_type)
    await db.commit()
    return {"data": {"id": tid, "deleted": True}}
