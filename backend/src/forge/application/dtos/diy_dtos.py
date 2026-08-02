"""DIY 页面装修 — Pydantic DTO v2.0。"""

from __future__ import annotations

import re
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

PageTypeEnum = Literal["home", "category", "product_detail"]

RESERVED_SLUGS = {
    "admin", "api", "login", "register", "cart", "checkout", "account",
    "orders", "search", "category", "product", "products", "home", "index",
}

_SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


class ComponentConfigDTO(BaseModel):
    """整页保存 — 单个组件实例"""

    component_id: UUID
    sort_order: int = 0
    config: dict = Field(default_factory=dict)
    is_visible: bool = True


class SaveComponentsDTO(BaseModel):
    """整页保存组件列表"""

    components: list[ComponentConfigDTO] = Field(default_factory=list)


class PageBasicDTO(BaseModel):
    """页面基础信息更新"""

    name: Optional[str] = Field(None, min_length=1, max_length=128)
    title: Optional[str] = None
    description: Optional[str] = None


class CreateCustomPageDTO(BaseModel):
    """创建自定义页面"""

    name: str = Field(..., min_length=1, max_length=128)
    slug: str = Field(..., min_length=1, max_length=128)
    title: str = ""
    description: str = ""

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        if not _SLUG_RE.match(v):
            raise ValueError("slug 只能包含小写字母、数字和中划线，且不能以中划线开头/结尾")
        if v.isdigit():
            raise ValueError("slug 不能是纯数字")
        if v in RESERVED_SLUGS:
            raise ValueError(f"slug '{v}' 是保留词，不可使用")
        return v


class SaveAsTemplateDTO(BaseModel):
    """当前站点保存为模板"""

    name: str = Field(..., min_length=1, max_length=128)
    industry_tag: Optional[str] = Field(None, max_length=64)
    template_description: Optional[str] = None
    template_thumbnail: Optional[str] = None


class ApplyTemplateDTO(BaseModel):
    """应用模板（二次确认）"""

    confirm: bool = True


# ---------------------------------------------------------------------------
# v1.x 兼容别名（旧 Admin API 仍引用）
# ---------------------------------------------------------------------------

DiyPageCreateDTO = CreateCustomPageDTO
DiyPageUpdateDTO = PageBasicDTO
PageComponentDTO = ComponentConfigDTO
