"""法务占位符渲染（CMS 内容 ← 站点配置 legal 块注入）。

法务事实（公司法定主体名 / 注册地址 / 隐私邮箱 / 管辖法律 / 生效日期 /
VAT ID / RCS 号）不在 CMS 正文里写死，正文只写占位符，渲染时统一从站点配置
``site_profiles.config.legal`` 注入。原因：

* 三语（en/zh/ar/de/fr）法务页共用同一组法务事实，写死会导致各语言版本不一致；
* 主体信息 / 地址 / 管辖法律变更时，只需在 Admin → 站点设置 → 法务信息改一次，
  无需重新导入多语言内容；
* 未配置的字段渲染后仍会留下占位符，调用方据此判定内容“未就绪”，避免半成品
  法务页对外展示。

占位符 → 站点配置字段（camelCase）：

    {{COMPANY_LEGAL_NAME}} -> legal.companyLegalName
    {{COMPANY_ADDRESS}}    -> legal.registeredAddress
    {{PRIVACY_EMAIL}}      -> legal.privacyEmail
    {{JURISDICTION}}       -> legal.jurisdiction
    {{LAST_UPDATED}}       -> legal.lastUpdated（按内容语言本地化格式）
    {{VAT_ID}}             -> legal.vatId
    {{RCS_NUMBER}}         -> legal.rcsNumber

按语言覆盖：``legal.byLocale[locale][字段]`` 若为非空值，优先于上面的全局值。
用于占位符处于语法内嵌位置、直填全局值会语病的字段（如德语
``Es gilt das Recht von {{JURISDICTION}}`` 需 ``der Volksrepublik China``）。
"""

from __future__ import annotations

import logging
import re
from datetime import date
from typing import Any

logger = logging.getLogger(__name__)

# 占位符 -> legal 块字段
PLACEHOLDER_FIELD_MAP: dict[str, str] = {
    "{{COMPANY_LEGAL_NAME}}": "companyLegalName",
    "{{COMPANY_ADDRESS}}": "registeredAddress",
    "{{PRIVACY_EMAIL}}": "privacyEmail",
    "{{JURISDICTION}}": "jurisdiction",
    "{{LAST_UPDATED}}": "lastUpdated",
    "{{VAT_ID}}": "vatId",
    "{{RCS_NUMBER}}": "rcsNumber",
}

# 需要按语言本地化格式化的占位符（日期）
_LOCALISED_DATE_PLACEHOLDERS = {"{{LAST_UPDATED}}"}

PLACEHOLDER_RE = re.compile(r"\{\{[A-Z0-9_]+\}\}")

_MONTHS: dict[str, tuple[str, ...]] = {
    "en": (
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ),
    "zh": tuple(f"{i}月" for i in range(1, 13)),
    "de": (
        "Januar",
        "Februar",
        "März",
        "April",
        "Mai",
        "Juni",
        "Juli",
        "August",
        "September",
        "Oktober",
        "November",
        "Dezember",
    ),
    "fr": (
        "janvier",
        "février",
        "mars",
        "avril",
        "mai",
        "juin",
        "juillet",
        "août",
        "septembre",
        "octobre",
        "novembre",
        "décembre",
    ),
    "ar": (
        "يناير",
        "فبراير",
        "مارس",
        "أبريل",
        "مايو",
        "يونيو",
        "يوليو",
        "أغسطس",
        "سبتمبر",
        "أكتوبر",
        "نوفمبر",
        "ديسمبر",
    ),
}

_ISO_DATE_RE = re.compile(r"^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})$")


def _parse_date(value: str) -> date | None:
    """解析 ``YYYY-MM-DD`` / ``YYYY/MM/DD`` / ``YYYY.MM.DD``；其它格式返回 None。"""
    match = _ISO_DATE_RE.match(value.strip())
    if not match:
        return None
    year, month, day = (int(g) for g in match.groups())
    try:
        return date(year, month, day)
    except ValueError:
        return None


def format_legal_date(value: str, locale: str) -> str:
    """法务日期按内容语言本地化（en: November 6, 2026 / de: 6. November 2026 / zh: 2026年11月6日）。

    非可解析格式（如用户手填的 ``6 November 2026`` 自由文本）原样返回，
    由填写方自行保证格式，不做二次解释。
    """
    parsed = _parse_date(value)
    if parsed is None:
        return value

    lang = (locale or "en").strip().lower().split("-")[0]
    months = _MONTHS.get(lang, _MONTHS["en"])
    month_name = months[parsed.month - 1]

    if lang == "zh":
        return f"{parsed.year}年{parsed.month}月{parsed.day}日"
    if lang == "de":
        return f"{parsed.day}. {month_name} {parsed.year}"
    if lang in {"fr", "ar"}:
        return f"{parsed.day} {month_name} {parsed.year}"
    return f"{month_name} {parsed.day}, {parsed.year}"


def _normalise_locale(locale: str | None) -> str:
    """``de-DE`` / ``DE`` / ``de_DE`` → ``de``。"""
    return (locale or "en").strip().lower().replace("_", "-").split("-")[0] or "en"


def resolve_legal_block(legal: dict[str, Any] | None, locale: str | None) -> dict[str, Any]:
    """合并全局 legal 与 ``byLocale[locale]`` 覆盖层，返回当前语言的生效值。

    覆盖层只对非空值生效：某语言未覆盖的字段回退全局值。
    """
    block = dict(legal or {})
    overrides = block.pop("byLocale", None)
    if isinstance(overrides, dict):
        per_locale = overrides.get(_normalise_locale(locale))
        if isinstance(per_locale, dict):
            for field, raw in per_locale.items():
                value = "" if raw is None else str(raw).strip()
                if value:
                    block[field] = value
    return block


def build_legal_replacements(legal: dict[str, Any] | None, locale: str = "en") -> dict[str, str]:
    """构建 ``占位符 -> 替换值`` 映射；未配置（空值）的字段不进入映射。"""
    block = resolve_legal_block(legal, locale)
    replacements: dict[str, str] = {}
    for placeholder, field in PLACEHOLDER_FIELD_MAP.items():
        raw = block.get(field)
        value = "" if raw is None else str(raw).strip()
        if not value:
            continue
        if placeholder in _LOCALISED_DATE_PLACEHOLDERS:
            value = format_legal_date(value, locale)
        replacements[placeholder] = value
    return replacements


def find_unresolved_placeholders(text: str | None) -> list[str]:
    """返回文本中仍存在（未配置）的占位符列表（去重排序）。"""
    if not text:
        return []
    return sorted(set(PLACEHOLDER_RE.findall(text)))


def render_legal_placeholders(text: str | None, legal: dict[str, Any] | None, locale: str = "en") -> str:
    """把正文中的法务占位符替换为站点配置值；未配置的占位符保持原样。"""
    if not text:
        return text or ""
    rendered = text
    for placeholder, value in build_legal_replacements(legal, locale).items():
        rendered = rendered.replace(placeholder, value)
    return rendered


def missing_legal_fields(text: str | None, legal: dict[str, Any] | None, locale: str = "en") -> list[str]:
    """返回正文用到、但站点配置尚未填写的 legal 字段名（用于 Admin/导入器给出补齐清单）。"""
    if not text:
        return []
    placeholders = set(PLACEHOLDER_RE.findall(text))
    block = resolve_legal_block(legal, locale)
    missing: list[str] = []
    for placeholder in sorted(placeholders):
        field = PLACEHOLDER_FIELD_MAP.get(placeholder)
        if field is None:
            # 未知占位符：调用方应按未解析处理，此处不臆测字段名
            continue
        raw = block.get(field)
        if raw is None or not str(raw).strip():
            missing.append(field)
    return missing


def is_legal_ready(text: str | None, legal: dict[str, Any] | None, locale: str = "en") -> bool:
    """正文是否可对外展示：替换后不存在任何未解析占位符。"""
    return not find_unresolved_placeholders(render_legal_placeholders(text, legal, locale))
