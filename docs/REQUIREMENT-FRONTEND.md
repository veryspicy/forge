# 模块需求文档 — 前端 (Nuxt 3)

## 1. 模块概述

**技术栈**: Nuxt 3 + Vue 3 + TypeScript + TailwindCSS + Pinia + nuxt-i18n

**目标**: 构建全球化宠物用品 AI 独立站前端，支持多语言、多币种、RTL 布局。

---

## 2. 页面需求

### 2.1 首页 (index.vue)

**路由**: `/` 或 `/:locale/`

**功能模块**:
1. **Hero 区域**
   - 大标题: "Your Pet's Health, AI-Optimized"
   - 副标题: AI 驱动的个性化宠物用品推荐
   - CTA 按钮: "Get Started" → 引导宠物档案录入
   - 背景: 宠物温馨图片

2. **AI 推荐商品区**
   - 标题: "AI Picks for You"
   - 4 个商品卡片 (横向滚动)
   - 标注 "AI Recommended" 标签
   - 点击跳转到商品详情

3. **为什么选择 Forge**
   - 3 列图标 + 文字
   - 宠物档案: 创建你的宠物数字档案
   - AI 顾问: 7x24 养宠问题解答
   - 智能推荐: 基于品种/年龄/健康推荐

4. **季节性推荐横幅**
   - 根据当前季节推荐 (如: "Summer flea protection")
   - 跳转到商品列表 (自动筛选)

5. **用户评价**
   - 3-5 条评价展示 (Phase 2)

**数据流**:
- 调用 `GET /api/v1/products/recommendations` 获取推荐商品
- 调用 `GET /api/v1/regions/current` 获取区域配置

### 2.2 商品列表页 (products/index.vue)

**路由**: `/products` 或 `/:locale/products`

**功能模块**:
1. **顶部筛选栏**
   - 品类筛选 (下拉/多选)
   - 宠物群体 (DOG/CAT/BIRD...)
   - 年龄阶段 (PUPPY_KITTEN/ADULT/SENIOR)
   - 价格区间 (slider)
   - 评分 (stars)
   - 适用过敏原 (checkbox)

2. **排序**
   - 价格升序/降序
   - 评分高低
   - 最新上架

3. **商品网格**
   - 响应式: 桌面 4 列，平板 2 列，手机 1 列
   - 每个商品卡片: 图片、名称、价格、评分、加入购物车按钮
   - AI 推荐商品带 "AI Pick" 角标
   - 缺货状态: 显示 "Out of Stock"

4. **分页**
   - 底部分页器或无限滚动
   - 每页 20 条

**数据流**:
- `GET /api/v1/products?category=food&breed_group=dog&min_price=10&sort=price_asc`
- 搜索: `?search=grain+free`

### 2.3 商品详情页 (products/[slug].vue)

**路由**: `/products/:slug`

**功能模块**:
1. **商品图片**
   - 主图 + 缩略图列表
   - 支持 zoom hover
   - 最多 5 张图片

2. **商品信息**
   - 名称 (H1)
   - SKU (灰色小字)
   - 价格 + 原价 + 折扣标签
   - 评分 (stars + 数量)
   - 库存状态 (In Stock / Low Stock / Out of Stock)

3. **AI 推荐标签**
   - 如果商品基于宠物档案推荐，显示:
   - "Recommended for [Breed] [LifeStage]"

4. **商品描述**
   - AI 生成的详细描述
   - 特性列表 (bullets)
   - 成分/规格

5. **加入购物车**
   - 数量选择器 (+ / -)
   - 加入购物车按钮
   - 立即购买按钮

6. **AI 推荐区**
   - 标题: "Customers who bought this also liked"
   - 4 个关联商品卡片

7. **适用信息**
   - 适合品种/年龄段
   - 过敏原信息 (Free from: chicken, wheat...)

**数据流**:
- `GET /api/v1/products/{slug}`
- `GET /api/v1/products/recommendations?based_on={product_id}&limit=4`

### 2.4 购物车页 (cart.vue)

**路由**: `/cart`

**功能模块**:
1. **购物车商品列表**
   - 商品图片 + 名称 + SKU
   - 单价
   - 数量选择器 (+ / -)
   - 小计 (单价 × 数量)
   - 删除按钮 (🗑️)

2. **优惠码**
   - 输入框 + Apply 按钮
   - 验证优惠码 (GET /api/v1/coupons/{code})
   - 显示折扣金额

3. **订单摘要**
   - 小计 (subtotal)
   - 税费 (tax, 区域感知)
   - 运费 (shipping, 基于地址计算)
   - 折扣 (discount)
   - 总计 (total)
   - 币种自动切换

4. **结算按钮**
   - "Proceed to Checkout" → /checkout

5. **继续购物**
   - 链接到商品列表

### 2.5 结算页 (checkout.vue)

**路由**: `/checkout`

**功能模块**:
1. **收货地址表单**
   - 收件人姓名
   - 地址行 1/2
   - 城市
   - 州/省
   - 邮编 (美国格式验证)
   - 国家 (下拉选择)
   - 电话
   - 地址自动补全 (US Zip Code API)

2. **配送方式**
   - 标准配送 (3-5 天, $5.99)
   - 快速配送 (1-2 天, $12.99)
   - 基于区域显示不同物流商

3. **支付方式**
   - Stripe Elements (信用卡/Apple Pay/Google Pay)
   - PayPal 按钮
   - 基于区域显示不同支付方式

4. **订单确认**
   - 商品列表 + 小计
   - 税费 + 运费
   - 总计
   - "Place Order" 按钮 → POST /api/v1/orders

5. **隐私协议**
   - 勾选 "I agree to the Terms & Privacy Policy"

### 2.6 宠物档案页 (pet/profile.vue)

**路由**: `/pet/profile`

**功能模块**:
1. **宠物卡片列表**
   - 每只宠物一张卡片:
     - 宠物头像 (上传/默认)
     - 名字 (可编辑)
     - 品种 + 生命周期阶段
     - 体重 + 健康状态指示器
   - "Add New Pet" 按钮

2. **快捷操作**
   - 每只宠物卡片上:
     - "View Recommendations" → 查看推荐商品
     - "Edit Profile" → 跳转到 wizard
     - "Delete" → 确认删除

3. **AI 推荐概览**
   - 当前选中宠物的 Top 3 推荐商品

**数据流**:
- `GET /api/v1/pets` → 渲染列表
- 选中宠物后 `GET /api/v1/pets/{id}/recommendations`

### 2.7 宠物档案录入向导 (pet/wizard.vue)

**路由**: `/pet/wizard`

**功能模块**:
1. **步骤指示器**
   - Step 1: Basic Info (名字, 品种, 生日)
   - Step 2: Health (体重, 性别, 绝育状态)
   - Step 3: Allergies (过敏原, 健康问题)
   - Step 4: Summary (确认并提交)

2. **品种选择**
   - 先选宠物群体 (DOG/CAT/BIRD...)
   - 再选具体品种 (基于群体筛选)
   - 搜索框支持模糊搜索

3. **智能建议**
   - 选择品种后显示该品种的平均体重范围
   - 选择生日后自动计算生命周期阶段

4. **表单验证**
   - 必填字段标红
   - 生日格式验证
   - 体重在合理范围内

5. **提交**
   - POST /api/v1/pets
   - 成功后跳转到 /pet/profile

### 2.8 订单列表页 (orders/index.vue)

**路由**: `/orders`

**功能模块**:
1. **订单列表**
   - 每个订单: 订单编号、日期、状态、总金额
   - 状态标签颜色:
     - PENDING: 黄色
     - PAID: 蓝色
     - SHIPPED: 紫色
     - DELIVERED: 绿色
     - CANCELLED: 红色

2. **订单筛选**
   - 按状态筛选
   - 按日期范围

3. **订单操作**
   - "View Details" → /orders/[id]
   - "Track" → 查看物流追踪
   - "Cancel" → 取消订单 (PENDING 状态)

### 2.9 订单详情页 (orders/[id].vue)

**路由**: `/orders/:orderNumber`

**功能模块**:
1. **订单信息**
   - 订单编号、日期、状态
   - 商品列表 (名称、单价、数量、小计)
   - 费用明细

2. **物流追踪**
   - 运单号 + 物流商
   - 时间线展示 (已发货 → 运输中 → 已签收)

3. **操作**
   - 下载发票
   - 申请退货 (Phase 2)
   - 再次购买 (添加到购物车)

### 2.10 AI 聊天 (全局组件)

**PetChatWidget** — 右下角悬浮聊天按钮

**功能模块**:
1. **悬浮按钮**
   - 右下角固定
   - 带消息数量角标
   - 点击展开/收起聊天面板

2. **聊天面板**
   - 标题: "AI Pet Assistant"
   - 消息区域 (用户消息右对齐，AI 左对齐)
   - 输入框 + 发送按钮
   - 流式输出 (打字机效果)
   - 推荐商品内嵌 (聊天消息中的商品卡片)

3. **上下文感知**
   - 自动携带当前宠物档案信息
   - 显示: "Chatting about [Pet Name] ([Breed])"

**WebSocket 连接**:
- `wss://api.forge.com/ws/chat`
- 消息格式:
  ```json
  { "type": "message", "content": "Question?" }
  { "type": "chunk", "content": "Partial response..." }
  { "type": "recommendations", "items": [...] }
  { "type": "end" }
  ```

---

## 3. 状态管理 (Pinia)

### 3.1 cart.ts

```typescript
export interface CartItem {
  product_id: string;
  name: string;
  price: number;
  quantity: number;
  image: string;
}

export const useCartStore = defineStore('cart', {
  state: () => ({
    items: [] as CartItem[],
    currency: 'USD',
    coupon_code: null as string | null,
  }),
  getters: {
    subtotal: (state) => ...,
    total: (state) => ...,
    item_count: (state) => ...,
  },
  actions: {
    async addItem(product_id: string, quantity: number) { ... },
    async removeItem(product_id: string) { ... },
    async updateQuantity(product_id: string, quantity: number) { ... },
    async clear() { ... },
    async applyCoupon(code: string) { ... },
    async syncWithServer() { ... },
  },
  persist: true,  // localStorage
});
```

### 3.2 pet.ts

```typescript
export interface PetProfile {
  id: string;
  name: string;
  breed: string;
  birthday: string;
  weight: number;
  gender: string;
  lifecycle: string;
  allergies: string[];
  health_notes: string[];
}

export const usePetStore = defineStore('pet', {
  state: () => ({
    pets: [] as PetProfile[],
    current_pet_id: null as string | null,
  }),
  getters: {
    current_pet: (state) => ...,
  },
  actions: {
    async fetchPets() { ... },
    async addPet(data: Partial<PetProfile>) { ... },
    async setCurrentPet(pet_id: string) { ... },
  },
  persist: true,
});
```

### 3.3 ai.ts

```typescript
export const useAiStore = defineStore('ai', {
  state: () => ({
    conversations: [] as Conversation[],
    current_conversation: null as string | null,
    is_streaming: false,
  }),
  actions: {
    async sendMessage(message: string) { ... },
    async fetchConversations() { ... },
    async connectWebSocket() { ... },
  },
});
```

---

## 4. Composables

### 4.1 useRegion.ts

```typescript
export function useRegion() {
  const config = useRuntimeConfig();
  const region = ref(config.public.region);
  const currency = ref(config.public.defaultCurrency);
  
  const regionConfig = computed(() => {
    // 根据区域返回配置
  });
  
  const setRegion = (code: string) => {
    // 切换区域，更新货币和语言
  };
  
  return { region, currency, regionConfig, setRegion };
}
```

### 4.2 useCurrency.ts

```typescript
export function useCurrency() {
  const formatPrice = (amount: number, currency: string = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
    }).format(amount);
  };
  
  const convertPrice = async (amount: number, from: string, to: string) => {
    // 调用汇率 API 或使用缓存
  };
  
  return { formatPrice, convertPrice };
}
```

### 4.3 useAuth.ts

```typescript
export function useAuth() {
  const user = ref(null);
  const token = useState<string>('access_token');
  
  const login = async (email: string, password: string) => { ... };
  const register = async (data: RegisterData) => { ... };
  const logout = async () => { ... };
  const isAuthenticated = computed(() => !!token.value);
  const isAdmin = computed(() => user.value?.role === 'admin');
  
  return { user, login, register, logout, isAuthenticated, isAdmin };
}
```

---

## 5. 国际化文件

### 5.1 locales/en.json (完整结构)
- navigation, common, hero, products, pet, chat, footer, checkout, orders, auth

### 5.2 locales/ar.json (RTL)
- 同上，阿拉伯语翻译

### 5.3 locales/de.json
- 同上，德语翻译

---

## 6. 组件库

### 6.1 UI 组件
- Button (primary/secondary/ghost/danger)
- Input / Textarea
- Select / MultiSelect
- Card
- Badge / Tag
- Modal / Drawer
- Toast / Notification
- Skeleton (加载骨架屏)
- Pagination

### 6.2 业务组件
- Header (导航栏 + 语言切换 + 购物车 + 用户)
- Footer (4 列 + 版权)
- ProductCard
- ProductGrid
- Filters
- CartBadge + CartDrawer
- PetChatWidget
- PetProfileForm
- OrderStatusBadge
- TrackingTimeline
- CurrencySwitcher
- LocaleSwitcher

---

## 7. 构建配置

### 7.1 Dockerfile (前端)
```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/.output ./
EXPOSE 3000
CMD ["node", "server/index.mjs"]
```

### 7.2 环境变量
```
NUXT_PUBLIC_API_BASE=https://api.forge.com/api/v1
NUXT_PUBLIC_AI_CHAT_BASE=wss://api.forge.com/ws
NUXT_PUBLIC_REGION=na
NUXT_PUBLIC_DEFAULT_CURRENCY=USD
NUXT_PUBLIC_STRIPE_KEY=pk_live_...
```
