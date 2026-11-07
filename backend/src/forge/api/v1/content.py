"""C-end CMS Content API.

按 slug 返回已发布（status=published）的 CMS 内容页，支持按语言（locale）独立获取：
- ``?locale=<code>`` 返回对应语言内容，语言清单取自站点配置 i18n.locales；
- 未指定、语言未在站点启用、或该语言无已发布内容时，按回退链降级：
  请求语言 → 站点默认语言（i18n.defaultLocale）→ ``en``；
- 未发布或不存在一律 404，由前端降级为 Coming soon 占位。

法务占位符注入：正文中的 ``{{COMPANY_LEGAL_NAME}}`` 等占位符在此处用站点配置
``legal`` 块（Admin → 站点设置 → 法务信息）渲染。渲染后仍残留占位符（即法务信息
尚未补齐）的内容页按“未就绪”处理，跳过该语言候选，避免半成品法务页对外展示。
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from forge.application.services.content_service import get_supported_locales, normalise_locale
from forge.application.services.legal_placeholder_service import (
    find_unresolved_placeholders,
    render_legal_placeholders,
)
from forge.infrastructure.persistence.repositories.content_repo import SQLAlchemyContentRepository
from forge.infrastructure.site_config_service import get_legal_info
from forge.main.dependencies import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["C-end Content"])

# 需要注入法务事实的文本字段
_RENDERED_FIELDS = ("title", "body", "seo_title", "seo_description")


def _render_payload(payload: dict[str, object], legal: dict[str, str], locale: str) -> dict[str, object]:
    """对返回给 C 端的文本字段统一渲染法务占位符（未配置的占位符保持原样）。"""
    result = dict(payload)
    for field in _RENDERED_FIELDS:
        value = result.get(field)
        if isinstance(value, str) and value:
            result[field] = render_legal_placeholders(value, legal, locale)
    return result


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

    legal = await get_legal_info(db)

    for code in candidates:
        content = await SQLAlchemyContentRepository.get_published_by_slug_locale(db, slug, code)
        if content is None:
            continue
        payload = _render_payload(content.to_dict(), legal, code)
        unresolved = find_unresolved_placeholders(str(payload.get("body") or ""))
        if unresolved:
            logger.warning(
                "CMS 内容含未配置的法务占位符，按未就绪跳过: slug=%s locale=%s placeholders=%s"
                "（请在 Admin → 站点设置 → 法务信息 补齐）",
                slug,
                code,
                ", ".join(unresolved),
            )
            continue
        return {"data": payload}

    raise HTTPException(status_code=404, detail="内容不存在或未发布")
