# 站点配置编辑器 - iframe 预览与元素选择

> 状态：已实现（重构版）
> 关联分支：`feature/diy-preview-bridge`
> 重构日期：2026-08-12

---

## 1. 背景

原 "DIY 页面装修" 功能已重构为 "站点配置"。重构删除了页面模块、组件库、结构编辑模式，
仅保留：
- 站点配置列表（品牌/主题/导航/分类/页脚/SEO/i18n/功能开关/货币）
- iframe 实时预览（PC/平板/手机设备切换 + 浏览器中打开）
- 元素选择模式（iframe 内点击元素高亮选中 + 信息提取；选择后的操作功能待规划）

## 2. 架构

```
Admin (Vue3 + Vite, :8383)
├── views/site-config/
│   ├── index.vue               # 主页面：左站点配置列表 + 中 iframe 预览 + 右属性面板
│   └── modules/PropertyPanel.vue # 站点配置编辑表单 + 选中元素信息展示
├── store/modules/diy/index.ts  # 站点配置状态 + 元素选择状态
└── service/api/diy.ts          # 站点图片上传 API

C 端 (Nuxt3, :3000)
└── plugins/diy-preview.client.ts # iframe 内自动补 preview=true，豁免登录

后端 (FastAPI, :8000)
├── api/admin/v1/site_config.py  # 站点配置 CRUD + 图片上传
└── uploads/site-config/site_config.json  # 站点配置 JSON 持久化
```

## 3. 路由

| 端 | 路由 | 说明 |
|---|---|---|
| Admin | `/site/config` | 站点配置编辑页（左中右布局） |
| Admin API | `GET/PUT /api/admin/v1/site/config` | 站点配置读写 |
| Admin API | `POST /api/admin/v1/site/upload-image` | 站点图片上传 |
| C 端代理 | `/portal-preview/zh` → `http://localhost:3000/zh` | iframe 同源预览 |

## 4. iframe 预览机制

- iframe `src` 指向 `/portal-preview/zh`，由 Admin Vite 代理到 C 端 Nuxt
- sandbox 属性：`allow-scripts allow-same-origin allow-forms allow-modals allow-popups allow-popups-to-escape-sandbox`
  （移除了 `allow-top-navigation-by-user-activation`，防止 logo 点击跳出 iframe）
- C 端 `diy-preview.client.ts` 插件在 iframe 环境下自动为 SPA 导航补 `preview=true`，
  豁免 auth 中间件的登录检查

## 5. 元素选择模式

点击工具栏"选择元素"按钮开启：
1. 注入高亮样式（`.marvis-hover` 绿色虚线、`.marvis-selected` 红色实线）
2. 监听 iframe `mouseover`/`mouseout`/`click` 事件
3. 点击元素时提取信息（tag/id/class/text/rect/computedStyles）并同步到 store
4. 右侧 PropertyPanel 优先展示"选中元素"信息面板

**注意**：选择后的具体操作功能（如样式编辑、内容替换等）待后续规划。

## 6. 已删除的功能

以下功能在 2026-08-12 重构中删除：

### 前端
- `admin/src/views/diy/` 目录（旧装修主页面）
- `admin/src/views/diy-editor/` 目录（结构编辑器、组件库、DynamicForm、所有 Renderer）
- 页面 Tab 管理（首页固定 + 动态标签）
- 组件库面板与拖拽画布
- 结构编辑模式（canvas 模式）
- 元素样式编辑（applyStyles/resetStyles）
- 样式覆盖持久化（style overrides）

### 后端
- `backend/src/forge/api/admin/v1/diy.py`（页面/组件 CRUD）
- `backend/src/forge/api/admin/v1/style_overrides.py`（样式覆盖 CRUD）
- `backend/src/forge/api/v1/diy.py`（C 端 DIY 页面渲染）
- `backend/src/forge/application/services/diy_service.py`
- `backend/src/forge/application/dtos/diy_dtos.py`
- `backend/src/forge/infrastructure/persistence/repositories/diy_repo.py`
- `backend/src/forge/domain/diy/` 整个目录
- `backend/src/forge/infrastructure/persistence/models.py` 中的 ORMDiyPage/ORMDiyComponent/ORMDiyPageComponent
- 数据库迁移 `0010_drop_diy_tables.py` drop 了 diy_pages/diy_components/diy_page_components 表

### C 端
- `portal-web/app/plugins/diy-style-overrides.client.ts`（样式覆盖注入插件）
- `portal-web/app/pages/index.vue` 中的 DIY 页面渲染逻辑（回退到硬编码首页）
- `portal-web/app/pages/category/[slug].vue` 中的 DIY 页面渲染逻辑（回退到硬编码分类页）

## 7. 站点配置数据结构

```json
{
  "brand": { "name": "Forge", "tagline": "", "logo": { "type": "text", "data": "" } },
  "theme": {
    "primaryColor": "#18a058", "primaryLight": "#36ad6a", "primaryDark": "#0c7a43",
    "secondaryColor": "#f0a020", "accentColor": "#2080f0",
    "fontHeading": "Inter", "fontBody": "Inter"
  },
  "nav": [{ "label": "首页", "url": "/" }, ...],
  "categories": [{ "slug": "cat-food", "nameKey": "footer.petFood", "icon": "mdi:food" }, ...],
  "footer": { "copyright": "© 2026 Forge.", "newsletter": true },
  "seo": { "homeTitle": "", "metaDescription": "", "metaKeywords": "" },
  "i18n": { "defaultLocale": "en", "locales": ["en"] },
  "featureFlags": { "liveChat": true, "reviews": true, "wishlist": false },
  "currencies": ["USD"]
}
```

存储位置：`backend/src/uploads/site-config/site_config.json`
