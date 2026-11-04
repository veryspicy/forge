"""Content — Application Service（轻量 CMS）。

承载内容页业务规则：slug 规范化与唯一校验、发布状态切换时维护 published_at。
API 层负责 HTTP 语义与错误映射，本层只抛领域异常。
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from forge.infrastructure.persistence.models import ORMContent
from forge.infrastructure.persistence.repositories.content_repo import SQLAlchemyContentRepository

VALID_STATUSES = {"draft", "published"}
SUPPORTED_LOCALES = {"en", "zh"}
_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _normalise_slug(value: str) -> str:
    """小写 + 连字符化：whitespace/underscore -> dash，移除非法字符。"""
    slug = value.strip().lower()
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug


class ContentValidationError(ValueError):
    """内容参数校验失败。"""

    def __init__(self, message: str, errors: dict[str, str] | None = None):
        super().__init__(message)
        self.errors = errors or {}


class ContentSlugConflictError(ValueError):
    pass


class ContentService:
    """CMS 内容业务规则层。"""

    @staticmethod
    async def create_content(db: AsyncSession, data: dict[str, Any]) -> ORMContent:
        errors = ContentService._validate_base(data)
        if errors:
            raise ContentValidationError("内容参数校验失败", errors)

        slug = _normalise_slug(str(data["slug"]))
        if not slug or not _SLUG_RE.match(slug):
            raise ContentValidationError(
                "slug 格式无效",
                {"slug": "slug 仅允许小写字母、数字与连字符（如 faqs / shipping）"},
            )

        locale = str(data.get("locale") or "en").lower()
        if locale not in SUPPORTED_LOCALES:
            raise ContentValidationError(
                "locale 无效",
                {"locale": f"locale 必须为 {sorted(SUPPORTED_LOCALES)} 之一"},
            )

        existing = await SQLAlchemyContentRepository.get_by_slug_locale(db, slug, locale)
        if existing:
            raise ContentSlugConflictError(f"slug 已存在: {slug}（locale={locale}）")

        payload = dict(data)
        payload["slug"] = slug
        payload["locale"] = locale
        payload.setdefault("status", "draft")
        payload.setdefault("body", "")
        if payload.get("status") == "published":
            payload.setdefault("published_at", datetime.now())
        return await SQLAlchemyContentRepository.create(db, payload)

    @staticmethod
    async def update_content(
        db: AsyncSession,
        content: ORMContent,
        data: dict[str, Any],
    ) -> ORMContent:
        errors = ContentService._validate_base(data, partial=True)
        if errors:
            raise ContentValidationError("内容参数校验失败", errors)

        # locale 变更时校验合法性
        if "locale" in data and data["locale"]:
            new_locale = str(data["locale"]).lower()
            if new_locale not in SUPPORTED_LOCALES:
                raise ContentValidationError(
                    "locale 无效",
                    {"locale": f"locale 必须为 {sorted(SUPPORTED_LOCALES)} 之一"},
                )
            data["locale"] = new_locale

        target_locale = str(data.get("locale") or content.locale or "en").lower()

        target_slug: str = str(content.slug)
        if "slug" in data and data["slug"]:
            target_slug = _normalise_slug(str(data["slug"]))
            if not target_slug or not _SLUG_RE.match(target_slug):
                raise ContentValidationError(
                    "slug 格式无效",
                    {"slug": "slug 仅允许小写字母、数字与连字符（如 faqs / shipping）"},
                )
            data["slug"] = target_slug

        # (slug, locale) 复合唯一：任一维度变更都必须查重，否则会撞 DB 唯一约束抛 500
        if target_slug != content.slug or target_locale != content.locale:
            existing = await SQLAlchemyContentRepository.get_by_slug_locale(db, target_slug, target_locale)
            if existing and str(existing.id) != str(content.id):
                raise ContentSlugConflictError(f"slug 已存在: {target_slug}（locale={target_locale}）")

        # 发布/下架切换时维护 published_at
        new_status = data.get("status")
        if new_status is not None and new_status != content.status:
            if new_status == "published" and content.published_at is None:
                data["published_at"] = datetime.now()
            elif new_status != "published":
                data["published_at"] = None

        return await SQLAlchemyContentRepository.update(db, content, data)

    @staticmethod
    async def set_status(db: AsyncSession, content: ORMContent, status: str) -> ORMContent:
        if status not in VALID_STATUSES:
            raise ContentValidationError("无效状态", {"status": f"status 必须为 {sorted(VALID_STATUSES)} 之一"})
        return await ContentService.update_content(db, content, {"status": status})

    @staticmethod
    def _validate_base(data: dict[str, Any], partial: bool = False) -> dict[str, str]:
        errors: dict[str, str] = {}

        if "slug" in data or not partial:
            slug = data.get("slug")
            if not slug or not str(slug).strip():
                errors["slug"] = "slug 不能为空"
            elif len(str(slug)) > 128:
                errors["slug"] = "slug 长度不能超过 128"

        if "title" in data or not partial:
            title = data.get("title")
            if not title or not str(title).strip():
                errors["title"] = "标题不能为空"
            elif len(str(title)) > 255:
                errors["title"] = "标题长度不能超过 255"

        if "status" in data and data["status"] not in VALID_STATUSES:
            errors["status"] = f"status 必须为 {sorted(VALID_STATUSES)} 之一"

        if "seo_title" in data and data["seo_title"] and len(str(data["seo_title"])) > 255:
            errors["seo_title"] = "SEO 标题长度不能超过 255"

        if "seo_description" in data and data["seo_description"] and len(str(data["seo_description"])) > 500:
            errors["seo_description"] = "SEO 描述长度不能超过 500"

        return errors
