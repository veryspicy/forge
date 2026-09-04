# Forge 前端实现汇总

> 项目: 全球化宠物用品 AI 独立站  
> 技术栈: Nuxt 3 + Vue 3 + TypeScript + TailwindCSS + Pinia  
> 设计方向: Warm Organic Premium (oklch 色彩系统, DM Sans 字体)  
> 完成时间: 2026-06-23

---

## 设计系统与配置

| 文件 | 内容 |
|---|---|
| `assets/css/main.css` | oklch 品牌色彩系统 (sage green / warm amber / terracotta / 暖灰), Tailwind 主题扩展 |
| `nuxt.config.ts` | 四区域配置 (US/DE/FR/SA), i18n 模块, Pinia, 全局 CSS |
| `layouts/default.vue` | AppHeader + slot + AppFooter + CartDrawer + PetChatWidget |

## 核心组件 (6个)

| 组件 | 功能 |
|---|---|
| `AppHeader.vue` | 导航栏, 搜索, 语言/货币切换, 购物车徽标, 用户菜单 |
| `AppFooter.vue` | 4列布局 (品牌/链接/客服/订阅) |
| `CartDrawer.vue` | 右侧滑出购物车, 商品列表, 快速跳转 |
| `PetChatWidget.vue` | 右下角悬浮 AI 聊天, 最小化/展开/全屏 |
| `ProductCard.vue` | AI推荐角标, 评分, 库存状态, hover 动效 |
| `OrderStatusBadge.vue` | 7 种状态彩色标签 |

## Composables (5个)

| 文件 | 功能 |
|---|---|
| `useApi.ts` | 统一 API 请求封装, 20+ 端点 |
| `useRegion.ts` | 区域/货币/税率/支付方式/物流配置 |
| `useCurrency.ts` | Intl.NumberFormat 价格格式化 |
| `useAuth.ts` | 登录/注册/登出, token Cookie 持久化 |
| `useI18n.ts` | i18n 便捷封装 |

## Stores (5个)

| Store | 核心能力 |
|---|---|
| `cart` | 增删改, 优惠码, 税费/运费, 持久化 |
| `pet` | CRUD, 当前宠物, 推荐加载 |
| `chat` | 对话管理, streaming 状态 |
| `product` | 分页列表, 筛选, 排序, 推荐 |
| `order` | 列表, 详情, 取消, 物流追踪 |

## 页面 (10个)

| 路由 | 页面 | 核心功能 |
|---|---|---|
| `/` | 首页 | Hero + 分类 + 畅销 + AI推荐 + 评价 + 信任标识 |
| `/products` | 商品列表 | 分类/价格/排序/宠物类型筛选 + 分页 |
| `/products/[id]` | 商品详情 | 图片画廊/变体选择/规格表/相关推荐 |
| `/cart` | 购物车 | 数量调整/优惠码/费用明细/结算 |
| `/checkout` | 结算 | 3步表单 (地址 → 支付 → 确认) |
| `/pets` | 宠物列表 | 卡片网格/删除/空状态引导 |
| `/pets/wizard` | 宠物向导 | 3步创建 (基本信息 → 详情 → 目标) |
| `/orders` | 订单列表 | Tab 状态筛选/分页 |
| `/orders/[id]` | 订单详情 | 进度时间线/物流追踪/取消 |
| `/chat` | AI 聊天 | 双栏布局/对话管理/流式响应 |

## 国际化 (4语言)

`en-US`, `de-DE`, `fr-FR`, `ar-SA` — 覆盖 common/nav/home/cart/checkout/pets/orders/chat 各命名空间。

## 项目路径

`D:\codeRepo\forge\portal-web\app\`
`D:\codeRepo\forge\backend\src\forge\`

## 设计系统详情

- **Primary**: Sage Green (hue 145°, oklch)
- **Secondary**: Warm Amber (hue 85°, oklch)
- **Accent**: Terracotta (hue 25°, oklch)
- **Neutral**: 暖灰 (chroma 0.003-0.008)
- **字体**: DM Sans
- **动画**: fade-in / slide-up / scale-in / slide-in-right (ease-out-expo)
- **Radius**: 0.375-1rem
- **Shadow**: tinted (非纯黑)

## 区域配置

| 区域 | 货币 | 税率 | 支付方式 | 物流 |
|---|---|---|---|---|
| US | USD | 8% Sales Tax | Stripe, PayPal | USPS, UPS, FedEx |
| DE | EUR | 19% VAT | Stripe, PayPal, Klarna | DHL, DPD |
| FR | EUR | 20% VAT | Stripe, PayPal | Colissimo, Chronopost |
| SA | SAR | 15% VAT | Stripe | Aramex, DHL |
