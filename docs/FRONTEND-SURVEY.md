# Forge — 前端项目探测报告

> 探测日期：2026-06-24
> 目标：为管理后台前端开发提供技术栈、项目结构和代码风格基线

---

## 1. 技术栈清单

| 分类 | 技术 | 版本 | 说明 |
|------|------|------|------|
| 框架 | Nuxt 3 | ^3.14.0 | Vue 3 SSR/SSG 全栈框架，`srcDir: "app"` |
| 运行时 | Vue 3 | ^3.5.0 | Composition API + `<script setup>` |
| 路由 | vue-router | ^4.4.0 | Nuxt 基于 `pages/` 目录自动生成路由 |
| 状态管理 | Pinia | ^2.2.0 | 通过 `@pinia/nuxt` 模块集成，store 采用 setup 语法 |
| UI 框架 | Tailwind CSS | ^4.0.0 | Vite 插件方式引入，自定义 Design Tokens (oklch) |
| HTTP 客户端 | $fetch (ofetch) | Nuxt 内置 | 在 `composables/useApi.ts` 中封装 |
| 国际化 | @nuxtjs/i18n | ^9.0.0 | 4 语言 (en/ar/de/fr)，strategy: prefix_except_default |
| 图片优化 | @nuxt/image | ^1.8.1 | Nuxt 内置图片优化模块 |
| 工具库 | @vueuse/core | ^11.0.0 | Vue Composition 工具集 |
| Toast | sonner | ^1.5.0 | 轻量通知组件 |
| 构建工具 | Vite + Nitro | Nuxt 内置 | Vite 前端打包，Nitro 服务端 |
| 代码检查 | ESLint | ^9.10.0 | @nuxt/eslint-config 预设 |
| 语言 | TypeScript | ^5.6.0 | 严格类型检查 (`typeCheck: true`) |
| 包管理 | pnpm | — | workspace 模式 |

---

## 2. 项目目录结构

```
D:\codeRepo\forge\portal-web\
├── nuxt.config.ts              # Nuxt 配置（模块/运行时/CSS/代理）
├── i18n.config.ts              # 国际化配置
├── package.json                # 依赖声明
├── tsconfig.json               # TypeScript 配置
├── pnpm-lock.yaml              # 锁文件
├── pnpm-workspace.yaml         # workspace 定义
├── .npmrc                      # npm 镜像配置
│
├── app/                        # 源码根目录 (srcDir)
│   ├── app.vue                 # 根组件 (<NuxtLayout> → <NuxtPage>)
│   ├── assets/
│   │   └── css/
│   │       └── main.css        # Tailwind 入口 + 设计系统 (oklch tokens)
│   ├── components/
│   │   ├── AppHeader.vue       # 全局头部导航
│   │   ├── AppFooter.vue       # 全局底部
│   │   ├── CartDrawer.vue      # 购物车抽屉
│   │   ├── OrderStatusBadge.vue # 订单状态徽章
│   │   ├── PetChatWidget.vue   # AI 聊天悬浮组件
│   │   └── products/
│   │       ├── FilterSidebar.vue # 商品筛选侧边栏
│   │       └── ProductCard.vue   # 商品卡片
│   ├── composables/
│   │   ├── useApi.ts           # HTTP 请求封装 ($fetch)
│   │   ├── useAuth.ts          # 认证逻辑 (token cookie)
│   │   ├── useCurrency.ts      # 货币相关
│   │   └── useRegion.ts        # 区域切换
│   ├── layouts/
│   │   └── default.vue         # 默认布局（Header + Main + ChatWidget + Footer）
│   ├── pages/
│   │   ├── index.vue           # 首页（Hero/BestSellers/Categories/Testimonials）
│   │   ├── products.vue        # 商品列表（筛选+排序+分页）
│   │   ├── products/
│   │   │   └── [id].vue        # 商品详情
│   │   ├── orders.vue          # 订单列表
│   │   ├── orders/
│   │   │   └── [id].vue        # 订单详情
│   │   ├── pets.vue            # 宠物列表
│   │   ├── pets/
│   │   │   ├── new.vue         # 新建宠物
│   │   │   └── wizard.vue      # 宠物向导
│   │   ├── cart.vue            # 购物车页
│   │   ├── chat.vue            # 聊天页
│   │   └── checkout.vue        # 结算页
│   ├── stores/
│   │   ├── cart.ts             # 购物车 Store
│   │   ├── chat.ts             # 聊天 Store
│   │   ├── order.ts            # 订单 Store
│   │   ├── pet.ts              # 宠物 Store
│   │   └── product.ts          # 商品 Store
│   └── types/
│       └── tailwindcss.d.ts    # Tailwind 类型声明
│
├── locales/                    # i18n 翻译文件
│   ├── en.json
│   ├── ar.json
│   ├── de.json
│   └── fr.json
│
├── .nuxt/                      # Nuxt 自动生成（忽略）
└── node_modules/               # 依赖（忽略）
```

---

## 3. 代码风格总结

### 3.1 组件结构

所有组件统一采用 `<script setup lang="ts">` + `<template>` + `<style>` 单文件组件模式：

```vue
<template>
  <!-- template 直接使用，无冗余包裹 div -->
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useXxxStore } from '~/stores/xxx'

// Props 使用 TypeScript 泛型
const props = defineProps<{ product: any }>()

// Store 直接在 setup 顶层调用
const store = useXxxStore()

// 计算属性
const computedVal = computed(() => { ... })

// 方法
function doSomething() { ... }

// 生命周期
onMounted(() => { ... })
</script>
```

**关键约定：**
- Props 类型目前多用 `any`（后续管理后台应补全严格类型）
- Emits 使用 `defineEmits<{}>({})` 格式
- 组件通过 `~/stores/xxx` 路径别名导入
- 路由跳转使用 `<NuxtLink>` 和 `useRouter()`
- 无 scoped style 块（样式全部由 Tailwind CSS 负责）

### 3.2 Store 写法

使用 Pinia **Setup Store** 模式（推荐），非 Options API：

```typescript
import { defineStore } from "pinia";
import { useApi } from "~/composables/useApi";

interface Product { ... }
interface ProductFilters { ... }

export const useProductStore = defineStore("product", () => {
  // State: 用 ref() 定义
  const products = ref<Product[]>([]);
  const loading = ref(false);

  // Getters: 用 computed() 定义
  const totalPages = computed(() => ...);

  // 获取 API 方法
  const { fetchProducts } = useApi();

  // Actions: 普通 async 函数
  const loadProducts = async (filters?: ProductFilters) => {
    loading.value = true;
    try {
      const result = await fetchProducts(filters);
      products.value = result.items || [];
    } finally {
      loading.value = false;
    }
  };

  // 返回公开状态和方法
  return { products, loading, totalPages, loadProducts };
});
```

**关键约定：**
- 每个 store 文件只导出一个 `useXxxStore`
- State 使用 `ref()` / `reactive()`
- 接口定义写在 store 文件顶部
- API 通过 `useApi()` composable 注入
- try/finally 模式确保 loading 状态正确恢复

### 3.3 API 封装模式

`composables/useApi.ts` 是统一的 HTTP 适配层，特点：

```typescript
const API_BASE = "http://localhost:8000/api/v1";

export function useApi() {
  const fetchProducts = async (params?: Record<string, any>) => {
    const query = params ? "?" + new URLSearchParams(params).toString() : "";
    return $fetch(`${API_BASE}/products${query}`);
  };
  // ... 每个 API endpoint 一个方法
  return { fetchProducts, fetchProduct, ... };
}
```

**关键约定：**
- 使用 Nuxt 内置 `$fetch`（不支持拦截器，需手动处理）
- API_BASE 硬编码在 composable 内部（非 nuxt.config public runtimeConfig）
- 返回类型目前无泛型约束，上游调用时 `as any` 或 `as Promise<{...}>`
- 无统一错误处理（错误由调用方 try/catch）
- 无请求/响应拦截器、无 token 注入（token 由 `useAuth` composable 管理但未传入 useApi）

### 3.4 路由组织方式

Nuxt 文件系统路由，无需手动配置：

| 文件路径 | 对应路由 |
|---------|---------|
| `pages/index.vue` | `/` |
| `pages/products.vue` | `/products` |
| `pages/products/[id].vue` | `/products/:id` |
| `pages/orders.vue` | `/orders` |
| `pages/orders/[id].vue` | `/orders/:id` |
| `pages/cart.vue` | `/cart` |
| `pages/checkout.vue` | `/checkout` |
| `pages/chat.vue` | `/chat` |
| `pages/pets.vue` | `/pets` |
| `pages/pets/new.vue` | `/pets/new` |
| `pages/pets/wizard.vue` | `/pets/wizard` |

**布局应用：**
- `app.vue` 中通过 `<NuxtLayout>` 自动匹配 `layouts/` 目录
- 当前仅有 `layouts/default.vue`（Header + Main + ChatWidget + Footer）
- 页面可通过 `definePageMeta({ layout: 'xxx' })` 切换布局

### 3.5 样式体系

- **Tailwind CSS v4**：通过 Vite 插件 `@tailwindcss/vite` 引入
- **Design Tokens**：`main.css` 中 `@theme` 块定义完整 oklch 调色板
  - Primary: Sage Green (oklch 145° hue)
  - Secondary: Warm Amber (oklch 85°→75° hue)
  - Accent: Terracotta (oklch 25° hue)
  - Neutral: Warm Gray (oklch 145° hue, low chroma)
  - Semantic: success/warning/error/info
- **自定义工具类**：`.surface-elevated`、`.surface-subtle`、`.gradient-brand`、`.skeleton`
- **动画**：`fade-in`、`slide-up`、`scale-in`、`slide-in-right`

---

## 4. 管理后台实现方案

### 4.1 架构决策

根据需求文档 §8 规划，管理后台需要 9 个页面，建议以下架构：

| 维度 | 方案 | 理由 |
|------|------|------|
| **路由模块** | 独立 `pages/admin/` 目录 | Nuxt 文件路由天然隔离，路由前缀统一 `/admin` |
| **独立布局** | `layouts/admin.vue` | 管理后台需要侧边栏+顶栏，完全不同于前台 shop 布局 |
| **独立 Store** | `stores/admin/` 子目录 | 管理端状态（供应商/定价/探针记录）与前台无交集 |
| **API 扩展** | 新增 `composables/useAdminApi.ts` | 后台 API 端点独立 (`/api/v1/admin/...`)，需带认证 token |
| **路由守卫** | `middleware/auth.ts` | 通过 `definePageMeta({ middleware: 'auth' })` 保护后台页面 |
| **UI 风格** | 沿用 Tailwind + oklch tokens | 保持设计一致性，但管理后台可增加更紧凑的数据密集样式 |

### 4.2 文件清单

```
app/
├── layouts/
│   └── admin.vue                    # 管理后台布局（侧边栏+顶栏）
├── pages/
│   └── admin/
│       ├── index.vue                # /admin — Dashboard
│       ├── products.vue             # /admin/products — 商品列表
│       ├── products/
│       │   ├── new.vue              # /admin/products/new — 新建商品
│       │   └── [id].vue             # /admin/products/:id — 商品编辑
│       ├── orders.vue               # /admin/orders — 订单列表
│       ├── orders/
│       │   └── [id].vue             # /admin/orders/:id — 订单详情+操作
│       ├── suppliers.vue            # /admin/suppliers — 供应商管理
│       ├── pricing.vue              # /admin/pricing — 定价规则配置
│       ├── chat-requests.vue        # /admin/chat-requests — AI 探针记录
│       └── settings.vue             # /admin/settings — 系统设置
├── composables/
│   └── useAdminApi.ts               # 管理后台 API 封装
├── stores/
│   └── admin/
│       ├── dashboard.ts             # Dashboard 统计
│       ├── product.ts               # 商品管理（CRUD+上下架）
│       ├── order.ts                 # 订单管理（审核/采购/物流）
│       ├── supplier.ts              # 供应商管理
│       ├── pricing.ts               # 定价规则
│       └── settings.ts              # 系统设置
├── middleware/
│   └── auth.ts                      # 认证中间件（检查 token + 角色）
└── components/
    └── admin/
        ├── AdminSidebar.vue         # 管理端侧边栏导航
        ├── AdminHeader.vue          # 管理端顶栏
        ├── StatCard.vue             # Dashboard 统计卡片
        ├── DataTable.vue            # 通用数据表格
        └── StatusBadge.vue          # 状态标签（订单/商品状态）
```

### 4.3 实施注意事项

1. **useAdminApi 与 useApi 的关系**：新建独立 composable，base URL 指向 `/api/v1/admin`，并在请求头注入 token（从 `useAuth().token` 获取）。可抽取公共 `createApiClient(baseUrl)` 工厂函数消除重复。

2. **admin.vue 布局参考现有 default.vue**：复用 `<slot />` 模式，但去掉 PetChatWidget、AppFooter 等前台组件，换为 AdminSidebar + AdminHeader。

3. **路由守卫**：`middleware/auth.ts` 检查 `useAuth().token`，无 token 跳转到 `/login`；后续可扩展角色检查（admin/operator/support）。

4. **类型强化**：管理后台应避免 `any`，为 Product、Order、Supplier 等定义完整 TypeScript 接口（放入 `types/` 目录）。

5. **Dashboard 数据**：需求 §8.2 定义了 6 个指标卡片，需对应后端 `/api/v1/admin/dashboard` 或类似端点。

6. **订单详情操作栏**：需求 §5.4.2 要求根据订单状态动态显示不同操作按钮，需设计 `OrderActions` 组件根据状态机渲染。

7. **定价引擎 UI**：需求 §4 涉及公式配置、区域差异表、促销规则三条子功能，建议用 Tab 分隔或分段表单。

---

## 5. 探测后记（2026-06-24）

本探测报告已完成前端实现。管理后台前端（基础架构 + 7 个页面 + 6 个公共组件）已按探测报告中 §4 的方案完整落地，详见 `DEVELOPMENT-LOG.md`（管理后台前端章节）和 `ARCHITECTURE.md`（§11.2 管理后台架构）。
