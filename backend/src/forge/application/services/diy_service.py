"""DIY 页面装修 — Application Service。

封装页面 CRUD、发布/撤销发布、渲染数据组装（enrich）与 Redis 缓存。
Redis 不可用时优雅降级为直查数据库。
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from forge.infrastructure.persistence.models import ORMDiyPage, ORMProduct
from forge.infrastructure.persistence.repositories.diy_repo import (
    SQLAlchemyDiyRepository,
)
from forge.main.config import settings

logger = logging.getLogger(__name__)

CACHE_TTL = 3600
CACHE_KEY_PREFIX = "diy:page:"
CACHE_KEY_DEFAULT = "diy:page:default"

_redis_client = None
_redis_unavailable = False


async def get_redis():
    """惰性初始化 Redis 客户端；不可用（未安装/连接失败）时返回 None。"""
    global _redis_client, _redis_unavailable
    if _redis_unavailable:
        return None
    if _redis_client is None:
        try:
            import redis.asyncio as aioredis

            _redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
            await _redis_client.ping()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Redis unavailable for DIY cache: %s", exc)
            _redis_unavailable = True
            _redis_client = None
            return None
    return _redis_client


class DiyService:
    """DIY 页面业务逻辑。"""

    def __init__(self, repo: Optional[SQLAlchemyDiyRepository] = None) -> None:
        self.repo = repo or SQLAlchemyDiyRepository()

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create_page(self, db: AsyncSession, data: dict) -> ORMDiyPage:
        return await self.repo.create_page(db, data)

    async def publish_page(self, db: AsyncSession, page_id: UUID) -> Optional[ORMDiyPage]:
        page = await db.get(ORMDiyPage, page_id)
        if not page:
            return None
        page.status = "published"
        page.published_at = datetime.now(timezone.utc)
        await db.flush()

        # 写入渲染缓存（enrich 后数据）
        try:
            payload = await self.get_page_for_render(db, page.slug, preview=True)
            redis = await get_redis()
            if redis:
                await redis.set(f"{CACHE_KEY_PREFIX}{page.slug}", json.dumps(payload), ex=CACHE_TTL)
                if page.page_type != "custom":
                    await redis.set(f"{CACHE_KEY_PREFIX}{page.page_type}", json.dumps(payload), ex=CACHE_TTL)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to warm DIY cache on publish: %s", exc)

        return await self.repo.get_page_by_id(db, page_id)

    async def unpublish_page(self, db: AsyncSession, page_id: UUID) -> Optional[ORMDiyPage]:
        page = await db.get(ORMDiyPage, page_id)
        if not page:
            return None
        page.status = "draft"
        await db.flush()

        await self.invalidate_page_cache(page.slug, page.page_type)
        return await self.repo.get_page_by_id(db, page_id)

    @staticmethod
    async def invalidate_page_cache(slug: str, page_type: str = "") -> None:
        """清除页面渲染缓存（slug + page_type 两个 key）。"""
        try:
            redis = await get_redis()
            if redis:
                keys = [f"{CACHE_KEY_PREFIX}{slug}"]
                if page_type and page_type != "custom" and page_type != slug:
                    keys.append(f"{CACHE_KEY_PREFIX}{page_type}")
                await redis.delete(*keys)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to invalidate DIY cache: %s", exc)

    async def duplicate_page(self, db: AsyncSession, page_id: UUID) -> Optional[ORMDiyPage]:
        source = await self.repo.get_page_by_id(db, page_id)
        if not source:
            return None

        suffix = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        new_page = await self.repo.create_page(
            db,
            {
                "name": f"{source.name} (Copy)",
                "slug": f"{source.slug}-copy-{suffix}",
                "title": source.title,
                "description": source.description,
                "page_type": source.page_type,
            },
        )
        from types import SimpleNamespace

        items = [
            SimpleNamespace(
                component_id=comp.component_id,
                sort_order=comp.sort_order,
                config=comp.config or {},
                is_visible=comp.is_visible,
            )
            for comp in source.components or []
        ]
        if items:
            await self.repo.save_components(db, new_page.id, items)
        return await self.repo.get_page_by_id(db, new_page.id)

    async def set_default(self, db: AsyncSession, page_id: UUID) -> Optional[ORMDiyPage]:
        page = await self.repo.set_default(db, page_id)
        if page:
            # 刷新默认首页缓存
            try:
                redis = await get_redis()
                if redis:
                    payload = await self.get_page_for_render(db, page.slug, preview=True)
                    await redis.set(CACHE_KEY_DEFAULT, json.dumps(payload), ex=CACHE_TTL)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to refresh default DIY cache: %s", exc)
        return page

    # ------------------------------------------------------------------
    # 渲染数据组装
    # ------------------------------------------------------------------

    async def _query_products(
        self,
        db: AsyncSession,
        ids: Optional[list[str]] = None,
        category: Optional[str] = None,
        limit: int = 6,
    ) -> list[dict]:
        stmt = select(ORMProduct)
        if ids:
            valid_ids = []
            for raw in ids:
                try:
                    valid_ids.append(UUID(str(raw)))
                except (ValueError, TypeError):
                    continue
            if not valid_ids:
                return []
            stmt = stmt.where(ORMProduct.id.in_(valid_ids))
        elif category:
            stmt = stmt.where(ORMProduct.category == category)
        stmt = stmt.limit(limit)
        result = await db.execute(stmt)
        products = result.scalars().all()
        items = [p.to_dict() for p in products]
        # 手动选品时保持 productIds 的顺序
        if ids:
            order = {str(pid): idx for idx, pid in enumerate(ids)}
            items.sort(key=lambda p: order.get(p["id"], 999))
        return items

    async def enrich_page_data(self, db: AsyncSession, page_dict: dict) -> dict:
        """遍历页面组件，为需要数据内联的组件类型填充 data 字段。"""
        for comp in page_dict.get("components", []):
            code = comp.get("component_code")
            config = comp.get("config") or {}
            comp["data"] = {}

            try:
                if code == "goods_list":
                    source = config.get("source", "manual")
                    limit = int(config.get("displayCount") or 6)
                    if source == "manual":
                        products = await self._query_products(
                            db, ids=config.get("productIds") or [], limit=limit
                        )
                    elif source == "category":
                        products = await self._query_products(
                            db, category=config.get("category") or None, limit=limit
                        )
                    else:  # ai_recommend — 预留，暂用最新商品
                        products = await self._query_products(db, limit=limit)
                    comp["data"]["products"] = products

                elif code == "goods_single":
                    product_id = config.get("productId")
                    products = (
                        await self._query_products(db, ids=[product_id], limit=1) if product_id else []
                    )
                    comp["data"]["product"] = products[0] if products else None

                elif code == "goods_group":
                    tabs_data = []
                    limit = int(config.get("displayCount") or 4)
                    for tab in config.get("tabs") or []:
                        products = await self._query_products(
                            db, category=tab.get("category") or None, limit=limit
                        )
                        tabs_data.append({"name": tab.get("name", ""), "products": products})
                    comp["data"]["tabs"] = tabs_data

                elif code == "coupon":
                    # 优惠券功能尚未上线 — 占位
                    comp["data"]["coupon"] = None
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to enrich component %s: %s", code, exc)

        return page_dict

    # ------------------------------------------------------------------
    # 渲染入口（缓存读路径）
    # ------------------------------------------------------------------

    async def get_page_for_render(
        self,
        db: AsyncSession,
        slug: str,
        preview: bool = False,
    ) -> Optional[dict]:
        """获取页面渲染数据。

        preview=True  — 直查 DB（含 draft）+ enrich，不读/写 Redis。
        preview=False — 仅已发布页面；优先 Redis，miss 时查 DB → enrich → 回填。
        """
        cache_key = f"{CACHE_KEY_PREFIX}{slug}"

        if not preview:
            try:
                redis = await get_redis()
                if redis:
                    cached = await redis.get(cache_key)
                    if cached:
                        return json.loads(cached)
            except Exception as exc:  # noqa: BLE001
                logger.warning("DIY cache read failed: %s", exc)

        page = await self.repo.get_page_by_slug(db, slug)
        if not page:
            return None
        if not preview and page.status != "published":
            return None

        payload = await self.enrich_page_data(db, page.to_dict())

        if not preview:
            try:
                redis = await get_redis()
                if redis:
                    await redis.set(cache_key, json.dumps(payload), ex=CACHE_TTL)
            except Exception as exc:  # noqa: BLE001
                logger.warning("DIY cache write failed: %s", exc)

        return payload

    async def get_default_for_render(self, db: AsyncSession) -> Optional[dict]:
        """获取默认首页渲染数据（v1 兼容：转为 home 页面）。"""
        return await self.get_page_for_render_by_type(db, "home")

    async def get_page_for_render_by_type(
        self,
        db: AsyncSession,
        page_type: str,
        preview: bool = False,
    ) -> Optional[dict]:
        """按 page_type 获取系统页面渲染数据（v2.0）。

        缓存 key: diy:page:{page_type}
        """
        cache_key = f"{CACHE_KEY_PREFIX}{page_type}"

        if not preview:
            try:
                redis = await get_redis()
                if redis:
                    cached = await redis.get(cache_key)
                    if cached:
                        return json.loads(cached)
            except Exception as exc:  # noqa: BLE001
                logger.warning("DIY cache read failed: %s", exc)

        page = await self.repo.get_page_by_type(db, page_type)
        if not page:
            return None
        if not preview and page.status != "published":
            return None

        payload = await self.enrich_page_data(db, page.to_dict())

        if not preview:
            try:
                redis = await get_redis()
                if redis:
                    await redis.set(cache_key, json.dumps(payload), ex=CACHE_TTL)
            except Exception as exc:  # noqa: BLE001
                logger.warning("DIY cache write failed: %s", exc)

        return payload

    # ------------------------------------------------------------------
    # 模板
    # ------------------------------------------------------------------

    async def save_as_template(
        self,
        db: AsyncSession,
        name: str,
        industry_tag: Optional[str] = None,
        template_description: Optional[str] = None,
        template_thumbnail: Optional[str] = None,
    ) -> ORMDiyPage:
        """当前站点（三套系统页面组件 + 站点配置）保存为模板。"""
        from forge.application.services.site_config_service import SiteConfigService

        pages_snapshot: dict[str, list] = {}
        for page_type in ("home", "category", "product_detail"):
            page = await self.repo.get_page_by_type(db, page_type)
            pages_snapshot[page_type] = (
                [
                    {
                        "component_code": c.component.code if c.component else None,
                        "component_id": str(c.component_id),
                        "sort_order": c.sort_order,
                        "config": c.config or {},
                        "is_visible": c.is_visible,
                    }
                    for c in (page.components or [])
                ]
                if page
                else []
            )

        site_config = await SiteConfigService().get_active_config(db)

        slug = f"template-{uuid4().hex[:12]}"
        return await self.repo.create_page(
            db,
            {
                "name": name,
                "slug": slug,
                "title": name,
                "description": template_description or "",
                "page_type": "home",
                "status": "published",
                "is_template": True,
                "industry_tag": industry_tag,
                "template_thumbnail": template_thumbnail,
                "template_description": template_description,
                "snapshot_config": {
                    "pages": pages_snapshot,
                    "site_config": site_config,
                },
            },
        )

    async def apply_template(self, db: AsyncSession, template_id: UUID) -> bool:
        """应用模板：替换三套系统页面组件 + 站点配置。"""
        from types import SimpleNamespace

        from forge.application.services.site_config_service import SiteConfigService
        from forge.infrastructure.persistence.models import ORMDiyComponent

        template = await self.repo.get_template(db, template_id)
        if not template:
            return False

        snapshot = template.snapshot_config or {}
        pages_snapshot = snapshot.get("pages") or {}

        # component_code -> id 映射
        result = await db.execute(select(ORMDiyComponent))
        code_map = {c.code: c.id for c in result.scalars().all()}

        for page_type in ("home", "category", "product_detail"):
            page = await self.repo.get_page_by_type(db, page_type)
            if not page:
                continue
            items = []
            for idx, comp in enumerate(pages_snapshot.get(page_type) or []):
                component_id = code_map.get(comp.get("component_code"))
                if not component_id and comp.get("component_id"):
                    try:
                        component_id = UUID(str(comp["component_id"]))
                    except (ValueError, TypeError):
                        component_id = None
                if not component_id:
                    continue
                items.append(
                    SimpleNamespace(
                        component_id=component_id,
                        sort_order=comp.get("sort_order", idx),
                        config=comp.get("config") or {},
                        is_visible=comp.get("is_visible", True),
                    )
                )
            await self.repo.save_components(db, page.id, items)
            # 应用后自动发布
            page.status = "published"
            page.published_at = datetime.now(timezone.utc)
            await db.flush()
            await self.invalidate_page_cache(page.slug, page_type)

        site_config = snapshot.get("site_config")
        if site_config:
            await SiteConfigService().replace_config(db, site_config)

        return True
