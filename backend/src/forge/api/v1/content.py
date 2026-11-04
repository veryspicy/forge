"""C-end CMS Content API.

按 slug 返回已发布（status=published）的 CMS 内容页，支持按语言（locale）独立获取：
- ``?locale=en`` / ``?locale=zh`` 返回对应语言内容；
- 未指定或指定语言无内容时回退 ``en``（默认语言）；
- 未发布或不存在一律 404，由前端降级为 Coming soon 占位。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from forge.infrastructure.persistence.repositories.content_repo import SQLAlchemyContentRepository
from forge.main.dependencies import get_db

router = APIRouter(tags=["C-end Content"])


@router.get("/content/{slug}")
async def get_content(
    slug: str,
    locale: str = Query(default="en", pattern="^(en|zh)$"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    content = await SQLAlchemyContentRepository.get_published_by_slug_locale(db, slug, locale)
    if content is None and locale != "en":
        # fallback：指定语言无已发布内容时回退默认语言
        content = await SQLAlchemyContentRepository.get_published_by_slug_locale(db, slug, "en")
    if content is None:
        raise HTTPException(status_code=404, detail="内容不存在或未发布")
    return {"data": content.to_dict()}
