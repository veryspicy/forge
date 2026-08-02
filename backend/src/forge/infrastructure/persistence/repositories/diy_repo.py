"""DIY 页面装修 — SQLAlchemy Repository。"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from forge.infrastructure.persistence.models import (
    ORMDiyComponent,
    ORMDiyPage,
    ORMDiyPageComponent,
)


class SQLAlchemyDiyRepository:
    """DIY 页面/组件的数据库访问封装。"""

    @staticmethod
    def _page_load_options():
        return [selectinload(ORMDiyPage.components).joinedload(ORMDiyPageComponent.component)]

    async def get_page_by_slug(self, db: AsyncSession, slug: str) -> Optional[ORMDiyPage]:
        stmt = (
            select(ORMDiyPage)
            .options(*self._page_load_options())
            .where(ORMDiyPage.slug == slug)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_page_by_id(self, db: AsyncSession, page_id: UUID) -> Optional[ORMDiyPage]:
        stmt = (
            select(ORMDiyPage)
            .options(*self._page_load_options())
            .where(ORMDiyPage.id == page_id)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_page_by_type(self, db: AsyncSession, page_type: str) -> Optional[ORMDiyPage]:
        """按 page_type 获取系统页面（非模板）。"""
        stmt = (
            select(ORMDiyPage)
            .options(*self._page_load_options())
            .where(ORMDiyPage.page_type == page_type, ORMDiyPage.is_template.is_(False))
            .limit(1)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_site_pages(self, db: AsyncSession) -> dict:
        """站点编辑器页面概览：系统页面卡片 + 自定义页面列表。"""
        stmt = (
            select(ORMDiyPage)
            .options(*self._page_load_options())
            .where(ORMDiyPage.is_template.is_(False))
            .order_by(ORMDiyPage.updated_at.desc())
        )
        result = await db.execute(stmt)
        pages = list(result.scalars().all())

        system_types = ["home", "category", "product_detail"]
        by_type = {p.page_type: p for p in pages if p.page_type in system_types}
        system = []
        for pt in system_types:
            page = by_type.get(pt)
            if page:
                system.append(
                    {
                        "id": str(page.id),
                        "page_type": pt,
                        "name": page.name,
                        "slug": page.slug,
                        "status": page.status,
                        "components_count": len(page.components or []),
                        "updated_at": page.updated_at.isoformat() if page.updated_at else None,
                    }
                )
            else:
                system.append(
                    {
                        "id": None,
                        "page_type": pt,
                        "name": pt,
                        "slug": pt,
                        "status": "not_initialized",
                        "components_count": 0,
                        "updated_at": None,
                    }
                )

        custom = [
            {
                "id": str(p.id),
                "name": p.name,
                "slug": p.slug,
                "title": p.title,
                "status": p.status,
                "components_count": len(p.components or []),
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            }
            for p in pages
            if p.page_type == "custom"
        ]

        return {"system": system, "custom": custom}

    async def list_templates(
        self,
        db: AsyncSession,
        industry_tag: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        filters = [ORMDiyPage.is_template.is_(True)]
        if industry_tag:
            filters.append(ORMDiyPage.industry_tag == industry_tag)

        total_query = select(func.count(ORMDiyPage.id)).where(*filters)
        total = (await db.execute(total_query)).scalar_one()

        query = (
            select(ORMDiyPage)
            .where(*filters)
            .order_by(ORMDiyPage.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(query)
        templates = result.scalars().all()

        return {
            "items": [
                {
                    "id": str(t.id),
                    "name": t.name,
                    "industry_tag": t.industry_tag,
                    "template_thumbnail": t.template_thumbnail,
                    "template_description": t.template_description,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                }
                for t in templates
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def get_template(self, db: AsyncSession, template_id: UUID) -> Optional[ORMDiyPage]:
        stmt = (
            select(ORMDiyPage)
            .options(*self._page_load_options())
            .where(ORMDiyPage.id == template_id, ORMDiyPage.is_template.is_(True))
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_default_page(self, db: AsyncSession) -> Optional[ORMDiyPage]:
        stmt = (
            select(ORMDiyPage)
            .options(*self._page_load_options())
            .where(ORMDiyPage.is_default.is_(True))
            .limit(1)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_pages(
        self,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        page_type: Optional[str] = None,
    ) -> dict:
        filters = []
        if status:
            filters.append(ORMDiyPage.status == status)
        if page_type:
            filters.append(ORMDiyPage.page_type == page_type)

        total_query = select(func.count(ORMDiyPage.id)).where(*filters)
        total = (await db.execute(total_query)).scalar_one()

        query = (
            select(ORMDiyPage)
            .options(*self._page_load_options())
            .where(*filters)
            .order_by(ORMDiyPage.updated_at.desc())
        )
        result = await db.execute(query.offset((page - 1) * page_size).limit(page_size))
        pages = result.scalars().all()

        return {
            "items": [p.to_dict() for p in pages],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def create_page(self, db: AsyncSession, data: dict) -> ORMDiyPage:
        page = ORMDiyPage(**data)
        db.add(page)
        await db.flush()
        return await self.get_page_by_id(db, page.id)

    async def update_page(self, db: AsyncSession, page_id: UUID, data: dict) -> Optional[ORMDiyPage]:
        page = await db.get(ORMDiyPage, page_id)
        if not page:
            return None
        for key, value in data.items():
            if value is not None:
                setattr(page, key, value)
        await db.flush()
        return await self.get_page_by_id(db, page_id)

    async def delete_page(self, db: AsyncSession, page_id: UUID) -> bool:
        page = await db.get(ORMDiyPage, page_id)
        if not page:
            return False
        await db.delete(page)
        await db.flush()
        return True

    async def get_components(self, db: AsyncSession) -> list[ORMDiyComponent]:
        stmt = (
            select(ORMDiyComponent)
            .where(ORMDiyComponent.is_active.is_(True))
            .order_by(ORMDiyComponent.sort_order.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def save_components(
        self,
        db: AsyncSession,
        page_id: UUID,
        components: list,
    ) -> int:
        """整页保存组件列表 — 先删后插。"""
        await db.execute(
            delete(ORMDiyPageComponent).where(ORMDiyPageComponent.page_id == page_id)
        )
        for item in components:
            pc = ORMDiyPageComponent(
                page_id=page_id,
                component_id=item.component_id,
                sort_order=item.sort_order,
                config=item.config,
                is_visible=item.is_visible,
            )
            db.add(pc)
        await db.flush()
        return len(components)

    async def set_default(self, db: AsyncSession, page_id: UUID) -> Optional[ORMDiyPage]:
        """将目标页面设为首页（全局唯一）。"""
        await db.execute(
            update(ORMDiyPage).where(ORMDiyPage.is_default.is_(True)).values(is_default=False)
        )
        page = await db.get(ORMDiyPage, page_id)
        if not page:
            return None
        page.is_default = True
        await db.flush()
        return await self.get_page_by_id(db, page_id)
