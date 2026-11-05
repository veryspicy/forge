"""C-end CMS Content API.

按 slug 返回已发布（status=published）的 CMS 内容页，支持按语言（locale）独立获取：
- ``?locale=<code>`` 返回对应语言内容，语言清单取自站点配置 i18n.locales；
- 未指定、语言未在站点启用、或该语言无已发布内容时，按回退链降级：
  请求语言 → 站点默认语言（i18n.defaultLocale）→ ``en``；
- 未发布或不存在一律 404，由前端降级为 Coming soon 占位。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from forge.application.services.content_service import get_supported_locales, normalise_locale
from forge.infrastructure.persistence.repositories.content_repo import SQLAlchemyContentRepository
from forge.main.dependencies import get_db

router = APIRouter(tags=["C-end Content"])


@router.get("/content/{slug}")
async def get_content(
    slug: str,
    locale: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    supported, default_locale = await get_supported_locales(db)
    requested = normalise_locale(locale)

    # 回退链：请求语言（须为站点启用语言）→ 站点默认语言 → en
    candidates: list[str] = []
    if requested and requested in supported:
        candidates.append(requested)
    for code in (default_locale, "en"):
        if code in supported and code not in candidates:
            candidates.append(code)

    for code in candidates:
        content = await SQLAlchemyContentRepository.get_published_by_slug_locale(db, slug, code)
        if content is not None:
            return {"data": content.to_dict()}

    raise HTTPException(status_code=404, detail="内容不存在或未发布")
