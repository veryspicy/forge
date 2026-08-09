---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 14f48488fead00d28e11c31f9845685c_29ab48288b4811f1a642525400287e28
    ReservedCode1: ERvN4i1xtfyd1KEKZXBrYY7ITxB52HdHvYEemUqWl5q7so7/xijEEP6ATqQeuFclxf+Hx/rMdgg5z+0cySAiL9BQepMw1CMrrnazPkpabhUw7NyBVWQDjbCTMJvlbMOSHaWLZ2eimtUugTbvBuBxpRjqXIsAkTKCi2m/eaXq9LqXDXUuSLszo2+uWFw=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 14f48488fead00d28e11c31f9845685c_29ab48288b4811f1a642525400287e28
    ReservedCode2: ERvN4i1xtfyd1KEKZXBrYY7ITxB52HdHvYEemUqWl5q7so7/xijEEP6ATqQeuFclxf+Hx/rMdgg5z+0cySAiL9BQepMw1CMrrnazPkpabhUw7NyBVWQDjbCTMJvlbMOSHaWLZ2eimtUugTbvBuBxpRjqXIsAkTKCi2m/eaXq9LqXDXUuSLszo2+uWFw=
---




# Forge 可视化 DIY 页面装修技术方案

> 基于项目现有架构（FastAPI + SQLAlchemy + Vue 3 + NaiveUI + Nuxt 3）设计，完全对齐现有技术栈、代码风格、DDD 分层公约。

> v2.0 — 已对齐实际代码实现（2026-08-10 更新）

---

## 零、项目分析摘要

### 技术栈矩阵

| 维度 | 技术选型 |
|------|----------|
| **后端框架** | FastAPI (Python 3.12)，异步 |
| **ORM** | SQLAlchemy 2.0 (async)，Alembic 迁移 |
| **数据库** | PostgreSQL (asyncpg)，Redis 5.x |
| **对象存储** | MinIO (S3-compatible) |
| **权限模型** | Casbin RBAC + 自定义 admin_users/roles/permissions 表 |
| **Admin 前端** | Vue 3 + Vite + TypeScript + NaiveUI + UnoCSS + Pinia |
| **拖拽库（已有）** | vue-draggable-plus 0.6.1 |
| **前端（C端）** | Nuxt 3 + Vue 3 + Tailwind CSS 4 + @nuxt/ui + @nuxt/image |
| **包管理** | pnpm (monorepo) → admin / frontend 独立 package.json |

### 后端分层架构（DDD）

```
forge/
├── domain/                 # 领域模型（纯 Python dataclasses）
│   └── product/models.py   # Product 聚合根，含工厂方法、业务规则
├── application/            # 应用服务层
│   ├── services/           # ProductService、OrderService 等
│   └── dtos/               # Pydantic Request/Response DTO
├── infrastructure/         # 基础设施层
│   └── persistence/
│       ├── database.py     # Base、async engine、get_db 依赖
│       ├── models.py       # ORM 映射类（ORMProduct 等）
│       └── repositories/   # SQLAlchemy 实现 + 接口协议
├── api/                    # FastAPI 路由
│   ├── admin/v1/           # 管理端 /api/admin/v1
│   └── v1/                 # C端 /api/v1
└── clients/                # MinIO 等外部客户端
```

### 关键编码公约

| 约定 | 示例 |
|------|------|
| **表名** | 小写蛇形，`products` / `site_profiles` / `admin_users` |
| **主键** | UUID，`gen_random_uuid()` 默认值 |
| **JSONB** | 灵活配置字段，如 `site_profiles.config` |
| **时间戳** | `created_at` + `updated_at`，`server_default=now()` |
| **ORM 模型** | 继承 `Base`，定义 `to_dict()` 方法 |
| **Repository** | 先在 `base.py` 定义接口协议，再在 `repositories/` 实现 |
| **Service** | 构造函数注入 Repository 接口 |
| **API DTO** | Pydantic `BaseModel`，含 Field 校验 |
| **Admin API** | 直接使用 `AsyncSession` + ORM 查询（如 site_profile.py），无需每次都走 Repository |
| **权限** | `Depends(require_permission("模块", "操作"))` |
| **Admin 前端 API** | `get/post/put/del` helper 函数，返回 Axios response |
| **Admin 前端组件** | NaiveUI 全套，UnoCSS 原子化 CSS |

### 现有配置管理机制

- **`site_profiles` 表**：JSONB `config` 字段存储品牌、主题、导航、首页 Section、SEO 等全部站点配置
- **`settings` 端点**：目前使用内存缓存（`_settings_cache`），存储店名、货币、通知等 KV 配置
- **Nuxt 前端**：通过 `/api/v1/site-profile/` 拉取激活 Profile 的 config，渲染首页

---

## 一、数据库设计

> 新增 3 张表：`diy_pages`（页面定义）、`diy_components`（组件库）、`diy_page_components`（页面组件实例）。遵循现有命名规范。

### 1.1 DIY 页面表 (`diy_pages`)

```sql
CREATE TABLE diy_pages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(128)  NOT NULL,               -- 页面名称（管理端标识）
    slug            VARCHAR(128)  NOT NULL UNIQUE,        -- URL 标识，如 "home_v2"、"promotion_2024"
    title           VARCHAR(256)  NOT NULL DEFAULT '',    -- 页面标题（SEO/browser title）
    description     TEXT          NOT NULL DEFAULT '',    -- 页面描述（SEO meta）
    page_type       VARCHAR(32)   NOT NULL DEFAULT 'custom',  -- home / category / product_detail / custom
    status          VARCHAR(16)   NOT NULL DEFAULT 'draft',   -- draft / published
    is_default      BOOLEAN       NOT NULL DEFAULT FALSE,     -- 是否设为首页（全局唯一）
    is_template      BOOLEAN       NOT NULL DEFAULT FALSE,    -- 是否为模板
    industry_tag     VARCHAR(64),                              -- 模板行业标签
    template_thumbnail VARCHAR(512),                           -- 模板缩略图
    template_description TEXT,                                 -- 模板描述
    snapshot_config  JSONB        NOT NULL DEFAULT '{}',       -- 模板快照配置
    published_at    TIMESTAMPTZ,                           -- 发布时间
    created_by      UUID          REFERENCES admin_users(id),-- 创建人
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ   NOT NULL DEFAULT now()
);

CREATE INDEX idx_diy_pages_slug ON diy_pages(slug);
CREATE INDEX idx_diy_pages_status ON diy_pages(status);
CREATE INDEX idx_diy_pages_type ON diy_pages(page_type);
```

### 1.2 DIY 组件定义表 (`diy_components`)

> 系统内置组件库，也支持后续扩展自定义组件。

```sql
CREATE TABLE diy_components (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code            VARCHAR(64)  NOT NULL UNIQUE,        -- 组件编码，如 "banner"、"goods_list"
    name            VARCHAR(128) NOT NULL,               -- 显示名称，如 "轮播横幅"
    category        VARCHAR(32)  NOT NULL DEFAULT 'basic', -- basic / goods / marketing / layout
    icon            VARCHAR(64)  NOT NULL DEFAULT 'mdi:widget', -- iconify 图标名
    default_config  JSONB        NOT NULL DEFAULT '{}',   -- 默认配置 JSON Schema
    config_schema   JSONB        NOT NULL DEFAULT '{}',   -- 属性编辑表单 Schema（字段定义）
    is_system       BOOLEAN      NOT NULL DEFAULT TRUE,   -- 是否系统内置
    sort_order      INTEGER      NOT NULL DEFAULT 0,      -- 组件库展示排序
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX idx_diy_components_category ON diy_components(category);
```

### 1.3 页面-组件关联表 (`diy_page_components`)

> 一个页面由多个组件实例组成，按 `sort_order` 纵向排列。

```sql
CREATE TABLE diy_page_components (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    page_id         UUID NOT NULL REFERENCES diy_pages(id) ON DELETE CASCADE,
    component_id    UUID NOT NULL REFERENCES diy_components(id),
    sort_order      INTEGER NOT NULL DEFAULT 0,       -- 排序（拖拽顺序）
    config          JSONB NOT NULL DEFAULT '{}',       -- 组件实例的具体配置（覆盖 default_config）
    is_visible      BOOLEAN NOT NULL DEFAULT TRUE,     -- 可见性
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_dpc_page_id ON diy_page_components(page_id);
CREATE INDEX idx_dpc_page_sort ON diy_page_components(page_id, sort_order);
```

### 1.4 关联现有表

- `diy_pages.created_by → admin_users.id`（记录创建人）
- 无需修改现有 `site_profiles` 表，DIY 页面作为独立功能存在；激活首页通过 `diy_pages` 表中 `page_type='home'` 的系统页面控制
- 3 个系统页面（home/category/product_detail）由迁移脚本 `0009_seed_system_diy_pages.py` 自动创建
- 现有的 `site_profiles.config` 可新增一个 `diy_page_slug` 字段指向 DIY 首页（渐进迁移）

### 1.5 系统内置组件初始化数据

```sql
INSERT INTO diy_components (code, name, category, icon, default_config, config_schema, sort_order) VALUES
-- 基础组件
('banner',        '轮播横幅',       'basic',    'mdi:view-carousel',   '{"slides":[],"autoplay":true,"interval":3000,"height":375}', '{"type":"object","properties":{"slides":{"type":"array","items":{"type":"object","properties":{"image":{"type":"string","title":"图片"},"link":{"type":"string","title":"链接"}}}},"autoplay":{"type":"boolean","title":"自动播放"},"interval":{"type":"integer","title":"间隔(ms)","default":3000},"height":{"type":"integer","title":"高度(px)","default":375}}}', 1),
('search_box',    '搜索框',         'basic',    'mdi:magnify',         '{"placeholder":"Search products...","style":"simple","backgroundColor":"#ffffff"}', '{"type":"object","properties":{"placeholder":{"type":"string","title":"占位文字"},"style":{"type":"string","enum":["simple","rounded","with-categories"],"title":"样式"},"backgroundColor":{"type":"string","title":"背景色"}}}', 2),
('image_ad',      '图片广告',       'basic',    'mdi:image',           '{"image":"","link":"","mode":"full_width","height":200}', '{"type":"object","properties":{"image":{"type":"string","title":"图片"},"link":{"type":"string","title":"链接"},"mode":{"type":"string","enum":["full_width","card"],"title":"展示模式"},"height":{"type":"integer","title":"高度(px)"}}}', 3),
('text_block',    '文本模块',       'basic',    'mdi:text',            '{"content":"","textAlign":"left","fontSize":14,"color":"#333333","backgroundColor":"transparent","padding":16}', '{"type":"object","properties":{"content":{"type":"string","title":"内容","ui:widget":"textarea"},"textAlign":{"type":"string","enum":["left","center","right"],"title":"对齐"},"fontSize":{"type":"integer","title":"字号"},"color":{"type":"string","title":"文字颜色"}}}', 4),
('rich_text',     '富文本',         'basic',    'mdi:format-text',     '{"content":"","padding":16}', '{"type":"object","properties":{"content":{"type":"string","title":"内容","ui:widget":"rich-editor"},"padding":{"type":"integer","title":"内边距"}}}', 5),
('video',         '视频模块',       'basic',    'mdi:video',           '{"url":"","poster":"","autoplay":false,"loop":false}', '{"type":"object","properties":{"url":{"type":"string","title":"视频地址"},"poster":{"type":"string","title":"封面图"},"autoplay":{"type":"boolean","title":"自动播放"}}}', 6),
('divider',       '分割线',         'basic',    'mdi:minus',           '{"style":"solid","color":"#e5e5e5","height":1,"margin":0}', '{"type":"object","properties":{"style":{"type":"string","enum":["solid","dashed","dotted"],"title":"线型"},"color":{"type":"string","title":"颜色"}}}', 7),

-- 商品组件
('goods_list',    '商品列表',       'goods',    'mdi:package-variant', '{"title":"Hot Products","source":"manual","category":"","productIds":[],"displayCount":6,"layout":"grid","columns":2,"showPrice":true,"showCartButton":true}', '{"type":"object","properties":{"title":{"type":"string","title":"标题"},"source":{"type":"string","enum":["manual","category","ai_recommend"],"title":"数据源"},"category":{"type":"string","title":"分类"},"productIds":{"type":"array","items":{"type":"string"},"title":"手动选品"},"displayCount":{"type":"integer","title":"展示数量"},"layout":{"type":"string","enum":["grid","list","scroll"],"title":"布局"},"columns":{"type":"integer","title":"列数"}}}', 10),
('goods_single',  '单商品卡片',     'goods',    'mdi:card',            '{"productId":"","layout":"vertical"}', '{"type":"object","properties":{"productId":{"type":"string","title":"商品ID","ui:widget":"product-picker"},"layout":{"type":"string","enum":["vertical","horizontal"],"title":"布局"}}}', 11),
('goods_group',   '商品分组',       'goods',    'mdi:view-grid',      '{"tabs":[{"name":"Tab 1","category":""}],"displayCount":4,"columns":2}', '{"type":"object","properties":{"tabs":{"type":"array","items":{"type":"object","properties":{"name":{"type":"string","title":"Tab名"},"category":{"type":"string","title":"分类"}}},"title":"Tab配置"}}}', 12),

-- 营销组件
('coupon',        '优惠券',         'marketing','mdi:ticket-percent', '{"couponId":"","style":"card"}', '{"type":"object","properties":{"couponId":{"type":"string","title":"优惠券ID","ui:widget":"coupon-picker"},"style":{"type":"string","enum":["card","banner"],"title":"样式"}}}', 20),
('countdown',     '倒计时',         'marketing','mdi:timer',          '{"endTime":"","title":"Limited Time Offer","backgroundColor":"#ff4757","textColor":"#ffffff"}', '{"type":"object","properties":{"endTime":{"type":"string","title":"结束时间","ui:widget":"datetime"},"title":{"type":"string","title":"标题"}}}', 21),
('notice_bar',    '公告栏',         'marketing','mdi:bullhorn',       '{"text":"","speed":50,"backgroundColor":"#fff7e6","textColor":"#fa8c16","closable":true}', '{"type":"object","properties":{"text":{"type":"string","title":"公告文字"},"speed":{"type":"integer","title":"滚动速度"}}}', 22),

-- 布局组件
('blank',         '空白占位',       'layout',   'mdi:dock-window',    '{"height":20,"backgroundColor":"transparent"}', '{"type":"object","properties":{"height":{"type":"integer","title":"高度(px)"},"backgroundColor":{"type":"string","title":"背景色"}}}', 30),
('nav_group',     '导航组',         'layout',   'mdi:apps',           '{"title":"","items":[],"columns":4}', '{"type":"object","properties":{"title":{"type":"string","title":"标题"},"items":{"type":"array","items":{"type":"object","properties":{"icon":{"type":"string","title":"图标"},"text":{"type":"string","title":"文字"},"link":{"type":"string","title":"链接"}}},"title":"导航项"},"columns":{"type":"integer","title":"列数"}}}', 31);
```

---

## 二、后端设计

### 2.1 新增文件清单

```
backend/src/forge/
├── domain/
│   └── diy/
│       ├── __init__.py
│       └── models.py              # DiyPage, DiyComponent, PageComponent 领域模型 + 枚举
├── application/
│   ├── dtos/
│   │   └── diy_dtos.py            # Pydantic Request/Response DTO
│   └── services/
│       └── diy_service.py         # DiyService（页面 CRUD + 发布 + 渲染数据组装）
├── infrastructure/
│   └── persistence/
│       ├── models.py              # 新增 ORMDiyPage, ORMDiyComponent, ORMDiyPageComponent
│       └── repositories/
│           └── diy_repo.py        # SQLAlchemyDiyRepository
├── api/
│   ├── admin/v1/
│   │   └── diy.py                 # Admin DIY API（挂载前缀 /api/admin/v1/site）
│   └── v1/
│       └── diy.py                 # 公开 DIY API (/api/v1/diy) — 给 Nuxt 调用
└── migrations/
    └── versions/
        ├── 0008_add_diy_tables.py            # Alembic 迁移脚本（建表 + 内置组件种子）
        └── 0009_seed_system_diy_pages.py     # 系统页面种子（home/category/product_detail）
```

> 说明：实际领域模型路径为 `domain/diy/models.py`；Admin API 文件位于 `api/admin/v1/diy.py`，但通过 router 挂载前缀 `/api/admin/v1/site`，因此对外暴露的端点路径形如 `/api/admin/v1/site/pages`。

### 2.2 领域模型

```python
# domain/diy/models.py

from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from uuid import UUID, uuid4


class PageStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"


class PageType(str, Enum):
    HOME = "home"
    CATEGORY = "category"
    PRODUCT_DETAIL = "product_detail"
    CUSTOM = "custom"


class ComponentCategory(str, Enum):
    BASIC = "basic"
    GOODS = "goods"
    MARKETING = "marketing"
    LAYOUT = "layout"


# 系统页面类型集合 — 这些类型的页面由迁移脚本预置，不可删除
SYSTEM_PAGE_TYPES = {PageType.HOME.value, PageType.CATEGORY.value, PageType.PRODUCT_DETAIL.value}


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
    """DIY 页面 — 聚合根"""
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    slug: str = ""
    title: str = ""
    description: str = ""
    page_type: str = PageType.CUSTOM.value
    status: PageStatus = PageStatus.DRAFT
    is_default: bool = False
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
```

### 2.3 ORM 模型（追加到 `infrastructure/persistence/models.py`）

```python
class ORMDiyPage(Base):
    __tablename__ = "diy_pages"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(128), nullable=False)
    slug = Column(String(128), unique=True, nullable=False, index=True)
    title = Column(String(256), nullable=False, default="")
    description = Column(Text, nullable=False, default="")
    page_type = Column(String(32), nullable=False, default="custom")
    status = Column(String(16), nullable=False, default="draft")
    is_default = Column(Boolean, nullable=False, default=False)
    is_template = Column(Boolean, nullable=False, default=False)
    industry_tag = Column(String(64), nullable=True)
    template_thumbnail = Column(String(512), nullable=True)
    template_description = Column(Text, nullable=True)
    snapshot_config = Column(JSONB, nullable=False, default=dict)
    published_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(PG_UUID(as_uuid=True), ForeignKey("admin_users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    components = relationship("ORMDiyPageComponent", back_populates="page", cascade="all, delete-orphan", order_by="ORMDiyPageComponent.sort_order")

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.name,
            "slug": self.slug,
            "title": self.title,
            "description": self.description,
            "page_type": self.page_type,
            "status": self.status,
            "is_default": self.is_default,
            "is_template": self.is_template,
            "industry_tag": self.industry_tag,
            "template_thumbnail": self.template_thumbnail,
            "template_description": self.template_description,
            "snapshot_config": self.snapshot_config or {},
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "created_by": str(self.created_by) if self.created_by else None,
            "components": [c.to_dict() for c in (self.components or [])],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ORMDiyComponent(Base):
    __tablename__ = "diy_components"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    code = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(128), nullable=False)
    category = Column(String(32), nullable=False, default="basic")
    icon = Column(String(64), nullable=False, default="mdi:widget")
    default_config = Column(JSONB, nullable=False, default=dict)
    config_schema = Column(JSONB, nullable=False, default=dict)
    is_system = Column(Boolean, nullable=False, default=True)
    sort_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "code": self.code,
            "name": self.name,
            "category": self.category,
            "icon": self.icon,
            "default_config": self.default_config or {},
            "config_schema": self.config_schema or {},
            "is_system": self.is_system,
            "sort_order": self.sort_order,
            "is_active": self.is_active,
        }


class ORMDiyPageComponent(Base):
    __tablename__ = "diy_page_components"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    page_id = Column(PG_UUID(as_uuid=True), ForeignKey("diy_pages.id", ondelete="CASCADE"), nullable=False)
    component_id = Column(PG_UUID(as_uuid=True), ForeignKey("diy_components.id"), nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)
    config = Column(JSONB, nullable=False, default=dict)
    is_visible = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    page = relationship("ORMDiyPage", back_populates="components")
    component = relationship("ORMDiyComponent", lazy="joined")

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "page_id": str(self.page_id),
            "component_id": str(self.component_id),
            "component_code": self.component.code if self.component else None,
            "component_name": self.component.name if self.component else None,
            "sort_order": self.sort_order,
            "config": self.config or {},
            "is_visible": self.is_visible,
        }
```

### 2.4 API 接口清单

#### Admin 端 (`/api/admin/v1/site`)

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| `GET` | `/pages` | 页面概览（返回 {system[], custom[]} 结构） | settings:manage |
| `POST` | `/custom-pages` | 创建自定义页面 | settings:manage |
| `GET` | `/pages/{key}` | 页面详情（key=UUID或page_type） | settings:manage |
| `PUT` | `/pages/{key}` | 更新页面信息（系统页不可改page_type/slug） | settings:manage |
| `DELETE` | `/custom-pages/{page_id}` | 删除自定义页面（系统页不可删） | settings:manage |
| `POST` | `/pages/{key}/publish` | 发布页面 | settings:manage |
| `POST` | `/pages/{key}/unpublish` | 撤销发布 | settings:manage |
| `POST` | `/custom-pages/{page_id}/duplicate` | 复制页面 | settings:manage |
| `PUT` | `/pages/{key}/components` | 保存组件列表（先删后插） | settings:manage |
| `GET` | `/components` | 组件库列表 | settings:manage |
| `POST` | `/upload-image` | 上传装修图片（存入 uploads/diy/ 目录） | settings:manage |
| `GET` | `/templates` | 模板列表（支持industry_tag过滤+分页） | settings:manage |
| `POST` | `/templates` | 保存当前站点为模板 | settings:manage |
| `POST` | `/templates/{template_id}/apply` | 应用模板到当前站点 | settings:manage |

#### 公开端 (`/api/v1/diy`)

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| `GET` | `/pages/{page_type}` | 获取系统页面渲染数据（home/category/product_detail） | 无 |
| `GET` | `/by-slug/{slug}` | 按 slug 获取已发布的自定义页面 | 无 |

> 说明：`preview=true` 参数绕过 Redis 直查 DB（允许 draft）；`preview=false` 仅返回已发布页面。

### 2.5 核心 API 代码骨架

```python
# api/admin/v1/diy.py
# 挂载前缀：/api/admin/v1/site
router = APIRouter()


@router.get("/pages", dependencies=[Depends(require_permission("settings", "manage"))])
async def list_pages(db: AsyncSession = Depends(get_db)):
    """DIY 页面概览 — 返回 {system[], custom[]} 结构，前端客户端过滤分页"""
    result = await db.execute(
        select(ORMDiyPage).order_by(ORMDiyPage.updated_at.desc())
    )
    all_pages = result.scalars().all()

    system_pages = [p.to_dict() for p in all_pages if p.page_type in SYSTEM_PAGE_TYPES]
    custom_pages = [p.to_dict() for p in all_pages if p.page_type not in SYSTEM_PAGE_TYPES]

    return {
        "system": system_pages,
        "custom": custom_pages,
    }


@router.get("/pages/{key}", dependencies=[Depends(require_permission("settings", "manage"))])
async def get_page(key: str, db: AsyncSession = Depends(get_db)):
    """页面详情（Eager-load 组件） — key 可以是 UUID 或 page_type"""
    stmt = select(ORMDiyPage).options(
        selectinload(ORMDiyPage.components).joinedload(ORMDiyPageComponent.component)
    )

    # 优先按 UUID 解析，失败则按 page_type 查找
    try:
        page_uuid = UUID(key)
        stmt = stmt.where(ORMDiyPage.id == page_uuid)
    except (ValueError, AttributeError):
        stmt = stmt.where(ORMDiyPage.page_type == key)

    result = await db.execute(stmt)
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(404, "Page not found")
    return page.to_dict()


@router.put("/pages/{key}/components", dependencies=[Depends(require_permission("settings", "manage"))])
async def save_components(
    key: str,
    data: list[PageComponentDTO],  # [{component_id, sort_order, config, is_visible}, ...]
    db: AsyncSession = Depends(get_db),
):
    """整页保存组件列表 — 先删后插（key 可以是 UUID 或 page_type）"""
    page = await _resolve_page(key, db)
    if not page:
        raise HTTPException(404, "Page not found")
    page_id = page.id

    # 删除现有组件
    await db.execute(delete(ORMDiyPageComponent).where(ORMDiyPageComponent.page_id == page_id))

    # 批量插入新组件
    for item in data:
        pc = ORMDiyPageComponent(
            page_id=page_id,
            component_id=item.component_id,
            sort_order=item.sort_order,
            config=item.config,
            is_visible=item.is_visible,
        )
        db.add(pc)

    await db.flush()
    return {"status": "ok", "count": len(data)}


@router.post("/pages/{key}/publish", dependencies=[Depends(require_permission("settings", "manage"))])
async def publish_page(key: str, db: AsyncSession = Depends(get_db)):
    """发布页面 + 刷新 Redis 缓存"""
    page = await _resolve_page(key, db)
    if not page:
        raise HTTPException(404, "Page not found")

    page.status = "published"
    page.published_at = datetime.now(timezone.utc)
    await db.flush()

    # 调用 enrich_page_data 后写入 Redis
    enriched = await enrich_page_data(page.to_dict())
    try:
        await redis_client.set(f"diy:page:{page.slug}", json.dumps(enriched))
        if page.page_type in SYSTEM_PAGE_TYPES:
            await redis_client.set(f"diy:page:{page.page_type}", json.dumps(enriched))
    except Exception:
        # Redis 不可用 — 通过 _redis_unavailable 熔断标志降级直查 DB
        global _redis_unavailable
        _redis_unavailable = True

    return {"status": "published", "published_at": page.published_at.isoformat()}


@router.post("/upload-image", dependencies=[Depends(require_permission("settings", "manage"))])
async def upload_diy_image(file: UploadFile = File(...)):
    """上传装修用图片到本地 uploads/diy/ 目录"""
    # 初期简化部署使用本地目录，后续可迁移到 MinIO
    ...
```

### 2.6 发布/预览机制

```
┌──────────────┐     保存组件      ┌──────────────┐
│   Admin SPA  │ ────────────────→ │   PostgreSQL  │
│   编辑器      │                   │  (diy_pages,  │
│              │                    │  diy_page_    │
│  [预览]按钮  │                    │  components)  │
└──────┬───────┘                   └──────┬───────┘
       │                                  │
       │ GET /api/v1/diy/by-slug/{slug}   │
       │ ?preview=true                    │
       ▼                                  ▼
┌──────────────┐                   ┌──────────────┐
│   后端 API   │ ←── 查询 DB ───→ │   PostgreSQL  │
│              │                   │              │
│  预览模式：  │                   └──────────────┘
│  直接读 DB   │
│  不读 Redis  │        ┌──────────────┐
│              │        │    Redis     │
│  发布模式：  │        │  diy:page:   │
│  读 Redis →  │──────→ │  {slug}      │
│  降级读 DB   │        │  diy:page:   │
│              │        │  {page_type} │
└──────────────┘        └──────────────┘
```

- **保存** → 写入 DB（draft/published 均由编辑器实时保存到 DB）
- **预览** → `GET /api/v1/diy/by-slug/{slug}?preview=true`，绕过 Redis，直接查询 draft 数据
- **发布** → 更新 `status=published` + `published_at`，调用 `enrich_page_data` 后写入/刷新 Redis 缓存
  - Redis key 为 `diy:page:{slug}`（所有页面）和 `diy:page:{page_type}`（系统页面，便于按类型直取）
- **C 端访问** → 优先读 Redis，miss 时降级到 DB 并回填
- **Redis 不可用** → 自动降级直查 DB（带熔断标志 `_redis_unavailable`），不阻塞功能
- **撤销发布** → 将 status 切回 `draft`，删除 Redis key

### 2.7 组件 JSON Schema 规范

每个组件配置由两部分组成：

```json
{
  // 组件实例的实际配置（编辑器保存）
  "config": {
    "title": "Hot Products",
    "source": "manual",
    "productIds": ["uuid-1", "uuid-2"],
    "displayCount": 6,
    "layout": "grid",
    "columns": 2
  },
  // 属性编辑面板的 Schema 定义（组件库读取）
  "configSchema": {
    "type": "object",
    "properties": {
      "title":    { "type": "string",  "title": "标题" },
      "source":   { "type": "string",  "title": "数据源", "enum": ["manual","category","ai_recommend"] },
      "category": { "type": "string",  "title": "商品分类" },
      "productIds": {
        "type": "array", "title": "手动选品",
        "items": { "type": "string" },
        "ui:widget": "product-picker"
      },
      "displayCount": { "type": "integer", "title": "展示数量", "default": 6 },
      "layout":   { "type": "string",  "title": "布局", "enum": ["grid","list","scroll"] },
      "columns":  { "type": "integer", "title": "列数", "default": 2 }
    }
  }
}
```

`ui:widget` 自定义字段用于编辑器渲染对应类型的控件：
- `product-picker` → 商品选择弹窗
- `coupon-picker` → 优惠券选择器
- `rich-editor` → 富文本编辑器
- `image-upload` → 图片上传
- `datetime` → 日期时间选择器
- `color` → 颜色选择器
- `icon` → iconify 图标选择器

---

## 三、管理端前端设计

> 完全基于现有技术栈：Vue 3 + NaiveUI + UnoCSS + vue-draggable-plus + Pinia。无需引入新的 UI 库。

### 3.1 组件目录结构

```
admin/src/
├── views/
│   ├── diy/                          # 一体化编辑器（页面列表+站点配置+组件库+画布）
│   │   └── index.vue
│   └── diy-editor/                   # 经典三栏编辑器（独立页面编辑）
│       ├── index.vue
│       └── modules/
│           ├── ComponentPanel.vue
│           ├── PreviewCanvas.vue
│           ├── PropertyPanel.vue
│           ├── DraggableComponent.vue
│           ├── DynamicForm.vue
│           ├── renderers/            # 15 个渲染器
│           │   ├── BannerRenderer.vue
│           │   ├── ...（共15个）
│           │   └── NavGroupRenderer.vue
│           └── widgets/              # 自定义表单控件
│               ├── ProductPicker.vue
│               ├── CouponPicker.vue
│               ├── ImageUpload.vue
│               └── RichTextEditor.vue
├── service/api/
│   └── diy.ts
├── store/modules/
│   └── diy/
│       └── index.ts
└── router/routes/
    └── index.ts
```

### 3.2 路由注册

```typescript
// router/routes/index.ts 新增
{
  name: 'site',
  path: '/site',
  meta: {
    title: '站点',
    i18nKey: 'route.site',
    icon: 'mdi:web',
    order: 6,
    roles: ['super_admin', 'admin', 'operator']
  },
  redirect: '/site/decoration',
  children: [
    {
      name: 'site-decoration',
      path: '/site/decoration',
      component: 'layout.base$view.diy',
      meta: { title: '页面装修', i18nKey: 'route.site-decoration', roles: ['super_admin', 'admin', 'operator'] }
    },
    {
      name: 'site-decoration-editor',
      path: '/site/decoration/editor/:id',
      component: 'layout.base$view.diy-editor',
      meta: { title: '页面编辑器', i18nKey: 'route.site-decoration-editor', hideInMenu: true, activeMenu: 'site-decoration', roles: ['super_admin', 'admin', 'operator'] }
    }
  ]
}
```

### 3.3 可视化编辑器布局

本系统提供两种编辑器形态，分别适配不同的装修场景：

1. **一体化编辑器**（`views/diy/index.vue`）
   - 左侧折叠面板：页面列表（NCollapse 折叠）+ 站点配置 + 组件库
   - 中间区域：支持实时预览（iframe）和结构编辑（画布）双模式 + 设备切换（desktop/tablet/mobile）
   - 右侧属性面板：同时支持组件属性和站点配置编辑

2. **经典三栏编辑器**（`views/diy-editor/index.vue`）
   - 左侧组件库（280px）
   - 中间画布（flex，含手机模拟器）
   - 右侧属性面板（360px）
   - 底部工具栏含模板管理

```
┌──────────────┬──────────────────────────┬──────────────┐
│  ComponentPanel  │    PreviewCanvas        │ PropertyPanel │
│  (280px)         │    (flex:1, max-390px)  │  (360px)      │
│                  │                          │               │
│  ┌────────────┐  │  ┌────────────────────┐  │ ┌───────────┐ │
│  │ Basic       │  │  │    iPhone Frame    │  │ │ Component │ │
│  │ ┌────────┐  │  │  │  ┌──────────────┐ │  │ │ Settings  │ │
│  │ │ Banner  │  │  │  │  │ [Banner]     │ │  │ │           │ │
│  │ ├────────┤  │  │  │  ├──────────────┤ │  │ │ Title:    │ │
│  │ │ Search  │  │  │  │  │ [SearchBox]  │ │  │ │ [______] │ │
│  │ ├────────┤  │  │  │  ├──────────────┤ │  │ │           │ │
│  │ │ Image   │  │  │  │  │ [GoodsList]  │ │  │ │ Layout:   │ │
│  │ └────────┘  │  │  │  └──────────────┘ │  │ │ [grid ▾] │ │
│  ├────────────┤  │  │  │    ↕ 拖拽排序    │  │ │           │ │
│  │ Goods       │  │  │  │                  │  │ │ Columns:  │ │
│  │ ┌────────┐  │  │  │                    │  │ │ [2]       │ │
│  │ │GoodList │  │  │  └────────────────────┘  │ └───────────┘ │
│  │ └────────┘  │  │                          │               │
│  └────────────┘  │                          │               │
└──────────────┴──────────────────────────┴──────────────┘
│                          │ Toolbar                           │
│  [← Back] [Save Draft] [Preview] [Publish] [Templates]      │
└──────────────────────────────────────────────────────────────┘
```

### 3.4 拖拽方案

项目已依赖 `vue-draggable-plus` (v0.6.1)，基于 SortableJS 封装，完美适配 Vue 3。

**拖拽核心逻辑：**

```vue
<!-- diy-editor/index.vue 核心结构 -->
<template>
  <div class="diy-editor flex h-full">
    <!-- 左侧组件库 -->
    <ComponentPanel @add="handleAddComponent" />

    <!-- 中间画布 -->
    <div class="canvas-wrapper flex-1 flex justify-center overflow-y-auto bg-gray-100 p-4">
      <div class="phone-frame w-[390px] min-h-[844px] bg-white shadow-lg rounded-xl overflow-hidden">
        <VueDraggable
          v-model="pageComponents"
          :animation="200"
          ghost-class="ghost"
          handle=".drag-handle"
          @end="onDragEnd"
        >
          <DraggableComponent
            v-for="pc in pageComponents"
            :key="pc.id"
            :component="pc"
            :active="pc.id === activeId"
            @click="selectComponent(pc.id)"
            @remove="removeComponent(pc.id)"
          >
            <component :is="getRenderer(pc.component_code)" :config="pc.config" />
          </DraggableComponent>
        </VueDraggable>
      </div>
    </div>

    <!-- 右侧属性面板 -->
    <PropertyPanel
      :component="activeComponent"
      @update:config="updateComponentConfig"
    />
  </div>
</template>
```

**关键点：**
- 左侧组件库拖入画布 = 创建新 `PageComponent`，使用 `component.default_config` 作为初始 config
- 画布内拖拽 = 调整 `sort_order`，排序结果实时同步回 `pageComponents` 数组
- `vue-draggable-plus` 的 `group` 属性支持跨容器拖拽（组件库 → 画布）
- 渲染器组件位于 `diy-editor/modules/renderers/` 下，通过 `getRenderer(code)` 动态解析

### 3.5 属性编辑面板

`PropertyPanel` 同时支持两种编辑场景：

1. **组件属性编辑**（选中组件时）
   - `DynamicForm` 根据组件的 `config_schema` 动态渲染表单
   - 通过 `v-model` 双向绑定到 `component.config`

2. **站点配置编辑**（选中站点配置项时）
   - 支持 9 大配置项：品牌 / 主题 / 导航 / 分类 / 页脚 / SEO / i18n / 功能开关 / 货币
   - 同样通过 `DynamicForm` 渲染对应 Schema

`DynamicForm` 已支持全部 widget 类型：

```vue
<!-- PropertyPanel.vue 核心思路 -->
<template>
  <NScrollbar>
    <div v-if="!component && !siteConfigActive" class="p-4 text-gray-400 text-center">
      请选择一个组件或站点配置项
    </div>
    <div v-else class="p-4">
      <div class="flex items-center gap-2 mb-4">
        <NButton size="tiny" quaternary @click="$emit('remove')">
          <Icon icon="mdi:delete" />
        </NButton>
        <span class="font-semibold">{{ component?.component_name || siteConfigTitle }}</span>
      </div>

      <!-- 动态表单 -->
      <DynamicForm
        :schema="component?.config_schema || siteConfigSchema"
        :model-value="component?.config || siteConfigValue"
        @update:model-value="handleUpdate"
      />
    </div>
  </NScrollbar>
</template>
```

`DynamicForm` 组件根据 Schema 中 `type` + `ui:widget` 渲染对应控件：

| Schema type | ui:widget | 渲染控件 |
|-------------|-----------|----------|
| `string` | (无) | `NInput` |
| `string` | `textarea` | `NInput type=textarea` |
| `string` | `rich-editor` | 简易富文本（基于 contenteditable） |
| `string` | `color` | `NColorPicker` |
| `string` | `image-upload` | 图片上传（调 `/api/admin/v1/site/upload-image`） |
| `string` | `product-picker` | 弹窗 + `NDataTable` 选择商品 |
| `string` | `coupon-picker` | `NSelect` 选择优惠券 |
| `string` | `datetime` | `NDatePicker` |
| `string` | `icon` | iconify 图标选择器 |
| `number` / `integer` | (无) | `NInputNumber` |
| `boolean` | (无) | `NSwitch` |
| `array` | (无) | 动态列表（可增删项） |
| `enum` | (无) | `NSelect` |

### 3.6 API 封装

```typescript
// service/api/diy.ts
import { get, post, put, del } from './helper';

export const diyApi = {
  listPages: (params?) => get('/api/admin/v1/site/pages'),  // 返回 {system[], custom[]}，前端客户端过滤
  getPage: (key: string) => get(`/api/admin/v1/site/pages/${key}`),  // key=UUID或page_type
  createPage: (data) => post('/api/admin/v1/site/custom-pages', data),
  updatePage: (key, data) => put(`/api/admin/v1/site/pages/${key}`, data),
  deletePage: (id) => del(`/api/admin/v1/site/custom-pages/${id}`),
  publishPage: (key) => post(`/api/admin/v1/site/pages/${key}/publish`),
  unpublishPage: (key) => post(`/api/admin/v1/site/pages/${key}/unpublish`),
  duplicatePage: (id) => post(`/api/admin/v1/site/custom-pages/${id}/duplicate`),
  saveComponents: (key, data) => put(`/api/admin/v1/site/pages/${key}/components`, data),
  setDefault: (id) => put(`/api/admin/v1/site/pages/${id}`, { is_default: true }),
  getComponents: () => get('/api/admin/v1/site/components'),
  uploadImage: (file) => post('/api/admin/v1/site/upload-image', form, { 'Content-Type': 'multipart/form-data' }),
};
```

### 3.7 页面列表页

页面列表内嵌在一体化编辑器左侧面板（`NCollapse` 折叠），不再是独立的 `NDataTable` 页面：

- 系统页面和自定义页面统一展示
- 系统页面显示类型图标（home/category/product_detail），不可删除
- 自定义页面可创建/删除
- 折叠展开支持选中当前编辑页面，与画布联动
- 顶部操作区提供"新建页面"按钮，弹出 `NModal` 表单

### 3.8 已有资源复用

| 现有资源 | DIY 装修复用方式 |
|----------|-----------------|
| `vue-draggable-plus` | 画布拖拽排序 |
| `@sa/axios` (request) | API 调用 |
| NaiveUI 全家桶 | 编辑器全部 UI 控件 |
| UnoCSS | 编辑器样式（flex/grid/padding/color 等工具类） |
| `NDataTable` | 商品选择弹窗 |
| `NColorPicker` | 颜色配置 |
| `NImage` | 图片预览 |
| `NFormItem` / `NInput` / `NSelect` / `NSwitch` | 属性编辑面板 |
| iconify (`@iconify/vue`) | 组件图标 |
| Pinia | 编辑器状态管理 |
| vue-i18n | 国际化 |

---

## 四、Nuxt 前端渲染设计

### 4.1 数据获取

```typescript
// Nuxt 前端 — 首页渲染
// pages/index.vue (改造后)

<script setup lang="ts">
// 通过 site_profile.diyPageSlug 获取 DIY 页面 slug
const diySlug = computed(() => profile.value.diyPageSlug || '')
const diyUrl = computed(() => diySlug.value ? `/diy/pages/${diySlug.value}` : '/diy/pages/home')
const { data: diyPage } = await useFetch(diyUrl, { baseURL: runtimeConfig.public.apiBase, server: false })

// 降级：如果 DIY 首页不存在，回退到现有硬编码首页
if (!diyPage.value || !diyPage.value.components?.length) {
  // 保留现有 index.vue 的渲染逻辑
}
</script>
```

### 4.2 组件映射与渲染引擎

在 `portal-web/app/components/diy/` 目录下创建渲染组件：

```
portal-web/app/components/diy/
├── DiyPageRenderer.vue          # 页面渲染容器
├── DiyBanner.vue                # 轮播横幅
├── DiySearchBox.vue             # 搜索框
├── DiyImageAd.vue               # 图片广告
├── DiyTextBlock.vue             # 文本模块
├── DiyRichText.vue              # 富文本
├── DiyVideo.vue                 # 视频
├── DiyDivider.vue               # 分割线
├── DiyGoodsList.vue             # 商品列表
├── DiyGoodsSingle.vue           # 单商品卡片
├── DiyGoodsGroup.vue            # 商品分组（Tab 切换）
├── DiyCoupon.vue                # 优惠券
├── DiyCountdown.vue             # 倒计时
├── DiyNoticeBar.vue             # 公告栏
├── DiyNavGroup.vue              # 导航组
└── DiyBlank.vue                 # 空白占位
```

**核心渲染器：**

```vue
<!-- DiyPageRenderer.vue -->
<template>
  <div class="diy-page">
    <!-- pending 骨架屏 -->
    <div v-if="pending" class="diy-skeleton">
      <NSkeleton v-for="n in 3" :key="n" height="120" />
    </div>

    <!-- error 重试按钮 -->
    <div v-else-if="error" class="diy-error">
      <NButton @click="refresh">重试</NButton>
    </div>

    <!-- empty 空状态 -->
    <div v-else-if="!visibleComponents.length" class="diy-empty">
      暂无内容
    </div>

    <!-- 正常渲染 -->
    <template v-else>
      <component
        v-for="pc in visibleComponents"
        :key="pc.id"
        :is="componentMap[pc.component_code]"
        :config="pc.config"
        :data="pc.data"
      />
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{ components: any[]; pending?: boolean; error?: any }>();

// 支持 is_visible 过滤
const visibleComponents = computed(() =>
  (props.components || []).filter(c => c.is_visible !== false)
);

const componentMap: Record<string, any> = {
  banner:       resolveComponent('DiyBanner'),
  search_box:   resolveComponent('DiySearchBox'),
  image_ad:     resolveComponent('DiyImageAd'),
  text_block:   resolveComponent('DiyTextBlock'),
  rich_text:    resolveComponent('DiyRichText'),
  video:        resolveComponent('DiyVideo'),
  divider:      resolveComponent('DiyDivider'),
  goods_list:   resolveComponent('DiyGoodsList'),
  goods_single: resolveComponent('DiyGoodsSingle'),
  goods_group:  resolveComponent('DiyGoodsGroup'),
  coupon:       resolveComponent('DiyCoupon'),
  countdown:    resolveComponent('DiyCountdown'),
  notice_bar:   resolveComponent('DiyNoticeBar'),
  nav_group:    resolveComponent('DiyNavGroup'),
  blank:        resolveComponent('DiyBlank'),
};
</script>
```

> 说明：每个 DIY 组件接收 `config` 和 `data` 两个 prop，其中 `data` 为后端 `enrich_page_data` 内联的预取数据（如商品列表、优惠券详情等），Nuxt 端无需额外请求。

### 4.3 首页改造策略（渐进式）

1. **现有 `index.vue` 保留**，作为降级方案
2. **通过 `site_profile.diyPageSlug` 字段决定渲染哪个 DIY 页面**
3. **`diyPageSlug` 为空时**回退到 `/diy/pages/home`（系统首页）
4. **DIY 首页不存在时**回退到硬编码首页
5. **后台切换** → 管理员可随时"撤销发布" DIY 首页，站点自动回退到原版
6. **SEO** → 通过 `useHead` 输出 DIY 页面的 `title` 和 `description`

### 4.4 商品数据渲染

`DiyGoodsList` 等组件在 Nuxt 端通过 `useFetch` 调后端 API 获取实际商品数据：

```vue
<!-- DiyGoodsList.vue -->
<script setup lang="ts">
const props = defineProps<{ config: any }>();

const { data: products } = await useFetch('/api/v1/products/', {
  query: {
    category: props.config.source === 'category' ? props.config.category : undefined,
    ids: props.config.source === 'manual' ? props.config.productIds?.join(',') : undefined,
    limit: props.config.displayCount || 6,
  },
});
</script>
```

或者更优：后端 `GET /api/v1/diy/by-slug/{slug}` 直接内联渲染所需数据：

```json
{
  "components": [
    {
      "component_code": "goods_list",
      "config": { "title": "Hot Products", "layout": "grid", "columns": 2 },
      "data": {
        "products": [
          { "id": "...", "name": "Premium Dog Food", "price": 29.99, "images": ["..."] },
          ...
        ]
      }
    }
  ]
}
```

这样 Nuxt 端无需额外请求，直接渲染即可，且支持 CDN/Redis 整页缓存。建议后端 `DiyService` 中实现 `enrich_page_data()` 方法，自动识别需要数据填充的组件类型（`goods_list`、`coupon` 等）并内联数据。

---

## 五、实施路径

### 第一阶段：基础设施 + 核心组件（1-2 周）✅ 已完成

| 任务 | 内容 | 状态 |
|------|------|------|
| 数据库迁移 | 创建 3 张表 + 迁移脚本 `0008_add_diy_tables.py` + 内置组件种子数据 | ✅ |
| 系统页面种子 | `0009_seed_system_diy_pages.py` 预置 home/category/product_detail | ✅ |
| ORM + Repository | 新增 ORMDiyPage（含模板字段）+ 基础 Repository | ✅ |
| Admin DIY API | 页面 CRUD + 组件库查询 + 图片上传（挂载 `/api/admin/v1/site`） | ✅ |
| 公开 DIY API | `/api/v1/diy/pages/{page_type}` + `/by-slug/{slug}` 渲染接口 | ✅ |
| Admin 一体化编辑器 | `views/diy/index.vue` 折叠面板布局 + 设备切换 | ✅ |
| Admin 经典编辑器骨架 | `views/diy-editor/` 三栏布局 + `vue-draggable-plus` 拖拽画布 | ✅ |
| 属性编辑面板 | `DynamicForm` 全部基础控件（文本/数字/开关/选择/颜色） | ✅ |
| 基础组件渲染器 | Banner / SearchBox / ImageAd / TextBlock / Divider / Blank | ✅ |
| Nuxt 渲染容器 | `DiyPageRenderer`（含 pending/error/empty 状态）+ 首页降级 | ✅ |

### 第二阶段：商品组件 + 营销组件（1-2 周）✅ 已完成

| 任务 | 内容 | 状态 |
|------|------|------|
| 商品选择器 | `widgets/ProductPicker.vue`（弹窗 + NDataTable 搜索选品） | ✅ |
| GoodsList 组件 | 编辑器渲染 + Nuxt 端渲染 + 数据内联 | ✅ |
| GoodsSingle / GoodsGroup | 编辑器 + Nuxt 渲染 | ✅ |
| 优惠券选择器 | `widgets/CouponPicker.vue` | ✅ |
| Coupon / Countdown / NoticeBar | 编辑器 + Nuxt 渲染 | ✅ |
| NavGroup 组件 | 导航组编辑器 + 渲染 | ✅ |
| 图片上传 | `widgets/ImageUpload.vue` 上传到 `uploads/diy/` 目录 | ✅ |
| 发布/缓存 | Redis 缓存层（`diy:page:{slug}` + `diy:page:{page_type}`）+ 发布失效 + 熔断降级 | ✅ |
| 模板系统 | 模板列表（industry_tag 过滤+分页）+ 保存/应用模板 | ✅ |

### 第三阶段：完善与优化（1-2 周）

| 任务 | 内容 | 状态 |
|------|------|------|
| 富文本编辑器 | `widgets/RichTextEditor.vue` widget（`ui:widget: rich-editor`） | ✅ 已提前实现 |
| Video 组件 | 视频渲染 + 封面图 | ⬜ 待实现 |
| 预览功能 | `preview=true` 参数绕过 Redis 直查 DB（含 draft） | ✅ |
| 设为首页 | `is_default` 机制 + 系统页 page_type 控制 | ✅ |
| 与 `site_profiles` 共存 | Profile 配置中 `diyPageSlug` 字段 | ✅ |
| 移动端适配 | Nuxt 端响应式 + Tailwind 断点 | ⬜ 待实现 |
| SEO 优化 | `useHead` 输出页面级 title/description | ✅ 已提前实现 |
| 权限完善 | Casbin 策略 + 前端按钮级权限 | ⬜ 待实现 |

### 与现有 `site_profiles` 的共存策略

```
site_profiles.config (JSONB)
├── branding           # 品牌信息（logo、名称、颜色）
├── theme              # 主题配置
├── navigation         # 主导航
├── diyPageSlug        # ← 新增：DIY 页面 slug（为空则使用默认首页 /diy/pages/home）
├── sections           # 现有硬编码首页 Section（diyPageSlug 为空时生效）
└── seo                # SEO 默认配置
```

- `diyPageSlug` 为空 → 沿用 `/diy/pages/home` 系统首页逻辑（向后兼容）
- `diyPageSlug` 有值 → 渲染对应 DIY 页面
- DIY 首页不存在时 → 回退到硬编码首页
- 管理员在 Admin 的 `site_profiles` 编辑页可直接选择已发布的 DIY 页面作为首页

---

## 六、关键设计决策总结

| 决策 | 理由 |
|------|------|
| **新增独立 DIY 表而非复用 site_profiles JSONB** | DIY 页面有复杂的关联关系（页面→组件→配置），JSONB 难以维护和查询 |
| **不引入新的拖拽库** | 项目已有 `vue-draggable-plus`，完全满足需求 |
| **组件定义用数据库存储而非代码枚举** | 支持后续热新增组件，无需发版 |
| **先删后插的组件保存策略** | 简单可靠，避免增量差异比较的复杂性 |
| **发布 = status 变更 + Redis 缓存** | 与现有 site_profiles 的 Redis 缓存模式一致 |
| **首页降级策略** | DIY 首页不存在时回退到硬编码首页，零风险上线 |
| **整页保存而非逐组件保存** | 减少请求次数，保证组件顺序的原子性 |
| **数据内联而非 Nuxt 端二次请求** | 减少前端请求数，支持整页 CDN 缓存 |
| **Admin API 挂载在 /site 前缀下** | DIY 装修与站点配置一体化，统一在站点管理域下 |
| **系统页+自定义页二元模型** | home/category/product_detail 三大流量页纳入装修体系，覆盖真实电商场景 |
| **模板系统** | 支持行业标签+保存为模板+应用模板，快速复制装修方案 |
| **一体化编辑器+经典编辑器双形态** | 一体化编辑器适合日常配置，经典三栏适合深度装修 |
| **Redis 可用性熔断** | Redis 不可用时自动降级直查 DB，不阻塞功能 |
| **图片上传使用本地目录** | 初期简化部署，后续可迁移到 MinIO |
| **listPages 客户端过滤** | 系统页+自定义页合并后数据量小，前端过滤即可 |
*（内容由AI生成，仅供参考）*
*（内容由AI生成，仅供参考）*
*（内容由AI生成，仅供参考）*
