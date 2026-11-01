"""C-end CMS Content API.

按 slug 返回已发布（status=published）的 CMS 内容页。
未发布或不存在一律 404，由前端降级为 Coming soon 占位。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from forge.infrastructure.persistence.repositories.content_repo import SQLAlchemyContentRepository
from forge.main.dependencies import get_db

router = APIRouter(tags=["C-end Content"])


@router.get("/content/{slug}")
async def get_content(slug: str, db: AsyncSession = Depends(get_db)) -> dict[str, object]:
    content = await SQLAlchemyContentRepository.get_published_by_slug(db, slug)
    if content is None:
        raise HTTPException(status_code=404, detail="内容不存在或未发布")
    return {"data": content.to_dict()}
