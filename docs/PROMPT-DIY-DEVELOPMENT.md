---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 14f48488fead00d28e11c31f9845685c_2a99d38e8b4811f184f2525400e6dd8f
    ReservedCode1: uTIOpBGZIse7nAzihw29nyAAVp/JkHo5B0k3gN2e9OlIGMnAPq0mhH84m2iwE+9PuqAyqeRAF+l0uLdsDwOdx9SlNePIE4IWk2IRpP0DtC+gXPiO9jBksc2owfayBctkLsdn6QXJcs9q+KwXEaslTsTWhDExM7AoLaPjAmYxAjc6og5yz1cdfWWJWHI=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 14f48488fead00d28e11c31f9845685c_2a99d38e8b4811f184f2525400e6dd8f
    ReservedCode2: uTIOpBGZIse7nAzihw29nyAAVp/JkHo5B0k3gN2e9OlIGMnAPq0mhH84m2iwE+9PuqAyqeRAF+l0uLdsDwOdx9SlNePIE4IWk2IRpP0DtC+gXPiO9jBksc2owfayBctkLsdn6QXJcs9q+KwXEaslTsTWhDExM7AoLaPjAmYxAjc6og5yz1cdfWWJWHI=
---



# Forge DIY 页面装修 — CodeBuddy 开发提示词

> 基于 `Forge_DIY页面装修方案.md` 生成。分三个阶段，每个阶段为独立的 CodeBuddy 提示词，可直接复制使用。

---

# 第一阶段：基础设施 + 核心组件

---

## 项目上下文

- 项目路径：`D:\codeRepo\forge`
- 后端：FastAPI + SQLAlchemy 2.0(async) + PostgreSQL + Redis + MinIO，DDD 分层：`domain/` → `application/` → `infrastructure/` → `api/`
- Admin 前端：Vue 3 + Vite + TypeScript + NaiveUI + UnoCSS + Pinia + vue-draggable-plus 0.6.1，路径 `admin/src/`
- Nuxt 前端：Nuxt 3 + Vue 3 + Tailwind CSS 4，路径 `frontend/`
- 表名小写蛇形，主键 UUID `gen_random_uuid()`，时间戳 `created_at` + `updated_at` `server_default=now()`
- ORM 模型继承 `Base`，定义 `to_dict()` 方法
- Admin API 直接用 `AsyncSession` + ORM 查询，权限 `Depends(require_permission("settings", "manage"))`
- Admin 前端 API 用 `get/post/put/del` helper
- 现有 `site_profiles` 表有 JSONB `config` 字段，Nuxt 通过 `/api/v1/site-profile/` 拉取渲染首页

---

## 任务目标

实现 DIY 页面装修功能的基础设施和 6 个核心组件（Banner / SearchBox / ImageAd / TextBlock / Divider / Blank），包含完整的后端 API + Admin 编辑器骨架 + Nuxt 渲染容器。

---

## Part A：数据库 & 后端基础设施

### A1. Alembic 迁移脚本

创建文件：`backend/src/forge/migrations/versions/0008_add_diy_tables.py`

新增 3 张表：

**diy_pages**（页面定义）：

| 列名 | 类型 | 约束 |
|------|------|------|
| id | UUID | PK, DEFAULT gen_random_uuid() |
| name | VARCHAR(128) | NOT NULL |
| slug | VARCHAR(128) | NOT NULL, UNIQUE |
| title | VARCHAR(256) | NOT NULL DEFAULT '' |
| description | TEXT | NOT NULL DEFAULT '' |
| page_type | VARCHAR(32) | NOT NULL DEFAULT 'custom' |
| status | VARCHAR(16) | NOT NULL DEFAULT 'draft' |
| is_default | BOOLEAN | NOT NULL DEFAULT FALSE |
| published_at | TIMESTAMPTZ | nullable |
| created_by | UUID | FK → admin_users(id), nullable |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |
| updated_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |

索引：`idx_diy_pages_slug` ON slug, `idx_diy_pages_status` ON status, `idx_diy_pages_type` ON page_type

**diy_components**（组件库）：

| 列名 | 类型 | 约束 |
|------|------|------|
| id | UUID | PK |
| code | VARCHAR(64) | NOT NULL UNIQUE |
| name | VARCHAR(128) | NOT NULL |
| category | VARCHAR(32) | NOT NULL DEFAULT 'basic' |
| icon | VARCHAR(64) | NOT NULL DEFAULT 'mdi:widget' |
| default_config | JSONB | NOT NULL DEFAULT '{}' |
| config_schema | JSONB | NOT NULL DEFAULT '{}' |
| is_system | BOOLEAN | NOT NULL DEFAULT TRUE |
| sort_order | INTEGER | NOT NULL DEFAULT 0 |
| is_active | BOOLEAN | NOT NULL DEFAULT TRUE |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |
| updated_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |

索引：`idx_diy_components_category` ON category

**diy_page_components**（页面组件实例）：

| 列名 | 类型 | 约束 |
|------|------|------|
| id | UUID | PK |
| page_id | UUID | FK → diy_pages(id) ON DELETE CASCADE, NOT NULL |
| component_id | UUID | FK → diy_components(id), NOT NULL |
| sort_order | INTEGER | NOT NULL DEFAULT 0 |
| config | JSONB | NOT NULL DEFAULT '{}' |
| is_visible | BOOLEAN | NOT NULL DEFAULT TRUE |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |
| updated_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |

索引：`idx_dpc_page_id` ON page_id, `idx_dpc_page_sort` ON (page_id, sort_order)

迁移脚本还需包含 INSERT 种子数据，插入以下 8 个系统内置组件（完整 SQL 参考方案 1.5 节，code/name/category/icon/default_config/config_schema/sort_order 必须与方案原文完全一致）：

| code | name | category | sort_order |
|------|------|----------|------------|
| banner | 轮播横幅 | basic | 1 |
| search_box | 搜索框 | basic | 2 |
| image_ad | 图片广告 | basic | 3 |
| text_block | 文本模块 | basic | 4 |
| rich_text | 富文本 | basic | 5 |
| video | 视频模块 | basic | 6 |
| divider | 分割线 | basic | 7 |
| blank | 空白占位 | layout | 30 |

每个组件的 `default_config` 和 `config_schema` 必须使用方案 1.5 节中的完整 JSON 字符串。

### A2. 领域模型

创建文件：`backend/src/forge/domain/diy/__init__.py`
创建文件：`backend/src/forge/domain/diy/models.py`

定义以下枚举和 dataclass（完整代码参考方案 2.2 节）：

- `PageStatus(str, Enum)`：DRAFT="draft", PUBLISHED="published"
- `PageType(str, Enum)`：HOME="home", CATEGORY="category", PRODUCT_DETAIL="product_detail", CUSTOM="custom"
- `ComponentCategory(str, Enum)`：BASIC="basic", GOODS="goods", MARKETING="marketing", LAYOUT="layout"
- `DiyComponent` dataclass：id, code, name, category, icon, default_config, config_schema, is_system, sort_order, is_active
- `PageComponent` dataclass：id, page_id, component_id, sort_order, config, is_visible
- `DiyPage` dataclass（聚合根）：id, name, slug, title, description, page_type, status, is_default, published_at, created_by, components(list[PageComponent]), created_at, updated_at，含类方法 `create()`、实例方法 `publish()`、`add_component()`、`reorder()`

### A3. ORM 模型

追加到 `backend/src/forge/infrastructure/persistence/models.py` 末尾：

- `ORMDiyPage(Base)`：表名 `diy_pages`，含 `components` relationship（`back_populates="page"`, `cascade="all, delete-orphan"`）
- `ORMDiyComponent(Base)`：表名 `diy_components`
- `ORMDiyPageComponent(Base)`：表名 `diy_page_components`，含 `page` 和 `component` relationship（`component` 使用 `lazy="joined"`）

每个 ORM 类必须定义 `to_dict()` 方法。完整字段和参数参考方案 2.3 节，务必逐字段对齐。

### A4. DTO

创建文件：`backend/src/forge/application/dtos/diy_dtos.py`

定义 Pydantic BaseModel：

- `DiyPageCreateDTO`：name(str), slug(str), title(str)="", description(str)="", page_type(str)="custom"
- `DiyPageUpdateDTO`：name, title, description 均为 Optional
- `PageComponentDTO`：component_id(UUID), sort_order(int), config(dict), is_visible(bool)=True，用于 `PUT /pages/{id}/components` 接收请求体

### A5. Repository

创建文件：`backend/src/forge/infrastructure/persistence/repositories/diy_repo.py`

实现 `SQLAlchemyDiyRepository`，提供：

- `get_page_by_slug(db, slug)` → ORMDiyPage（eager-load components + component）
- `get_page_by_id(db, page_id)` → ORMDiyPage（eager-load）
- `list_pages(db, page, page_size, status, page_type)` → dict(items, total, page, page_size)
- `create_page(db, data)` → ORMDiyPage
- `update_page(db, page_id, data)` → ORMDiyPage
- `delete_page(db, page_id)` → None
- `get_components(db)` → list[ORMDiyComponent]
- `save_components(db, page_id, components)` → 先 `delete(ORMDiyPageComponent).where(page_id=...)` 后批量 insert
- `set_default(db, page_id)` → 先 `update(ORMDiyPage).where(is_default=True).values(is_default=False)` 再设置目标 page 的 is_default=True

### A6. Application Service

创建文件：`backend/src/forge/application/services/diy_service.py`

`DiyService`——构造函数注入 `DiyRepository` 接口，封装业务逻辑：

- `create_page(...)`
- `publish_page(page_id)`：更新 status + published_at + 失效 Redis `diy:page:{slug}` 和 `diy:page:default`
- `duplicate_page(page_id)`：深拷贝页面及其组件
- `get_page_for_render(slug, preview=False)`：preview=True 直查 DB，否则优先 Redis → DB 降级回填。返回组件列表 JSON，基础阶段不需 enrich 数据

### A7. API 路由

创建文件：`backend/src/forge/api/admin/v1/diy.py`

Admin 端路由（prefix `/api/admin/v1/diy`），所有路由 `dependencies=[Depends(require_permission("settings", "manage"))]`：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/pages` | 列表，Query: page(1), page_size(20), status, page_type |
| POST | `/pages` | 创建页面 |
| GET | `/pages/{page_id}` | 详情（含组件） |
| PUT | `/pages/{page_id}` | 更新基础信息 |
| DELETE | `/pages/{page_id}` | 删除页面 |
| POST | `/pages/{page_id}/publish` | 发布 |
| POST | `/pages/{page_id}/duplicate` | 复制 |
| PUT | `/pages/{page_id}/components` | 保存组件列表 |
| POST | `/pages/{page_id}/set-default` | 设为首页 |
| GET | `/components` | 组件库列表 |
| POST | `/upload-image` | 上传图片到 MinIO（`diy-images` bucket），返回 URL |

实现方式：直接使用 `AsyncSession` + ORM 查询，与现有 `api/admin/v1/site_profile.py` 风格一致。publish 接口需操作 Redis client（已存在于项目中）。

创建文件：`backend/src/forge/api/v1/diy.py`

公开端路由（prefix `/api/v1/diy`，无需鉴权）：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/pages/{slug}` | Query: preview(bool)=False。返回已发布页面组件 JSON |
| GET | `/pages/default` | 获取 is_default=True 的页面数据 |

将新路由注册到 FastAPI app（在对应 `__init__.py` 或路由注册处 include）。

---

## Part B：Admin 前端

### B1. API 封装

创建文件：`admin/src/service/api/diy.ts`

实现 `diyApi` 对象（参考方案 3.6 节），所有方法使用项目已有的 `get/post/put/del` helper：

- `listPages(params)`, `getPage(id)`, `createPage(data)`, `updatePage(id, data)`, `deletePage(id)`, `publishPage(id)`, `duplicatePage(id)`, `saveComponents(id, data)`, `setDefault(id)`, `getComponents()`, `uploadImage(file)`（FormData）

### B2. Pinia Store

创建文件：`admin/src/store/modules/diy.ts`

`useDiyStore`：

- state：`currentPage`(当前页面数据，含 components 数组), `componentsLibrary`(组件库列表)
- actions：`fetchPage(id)`（调 getPage 并存入 currentPage）, `fetchComponentsLibrary()`（调 getComponents）, `addComponent(component)`（用 default_config 创建 PageComponent）, `removeComponent(id)`, `updateComponentConfig(id, config)`, `reorderComponents(newOrder)`（更新 sort_order）, `saveComponents(pageId)`（调 saveComponents API）

### B3. 路由注册

在 `admin/src/router/routes/index.ts` 新增 `/diy` 路由组（参考方案 3.2 节）：

- `/diy` → redirect `/diy/pages`
- `/diy/pages` → `layout.base$view.diy`
- `/diy/editor/:id` → `layout.base$view.diy-editor`（`hideInMenu: true`, `activeMenu: 'diy-pages'`）

meta：`roles: ['super_admin', 'admin', 'operator']`

### B4. 页面列表页

创建文件：`admin/src/views/diy/index.vue`

复刻 `views/products/index.vue` 模式：

- 过滤栏：`NSpace` + `NInput`（搜索名称/slug）+ `NSelect`（status/page_type 筛选）
- 表格 `NDataTable`：列 — 名称、Slug、类型、状态（NTag 区分 draft/published）、更新时间、操作
- 操作列按钮：编辑（跳转 `/diy/editor/{id}`）、预览（新窗口 `/api/v1/diy/pages/{slug}`）、发布/撤销发布（toggle）、复制、设为首页、删除（NPopconfirm）
- `NButton type=primary` 新建页面 → 弹窗输入 name + slug → 创建后跳转编辑器

### B5. 可视化编辑器

创建文件：`admin/src/views/diy/editor.vue`

三栏布局（参考方案 3.3 节和 3.4 节）：

**左侧 ComponentPanel（280px）**：`admin/src/views/diy/components/ComponentPanel.vue`

- 从 store 读取 `componentsLibrary`，按 category 分组（basic / goods / marketing / layout）
- 每个组件项显示 icon + name，点击触发 `@add` 事件
- 拖拽支持：使用 `vue-draggable-plus` 的 `group` 实现从组件库拖入画布（clone 模式）

**中间 PreviewCanvas（flex:1, max-width:390px）**：`admin/src/views/diy/components/PreviewCanvas.vue`

- 手机模拟器外壳：`w-[390px] min-h-[844px] bg-white shadow-lg rounded-xl overflow-hidden`
- 内部使用 `VueDraggable v-model="pageComponents"` 实现画布内拖拽排序
- `ghost-class="ghost"`, `handle=".drag-handle"`, `@end` 触发 `onDragEnd` 更新 sort_order

**右侧 PropertyPanel（360px）**：`admin/src/views/diy/components/PropertyPanel.vue`

- 选中组件时显示属性编辑区，未选中显示"请选择一个组件"占位
- 顶部：删除按钮 + 组件名称
- 动态表单 `DynamicForm`：根据组件 `config_schema` 渲染控件
- `DynamicForm` 支持以下 Schema type + ui:widget 映射：

| Schema type | ui:widget | 控件 |
|-------------|-----------|------|
| string | (默认) | NInput |
| string | textarea | NInput type=textarea |
| string | color | NColorPicker |
| integer/number | (默认) | NInputNumber |
| boolean | (默认) | NSwitch |
| string | (enum) | NSelect |

- `@update:model-value` → store `updateComponentConfig`

**画布中组件项**：`admin/src/views/diy/components/DraggableComponent.vue`

- 包装每个画布中的组件实例，含拖拽手柄（`.drag-handle`）、选中高亮、删除按钮
- 插槽渲染对应的 Renderer 组件

**6 个基础 Renderer**（`admin/src/views/diy/components/renderers/`）：

每个 Renderer 接收 `config` prop，在手机模拟器中渲染组件预览：

- `BannerRenderer.vue`：轮播占位（显示 slides 数量 + autoplay 状态）
- `SearchBoxRenderer.vue`：按 config 渲染搜索框外观（placeholder/style/bgColor）
- `ImageAdRenderer.vue`：图片广告占位（显示 mode + height，有 image 时显示 NImage）
- `TextBlockRenderer.vue`：按 textAlign/fontSize/color/padding 渲染文本
- `DividerRenderer.vue`：按 style/color/height 渲染分割线
- `BlankRenderer.vue`：按 height/backgroundColor 渲染空白块

### B6. 编辑器工具栏

在 `editor.vue` 底部添加工具栏：`[← Back] [Save Draft] [Preview] [Publish]`

- Save → 调用 `diyApi.saveComponents` + `diyApi.updatePage`
- Preview → `window.open('/api/v1/diy/pages/{slug}?preview=true')`
- Publish → 调用 `diyApi.publishPage`

---

## Part C：Nuxt 前端

### C1. 渲染组件

在 `frontend/app/components/diy/` 下创建以下文件：

- `DiyPageRenderer.vue`：渲染容器，遍历 `components`，用 `componentMap` 按 `component_code` 动态匹配渲染组件。componentMap 映射表参考方案 4.2 节（第一阶段仅映射 banner / search_box / image_ad / text_block / divider / blank / rich_text / video，后两类可先做占位）
- `DiyBanner.vue`：轮播横幅，使用 Tailwind CSS 样式
- `DiySearchBox.vue`：搜索框，emit search 事件
- `DiyImageAd.vue`：图片广告，NImage + link
- `DiyTextBlock.vue`：文本模块，动态样式
- `DiyDivider.vue`：分割线
- `DiyBlank.vue`：空白占位

每个组件接收 `config` prop，按配置渲染。使用 Tailwind CSS 4 样式。

### C2. 首页改造

修改 `frontend/app/pages/index.vue`：

```typescript
const { data: diyPage } = await useFetch('/api/v1/diy/pages/default');

// 有 DIY 首页数据 → 渲染 DiyPageRenderer
// 无数据或空组件 → 保留现有硬编码首页渲染逻辑（降级）
```

---

## 第一阶段验收检查点

- [ ] `alembic upgrade head` 成功创建 3 张表 + 种子数据 8 个组件
- [ ] `GET /api/admin/v1/diy/components` 返回 8 个组件
- [ ] Admin 端 CRUD 页面：新建 → 编辑 → 删除 完整可用
- [ ] 编辑器三栏布局正常，可从组件库添加组件到画布
- [ ] 画布内拖拽排序正常，排序结果保存到 DB
- [ ] 属性面板：文本/数字/开关/颜色/选择 控件可编辑配置
- [ ] `PUT /api/admin/v1/diy/pages/{id}/components` 保存组件成功
- [ ] 发布后 `GET /api/v1/diy/pages/{slug}` 返回组件 JSON
- [ ] Nuxt 首页：有 DIY 首页时渲染 DiyPageRenderer，无时回退硬编码首页
- [ ] `POST /api/admin/v1/diy/upload-image` 上传成功返回 MinIO URL

---

# 第二阶段：商品组件 + 营销组件

---

## 项目上下文

第一阶段已完成，现有：
- 3 张 DIY 表 + 8 个系统内置组件（banner/search_box/image_ad/text_block/rich_text/video/divider/blank）
- Admin 页面 CRUD + 三栏编辑器骨架 + DynamicForm 基础控件
- Nuxt DiyPageRenderer + 6 个渲染组件 + 首页降级
- `diyApi`、`useDiyStore`、路由已注册

---

## 任务目标

在 Phase 1 基础设施之上，实现商品相关组件（GoodsList / GoodsSingle / GoodsGroup）和营销组件（Coupon / Countdown / NoticeBar / NavGroup），以及配套的 product-picker / coupon-picker widget、MinIO 图片上传集成、Redis 缓存层。

---

## Part A：后端增强

### A1. 补充种子数据

修改已有迁移脚本或新增迁移，追加 INSERT 以下 7 个组件的种子数据（code/name/category/icon/default_config/config_schema 必须与方案 1.5 节完全一致）：

| code | name | category | sort_order |
|------|------|----------|------------|
| goods_list | 商品列表 | goods | 10 |
| goods_single | 单商品卡片 | goods | 11 |
| goods_group | 商品分组 | goods | 12 |
| coupon | 优惠券 | marketing | 20 |
| countdown | 倒计时 | marketing | 21 |
| notice_bar | 公告栏 | marketing | 22 |
| nav_group | 导航组 | layout | 31 |

总计 15 个系统内置组件。

### A2. DiyService 增强

在 `backend/src/forge/application/services/diy_service.py` 新增：

**`enrich_page_data(page)`** 方法：

遍历 page 的 components，对需要数据内联的组件类型自动填充实际数据：
- `goods_list`：根据 source 字段 — `manual` 时按 `productIds` 查询商品；`category` 时按 `category` 查询；`ai_recommend` 时预留接口。调用现有 ProductService 或直接 ORM 查询 products 表
- `goods_single`：按 `productId` 查询单个商品
- `goods_group`：遍历 `tabs`，按每个 tab 的 `category` 查询商品
- `coupon`：按 `couponId` 查询优惠券

返回结构为每个组件增加 `data` 字段：`{ ...component, data: { products: [...] } }` 或 `{ ...component, data: { coupon: {...} } }`。

**`get_page_for_render(slug, preview)`** 方法增强：

- 非预览模式：优先从 Redis `diy:page:{slug}` 读取（JSON），miss 时查 DB → enrich → JSON 序列化写入 Redis（TTL 可设 3600s） → 返回
- 预览模式：直接查 DB → enrich → 返回（不写 Redis）

**`publish_page(page_id)`** 修改：

- 发布时调用 `enrich_page_data` → 写入 Redis `diy:page:{slug}`
- 同时更新/写入 `diy:page:default`（如果 `is_default=True`）

**`set_default(page_id)`** 增强：

- 先将所有 `is_default=True` 设为 False
- 再设目标 page 的 `is_default=True`
- 刷新 Redis `diy:page:default`

**`unpublish_page(page_id)`**（新增）：

- status 切回 draft
- 删除 Redis `diy:page:{slug}` 和（如适用）`diy:page:default`

### A3. API 补充

Admin 路由新增：

- `POST /pages/{page_id}/unpublish`：撤销发布（有了 publish 就有 unpublish）

公开路由增强：

- `GET /pages/{slug}`：返回 enrich 后的数据（含 `data` 字段内联商品/优惠券实际数据）
- `GET /pages/default`：同上，基于 `is_default=True` 查询

### A4. 图片上传完善

`POST /api/admin/v1/diy/upload-image` 完善实现：

- 接收 `UploadFile`
- 上传到 MinIO `diy-images` bucket（项目中已有 MinIO client，可复用 `clients/` 下的逻辑）
- 返回公开访问 URL

---

## Part B：Admin 前端增强

### B1. 商品选择器 Widget

创建 `admin/src/views/diy/components/widgets/ProductPicker.vue`：

- 弹窗组件（`NModal`），内含 `NDataTable` 展示商品列表（分页、搜索框）
- 支持多选（checkboxes），确认后返回选中的 `productIds[]`
- 在 `DynamicForm` 中，当 schema 属性含 `ui:widget: "product-picker"` 时渲染此组件

同时更新 `DynamicForm`，新增 widget 映射：

| ui:widget | 组件 |
|-----------|------|
| product-picker | ProductPicker |
| coupon-picker | NCouponPicker（见 B2） |
| image-upload | NUploadImage（见 B3） |
| datetime | NDatePicker |
| icon | NIconPicker（简单 iconify 搜索选择） |

### B2. 优惠券选择器 Widget

创建 `admin/src/views/diy/components/widgets/CouponPicker.vue`：

- `NSelect` 或 `NModal` + `NDataTable`，从 `/api/admin/v1/coupons` 获取优惠券列表
- 单选模式，返回 `couponId`
- 若项目中尚无 coupons API，先做占位组件，提示"即将上线"

### B3. 图片上传 Widget

在 `DynamicForm` 中为 `ui:widget: "image-upload"` 渲染上传控件：

- `NUpload` 或自定义组件，调 `diyApi.uploadImage(file)`
- 上传成功后回写 URL 到 config

### B4. 新增 Renderer（编辑器画布预览）

在 `admin/src/views/diy/components/renderers/` 新增：

- `GoodsListRenderer.vue`：显示商品网格占位（columns × displayCount 网格）
- `GoodsSingleRenderer.vue`：单商品卡片占位
- `GoodsGroupRenderer.vue`：Tab 切换 + 商品网格占位
- `CouponRenderer.vue`：优惠券卡片占位
- `CountdownRenderer.vue`：倒计时显示（endTime）
- `NoticeBarRenderer.vue`：公告滚动条
- `NavGroupRenderer.vue`：图标 + 文字网格

### B5. editor.vue 更新

将 7 个新 Renderer 注册到 `getRenderer()` 映射中。

---

## Part C：Nuxt 前端增强

### C1. 新增渲染组件

在 `frontend/app/components/diy/` 下新增：

- `DiyGoodsList.vue`：接收 `config` 和 `data.products`。按 layout(grid/list/scroll) 和 columns 渲染商品卡片。使用 Tailwind CSS 4，复用项目已有的 ProductCard 组件（如有）
- `DiyGoodsSingle.vue`：单商品卡片，按 layout(vertical/horizontal) 渲染
- `DiyGoodsGroup.vue`：Tab 切换（`config.tabs`），每个 tab 下渲染商品网格。Tab 切换可用 `@nuxt/ui` 的 `UTabs` 或手写
- `DiyCoupon.vue`：优惠券卡片，按 style(card/banner) 渲染
- `DiyCountdown.vue`：倒计时组件，基于 `endTime` 计算剩余时间，`setInterval` 实时刷新
- `DiyNoticeBar.vue`：公告栏，水平滚动文字（CSS animation），支持关闭
- `DiyNavGroup.vue`：导航组，按 `columns` 列数渲染 icon+text 网格

### C2. DiyPageRenderer 更新

将 7 个新组件的 `component_code` 映射注册到 `componentMap`。

完整映射表：

| component_code | 组件 |
|----------------|------|
| banner | DiyBanner |
| search_box | DiySearchBox |
| image_ad | DiyImageAd |
| text_block | DiyTextBlock |
| rich_text | DiyRichText（占位） |
| video | DiyVideo（占位） |
| divider | DiyDivider |
| blank | DiyBlank |
| goods_list | DiyGoodsList |
| goods_single | DiyGoodsSingle |
| goods_group | DiyGoodsGroup |
| coupon | DiyCoupon |
| countdown | DiyCountdown |
| notice_bar | DiyNoticeBar |
| nav_group | DiyNavGroup |

（rich_text 和 video 的完整实现留到第三阶段）

---

## 第二阶段验收检查点

- [ ] 所有 15 个组件可从组件库选择添加到画布
- [ ] ProductPicker 弹窗可搜索/选择商品，选中的 productIds 写入 config
- [ ] CouponPicker 渲染正常（或占位提示）
- [ ] DynamicForm 支持 image-upload / datetime / product-picker / coupon-picker widget
- [ ] 图片上传到 MinIO 返回可访问 URL
- [ ] 发布后 Redis 缓存写入成功（验证：`GET /api/v1/diy/pages/{slug}` 响应头或日志确认命中缓存）
- [ ] Nuxt 端 `DiyGoodsList` 渲染实际商品数据（产品名/价格/图片）
- [ ] Nuxt 端 `DiyCoupon` / `DiyCountdown` / `DiyNoticeBar` / `DiyNavGroup` 正常渲染
- [ ] `POST /pages/{id}/unpublish` 撤销发布 → status=draft + 缓存清理
- [ ] 设为首页后 `GET /api/v1/diy/pages/default` 返回正确页面

---

# 第三阶段：完善与优化

---

## 项目上下文

前两阶段已完成：
- 15 个系统内置组件 + 完整 CRUD + 三栏编辑器 + DynamicForm 全部 widget
- 商品/营销组件 + Redis 缓存 + 图片上传
- Nuxt 端 13 个渲染组件 + 首页降级

---

## 任务目标

完善剩余组件（富文本编辑器、视频）、预览功能、site_profiles 共存机制、移动端适配、SEO、权限。

---

## Part A：后端完善

### A1. site_profiles 共存

在 `site_profiles` JSONB `config` 字段中新增支持 `diy_page_slug`：

- 修改 `api/admin/v1/site_profile.py` 的 update 接口：允许 config 中包含 `diy_page_slug` 字段
- 修改 `api/v1/site_profile.py` 的公开接口：响应中包含 `diy_page_slug`
- 无需改表结构，JSONB 天然支持新增字段

### A2. 预览接口增强

在 `GET /api/v1/diy/pages/{slug}` 中：

- `preview=true`：即使 status=draft 也返回（绕过 Redis，直查 DB + enrich）
- `preview=false/不传`：仅返回 status=published 的页面，优先 Redis
- 预览接口可选增加简单 token 校验（如 `?preview=true&token=xxx`），防止未授权访问 draft 页面

### A3. SEO 字段输出

在 `DiyPage` 的 API 响应中包含 `title` 和 `description` 字段，Nuxt 端使用 `useHead` 输出：

- `GET /api/v1/diy/pages/{slug}` 和 `/pages/default` 返回 `title` + `description`

### A4. 权限与 Casbin 策略

- 确保 `settings:manage` 权限覆盖所有 `/api/admin/v1/diy/*` 路由
- 在 Casbin 策略文件中添加对应的 policy 规则（如项目中已有 Casbin 初始化脚本）

---

## Part B：Admin 前端完善

### B1. 富文本编辑器

创建 `admin/src/views/diy/components/widgets/RichTextEditor.vue`：

- 基于 Tiptap（`@tiptap/vue-3` + `@tiptap/starter-kit`），如项目未安装则使用 `contenteditable` + `document.execCommand` 简易方案
- 在 `DynamicForm` 中映射 `ui:widget: "rich-editor"` → RichTextEditor
- `RichTextRenderer.vue`（画布预览）：渲染 HTML 内容（`v-html`）

### B2. Video 组件

- `VideoRenderer.vue`：显示视频 URL 或封面图占位
- Nuxt `DiyVideo.vue`：使用 HTML5 `<video>` 标签渲染

### B3. 预览功能

在 `editor.vue` 工具栏增加"预览"按钮：

- `window.open('/api/v1/diy/pages/{slug}?preview=true', '_blank')` 在新窗口打开 C 端页面
- 或创建 `views/diy/preview.vue`：iframe 嵌入 `/api/v1/diy/pages/{slug}?preview=true`，绕过后端缓存

### B4. 页面列表增强

在 `views/diy/index.vue` 列表中：

- 状态列：`NButton` 可切换发布/撤销发布
- 新增"设为首页"按钮，调用 `diyApi.setDefault(id)` 后刷新列表
- "预览"按钮打开新窗口

---

## Part C：Nuxt 前端完善

### C1. 移动端响应式

所有 `DiyXxx.vue` 组件增加响应式设计：

- 使用 Tailwind CSS 4 响应式断点：`sm:` / `md:` / `lg:`
- `DiyGoodsList`：grid 在移动端 `columns` 自动降为 1 或 2
- `DiyBanner`：移动端降低 height
- `DiyNavGroup`：移动端 columns 自动适配

### C2. SEO 优化

在 `pages/index.vue` 中（当渲染 DIY 首页时）：

```typescript
useHead({
  title: diyPage.value?.title || '首页',
  meta: [
    { name: 'description', content: diyPage.value?.description || '' }
  ]
});
```

### C3. DiyVideo + DiyRichText 完整实现

- `DiyVideo.vue`：接收 `config.url` + `config.poster` + `config.autoplay`，渲染 HTML5 `<video>` 标签
- `DiyRichText.vue`：接收 `config.content`（HTML），用 `v-html` 渲染，确保 XSS 安全（后端存储时已有清洗或前端用 DOMPurify）

### C4. 空状态与加载状态

`DiyPageRenderer.vue` 增加：
- loading：骨架屏或 NSkeleton
- empty：无组件时显示空状态提示
- error：接口失败时显示错误提示 + 重试按钮

---

## 第三阶段验收检查点

- [ ] RichTextEditor 可编辑富文本内容并保存/渲染
- [ ] Video 组件在编辑器和 C 端均可正常渲染
- [ ] 预览按钮打开新窗口，展示 draft 状态的页面（绕过 Redis）
- [ ] `site_profiles.config.diy_page_slug` 可配置，Nuxt 端据此选择渲染哪个 DIY 页面
- [ ] 移动端响应式：375px 宽度下所有组件布局正常
- [ ] SEO：DIY 首页的 `<title>` 和 `<meta description>` 正确输出
- [ ] 设为首页功能完整：列表中可设置，default API 返回正确的 is_default 页面
- [ ] 权限：非 settings:manage 角色无法访问 `/api/admin/v1/diy/*`
- [ ] 所有 15 个组件在编辑器中可拖拽、编辑、删除，在 C 端完整渲染
*（内容由AI生成，仅供参考）*
*（内容由AI生成，仅供参考）*
