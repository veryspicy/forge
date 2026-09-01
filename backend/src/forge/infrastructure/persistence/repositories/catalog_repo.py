"""Catalog — SQLAlchemy Repository.

商品体系改造（PRODUCT-CATALOG-REFACTOR）新增的目录侧仓储：
分类树 / 轻量品牌 / 商品类型规格模板。
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from forge.infrastructure.persistence.models import (
    ORMBrand,
    ORMProduct,
    ORMProductCategory,
    ORMProductSpecKey,
    ORMProductSpecValue,
    ORMProductType,
    ORMProductTypeSpec,
    ORMProductVariant,
    ORMVariantSpec,
)


def _now() -> datetime:
    return datetime.now(UTC)


class CategoryRepository:
    """商品分类树仓储。"""

    @staticmethod
    async def list_all(db: AsyncSession) -> list[ORMProductCategory]:
        result = await db.execute(
            select(ORMProductCategory).order_by(ORMProductCategory.sort.asc(), ORMProductCategory.id.asc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_by_id(db: AsyncSession, category_id: int) -> ORMProductCategory | None:
        result = await db.execute(select(ORMProductCategory).where(ORMProductCategory.id == category_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_slug(db: AsyncSession, slug: str) -> ORMProductCategory | None:
        result = await db.execute(select(ORMProductCategory).where(ORMProductCategory.slug == slug))
        return result.scalar_one_or_none()

    @staticmethod
    async def create(db: AsyncSession, data: dict[str, Any]) -> ORMProductCategory:
        category = ORMProductCategory(**data)
        db.add(category)
        await db.flush()
        await db.refresh(category)
        return category

    @staticmethod
    async def update(
        db: AsyncSession,
        category: ORMProductCategory,
        data: dict[str, Any],
    ) -> ORMProductCategory:
        for key, value in data.items():
            if hasattr(category, key):
                setattr(category, key, value)
        category.updated_at = _now()  # type: ignore[assignment]
        await db.flush()
        await db.refresh(category)
        return category

    @staticmethod
    async def count_children(db: AsyncSession, parent_id: int) -> int:
        result = await db.execute(
            select(func.count(ORMProductCategory.id)).where(ORMProductCategory.parent_id == parent_id)
        )
        return int(result.scalar_one())


class BrandRepository:
    """轻量品牌仓储。"""

    @staticmethod
    async def list_all(db: AsyncSession) -> list[ORMBrand]:
        result = await db.execute(select(ORMBrand).order_by(ORMBrand.sort.asc(), ORMBrand.id.asc()))
        return list(result.scalars().all())

    @staticmethod
    async def get_by_id(db: AsyncSession, brand_id: int) -> ORMBrand | None:
        result = await db.execute(select(ORMBrand).where(ORMBrand.id == brand_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_name(db: AsyncSession, name: str) -> ORMBrand | None:
        result = await db.execute(select(ORMBrand).where(ORMBrand.name == name))
        return result.scalar_one_or_none()

    @staticmethod
    async def create(db: AsyncSession, data: dict[str, Any]) -> ORMBrand:
        brand = ORMBrand(**data)
        db.add(brand)
        await db.flush()
        await db.refresh(brand)
        return brand

    @staticmethod
    async def update(db: AsyncSession, brand: ORMBrand, data: dict[str, Any]) -> ORMBrand:
        for key, value in data.items():
            if hasattr(brand, key):
                setattr(brand, key, value)
        brand.updated_at = _now()  # type: ignore[assignment]
        await db.flush()
        await db.refresh(brand)
        return brand


class ProductTypeRepository:
    """商品类型 + 规格模板仓储。"""

    @staticmethod
    async def list_all(db: AsyncSession) -> list[ORMProductType]:
        result = await db.execute(select(ORMProductType).order_by(ORMProductType.sort.asc(), ORMProductType.id.asc()))
        return list(result.scalars().all())

    @staticmethod
    async def get_by_id(db: AsyncSession, type_id: int) -> ORMProductType | None:
        result = await db.execute(select(ORMProductType).where(ORMProductType.id == type_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_name(db: AsyncSession, name: str) -> ORMProductType | None:
        result = await db.execute(select(ORMProductType).where(ORMProductType.name == name))
        return result.scalar_one_or_none()

    @staticmethod
    async def create(db: AsyncSession, data: dict[str, Any]) -> ORMProductType:
        product_type = ORMProductType(**data)
        db.add(product_type)
        await db.flush()
        await db.refresh(product_type)
        return product_type

    @staticmethod
    async def update(db: AsyncSession, product_type: ORMProductType, data: dict[str, Any]) -> ORMProductType:
        for key, value in data.items():
            if hasattr(product_type, key):
                setattr(product_type, key, value)
        product_type.updated_at = _now()  # type: ignore[assignment]
        await db.flush()
        await db.refresh(product_type)
        return product_type

    # ---- 规格模板 ----
    @staticmethod
    async def list_specs(db: AsyncSession, type_id: int) -> list[ORMProductTypeSpec]:
        result = await db.execute(
            select(ORMProductTypeSpec)
            .where(ORMProductTypeSpec.product_type_id == type_id)
            .order_by(ORMProductTypeSpec.sort.asc(), ORMProductTypeSpec.id.asc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def replace_specs(db: AsyncSession, type_id: int, specs: list[dict[str, Any]]) -> None:
        """整表替换某类型的规格模板（先删后插）。"""
        await db.execute(delete(ORMProductTypeSpec).where(ORMProductTypeSpec.product_type_id == type_id))
        for idx, spec in enumerate(specs):
            db.add(
                ORMProductTypeSpec(
                    product_type_id=type_id,
                    spec_key=str(spec.get("spec_key", "")).strip(),
                    sort=int(spec.get("sort", idx)),
                )
            )
        await db.flush()


class SpecRepository:
    """SPU 规格键/值 + 变体规格关联仓储。

    规格关系表（product_spec_keys / product_spec_values / variant_specs）
    是商品规格的权威数据源，products.attributes 仅作为读快照同步维护。
    """

    # ---- 规格键 ----
    @staticmethod
    async def list_keys(db: AsyncSession, product_id: int) -> list[ORMProductSpecKey]:
        result = await db.execute(
            select(ORMProductSpecKey)
            .where(ORMProductSpecKey.product_id == product_id)
            .order_by(ORMProductSpecKey.sort.asc(), ORMProductSpecKey.id.asc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_key_by_name(db: AsyncSession, product_id: int, spec_key: str) -> ORMProductSpecKey | None:
        result = await db.execute(
            select(ORMProductSpecKey).where(
                ORMProductSpecKey.product_id == product_id,
                ORMProductSpecKey.spec_key == spec_key,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_key_by_id(db: AsyncSession, key_id: int) -> ORMProductSpecKey | None:
        result = await db.execute(select(ORMProductSpecKey).where(ORMProductSpecKey.id == key_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def ensure_key(db: AsyncSession, product_id: int, spec_key: str, sort: int = 0) -> ORMProductSpecKey:
        existing = await SpecRepository.get_key_by_name(db, product_id, spec_key)
        if existing:
            return existing
        key = ORMProductSpecKey(product_id=product_id, spec_key=spec_key, sort=sort)
        db.add(key)
        await db.flush()
        await db.refresh(key)
        return key

    @staticmethod
    async def replace_keys(db: AsyncSession, product_id: int, keys: list[str]) -> None:
        """按 SPU 规格键列表整表替换（规格键不再被使用时清理）。"""
        await db.execute(delete(ORMProductSpecKey).where(ORMProductSpecKey.product_id == product_id))
        for idx, key in enumerate(keys):
            db.add(ORMProductSpecKey(product_id=product_id, spec_key=key, sort=idx))
        await db.flush()

    # ---- 规格值 ----
    @staticmethod
    async def list_values(db: AsyncSession, key_id: int) -> list[ORMProductSpecValue]:
        result = await db.execute(
            select(ORMProductSpecValue)
            .where(ORMProductSpecValue.spec_key_id == key_id)
            .order_by(ORMProductSpecValue.sort.asc(), ORMProductSpecValue.id.asc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_value(db: AsyncSession, key_id: int, value: str) -> ORMProductSpecValue | None:
        result = await db.execute(
            select(ORMProductSpecValue).where(
                ORMProductSpecValue.spec_key_id == key_id,
                ORMProductSpecValue.value == value,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def ensure_value(db: AsyncSession, key_id: int, value: str, sort: int = 0) -> ORMProductSpecValue:
        existing = await SpecRepository.get_value(db, key_id, value)
        if existing:
            return existing
        spec_value = ORMProductSpecValue(spec_key_id=key_id, value=value, sort=sort)
        db.add(spec_value)
        await db.flush()
        await db.refresh(spec_value)
        return spec_value

    # ---- 变体规格关联 ----
    @staticmethod
    async def list_variant_specs(db: AsyncSession, variant_id: str) -> list[ORMVariantSpec]:
        result = await db.execute(select(ORMVariantSpec).where(ORMVariantSpec.variant_id == variant_id))
        return list(result.scalars().all())

    @staticmethod
    async def list_variant_spec_details(db: AsyncSession, variant_id: str) -> list[dict[str, Any]]:
        """返回变体规格详情（含键名与值），供前端行内编辑表格使用。"""
        rows = await db.execute(
            select(
                ORMProductSpecKey.spec_key,
                ORMProductSpecValue.value,
                ORMProductSpecValue.sort,
            )
            .select_from(ORMVariantSpec)
            .join(ORMProductSpecKey, ORMVariantSpec.spec_key_id == ORMProductSpecKey.id)
            .join(ORMProductSpecValue, ORMVariantSpec.spec_value_id == ORMProductSpecValue.id)
            .where(ORMVariantSpec.variant_id == variant_id)
            .order_by(ORMProductSpecValue.sort.asc(), ORMProductSpecKey.id.asc())
        )
        return [
            {
                "spec_key": str(row.spec_key),
                "value": str(row.value),
                "sort": int(row.sort or 0),
            }
            for row in rows
        ]

    @staticmethod
    async def replace_variant_specs(
        db: AsyncSession,
        variant_id: str,
        pairs: list[tuple[ORMProductSpecKey, ORMProductSpecValue]],
    ) -> None:
        """整表替换某变体的规格关联（先删后插）。"""
        await db.execute(delete(ORMVariantSpec).where(ORMVariantSpec.variant_id == variant_id))
        for key, value in pairs:
            db.add(ORMVariantSpec(variant_id=variant_id, spec_key_id=key.id, spec_value_id=value.id))
        await db.flush()

    # ---- 快照同步 ----
    @staticmethod
    async def build_product_attributes(db: AsyncSession, product_id: int) -> dict[str, Any]:
        """根据规格关系表重建 products.attributes 读快照。"""
        keys = await SpecRepository.list_keys(db, product_id)
        snapshot: dict[str, Any] = {}
        for key in keys:
            values = await SpecRepository.list_values(db, int(key.id))
            snapshot[str(key.spec_key)] = {
                "values": [str(v.value) for v in values],
                "unit": None,
            }
        return snapshot

    @staticmethod
    async def sync_product_attributes(db: AsyncSession, product_id: int) -> None:
        snapshot = await SpecRepository.build_product_attributes(db, product_id)
        await db.execute(
            update(ORMProduct).where(ORMProduct.id == product_id).values(attributes=snapshot, updated_at=_now())
        )
        await db.flush()

    @staticmethod
    async def sync_variant_attributes(db: AsyncSession, variant: ORMProductVariant, attributes: dict[str, Any]) -> None:
        """将变体 attributes 字典同步为规格关系表（权威）+ 产品快照。"""
        product_id = int(variant.product_id)
        normalized: dict[str, str] = {}
        for key, value in (attributes or {}).items():
            if value is None:
                continue
            normalized[str(key)] = str(value)

        pairs: list[tuple[ORMProductSpecKey, ORMProductSpecValue]] = []
        keys = await SpecRepository.list_keys(db, product_id)
        key_names = [str(k.spec_key) for k in keys]

        for idx, (key, value) in enumerate(normalized.items()):
            if key in key_names:
                spec_key = next(k for k in keys if str(k.spec_key) == key)
            else:
                spec_key = await SpecRepository.ensure_key(db, product_id, key, sort=len(keys) + idx)
                keys.append(spec_key)
                key_names.append(key)
            spec_value = await SpecRepository.ensure_value(db, int(spec_key.id), value, sort=0)
            pairs.append((spec_key, spec_value))

        await SpecRepository.replace_variant_specs(db, str(variant.id), pairs)
        await SpecRepository.sync_product_attributes(db, product_id)
