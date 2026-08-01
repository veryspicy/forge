"""DIY 页面装修 — 领域模型 v2.0（纯 Python dataclasses）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4


class PageStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"


class PageType(str, Enum):
    HOME = "home"
    CATEGORY = "category"
    PRODUCT_DETAIL = "product_detail"
    CUSTOM = "custom"


SYSTEM_PAGE_TYPES = {PageType.HOME.value, PageType.CATEGORY.value, PageType.PRODUCT_DETAIL.value}


class ComponentCategory(str, Enum):
    BASIC = "basic"
    GOODS = "goods"
    MARKETING = "marketing"
    LAYOUT = "layout"


@dataclass
class DiyComponent:
    """组件定义（系统内置 + 可扩展）"""

    id: UUID = field(default_factory=uuid4)
    code: str = ""
    name: str = ""
    category: ComponentCategory = ComponentCategory.BASIC
    icon: str = "mdi:widget"
    default_config: dict = field(default_factory=dict)
    config_schema: dict = field(default_factory=dict)
    is_system: bool = True
    sort_order: int = 0
    is_active: bool = True


@dataclass
class PageComponent:
    """页面中的组件实例"""

    id: UUID = field(default_factory=uuid4)
    page_id: UUID = field(default_factory=uuid4)
    component_id: UUID = field(default_factory=uuid4)
    sort_order: int = 0
    config: dict = field(default_factory=dict)
    is_visible: bool = True


@dataclass
class DiyPage:
    """DIY 页面 — 聚合根（v2.0）"""

    id: UUID = field(default_factory=uuid4)
    name: str = ""
    slug: str = ""
    title: str = ""
    description: str = ""
    page_type: str = PageType.CUSTOM.value
    status: PageStatus = PageStatus.DRAFT
    is_template: bool = False
    industry_tag: str | None = None
    template_thumbnail: str | None = None
    template_description: str | None = None
    snapshot_config: dict = field(default_factory=dict)
    published_at: datetime | None = None
    created_by: UUID | None = None
    components: list[PageComponent] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def create(cls, name: str, slug: str, page_type: str = PageType.CUSTOM.value) -> "DiyPage":
        return cls(name=name, slug=slug, page_type=page_type)

    def publish(self) -> None:
        self.status = PageStatus.PUBLISHED
        self.published_at = datetime.now()

    def add_component(self, pc: PageComponent) -> None:
        """向页面添加组件实例"""
        if not self.components:
            pc.sort_order = 0
        else:
            pc.sort_order = max(c.sort_order for c in self.components) + 1
        pc.page_id = self.id
        self.components.append(pc)

    def reorder(self, component_ids: list[UUID]) -> None:
        """按传入顺序重新排序组件"""
        id_map = {c.id: c for c in self.components}
        for i, cid in enumerate(component_ids):
            if cid in id_map:
                id_map[cid].sort_order = i
