---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 14f48488fead00d28e11c31f9845685c_67c47b286f2911f195af5254002afed2
    ReservedCode1: N2k11sjdiaLLGJCuiL1Che6PGzFnWf82jWeXR/L7PRWH1BA7sZkgtYcP0KaEXFMtSH6ey89aaE3+N8Dq48+SDFhZvki2+vukEgXks7AeM5nM5MHZVlPAkqkcYi3df+521xfx+0Ql0uAoGFrtfjKqik1bhoahn1hwoisAhVQx6TZno11I+d4fjOv80M0=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 14f48488fead00d28e11c31f9845685c_67c47b286f2911f195af5254002afed2
    ReservedCode2: N2k11sjdiaLLGJCuiL1Che6PGzFnWf82jWeXR/L7PRWH1BA7sZkgtYcP0KaEXFMtSH6ey89aaE3+N8Dq48+SDFhZvki2+vukEgXks7AeM5nM5MHZVlPAkqkcYi3df+521xfx+0Ql0uAoGFrtfjKqik1bhoahn1hwoisAhVQx6TZno11I+d4fjOv80M0=
---

﻿# API 接口参考文档

## 基础信息

- Base URL: `https://api.forge.com/api/v1`
- Format: JSON
- Auth: Bearer Token (JWT)
- Content-Type: application/json

---

## 1. 认证接口

### 1.1 用户注册
```
POST /auth/register
```

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "name": "John Doe",
  "locale": "en",
  "region": "US"
}
```

**Response 201**:
```json
{
  "user_id": "uuid-here",
  "access_token": "eyJhbG...",
  "refresh_token": "eyJhbG...",
  "expires_in": 86400
}
```

### 1.2 用户登录
```
POST /auth/login
```

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response 200**:
```json
{
  "access_token": "eyJhbG...",
  "refresh_token": "eyJhbG...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "name": "John Doe"
  }
}
```

### 1.3 Token 刷新
```
POST /auth/refresh
```

**Request Body**:
```json
{
  "refresh_token": "eyJhbG..."
}
```

### 1.4 登出
```
POST /auth/logout
Authorization: Bearer <token>
```

---

## 2. 宠物档案接口

### 2.1 创建宠物档案
```
POST /pets
Authorization: Bearer <token>
```

**Request Body**:
```json
{
  "name": "Buddy",
  "breed": "GOLDEN_RETRIEVER",
  "birthday": "2023-06-15",
  "weight": 30.5,
  "gender": "MALE",
  "spayed_neutered": true,
  "health_notes": ["Hip dysplasia prone"],
  "allergies": ["chicken"]
}
```

**Response 201**:
```json
{
  "id": "uuid",
  "owner_id": "uuid",
  "name": "Buddy",
  "breed": "GOLDEN_RETRIEVER",
  "birthday": "2023-06-15",
  "weight": 30.5,
  "gender": "MALE",
  "spayed_neutered": true,
  "health_notes": ["Hip dysplasia prone"],
  "allergies": ["chicken"],
  "lifecycle": "ADULT",
  "created_at": "2025-01-01T00:00:00Z"
}
```

### 2.2 获取宠物列表
```
GET /pets
Authorization: Bearer <token>
```

**Query Params**:
- `limit`: 20 (default)
- `offset`: 0 (default)

**Response 200**:
```json
{
  "items": [...],
  "total": 3,
  "limit": 20,
  "offset": 0
}
```

### 2.3 获取单个宠物
```
GET /pets/{pet_id}
Authorization: Bearer <token>
```

### 2.4 更新宠物
```
PUT /pets/{pet_id}
Authorization: Bearer <token>
```

### 2.5 删除宠物
```
DELETE /pets/{pet_id}
Authorization: Bearer <token>
```

### 2.6 获取推荐商品 (基于宠物)
```
GET /pets/{pet_id}/recommendations
Authorization: Bearer <token>
```

**Query Params**:
- `limit`: 10
- `algorithm`: pet_profile (default) | collaborative | seasonal

---

## 3. 商品接口

### 3.1 商品列表
```
GET /products
```

**Query Params**:
| 参数 | 类型 | 说明 |
|------|------|------|
| `category` | string | FOOD, TOYS, HEALTH... |
| `breed_group` | string | DOG, CAT, BIRD... |
| `life_stage` | string | PUPPY_KITTEN, ADULT, SENIOR |
| `min_price` | number | 最低价格 |
| `max_price` | number | 最高价格 |
| `min_rating` | number | 最低评分 |
| `suitable_for_allergy` | string | 适合该过敏原的商品 |
| `search` | string | 全文搜索 |
| `sort` | string | price_asc, price_desc, rating, newest |
| `limit` | int | 默认 20，最大 100 |
| `offset` | int | 默认 0 |

**Response 200**:
```json
{
  "items": [
    {
      "id": "uuid",
      "sku": "DOG-FOOD-001",
      "slug": "premium-dog-food",
      "name": "Premium Dog Food",
      "description": "High-protein formula...",
      "price": 29.99,
      "currency": "USD",
      "category": "FOOD",
      "breed_groups": ["DOG"],
      "suitable_for": {
        "life_stages": ["ADULT", "SENIOR"],
        "conditions": ["hip_health"]
      },
      "rating": 4.5,
      "review_count": 128,
      "images": ["https://..."],
      "inventory": 500,
      "is_ai_generated": true,
      "tags": ["grain-free", "high-protein"]
    }
  ],
  "total": 156,
  "limit": 20,
  "offset": 0
}
```

### 3.2 商品详情
```
GET /products/{slug}
```

**Response 200**:
```json
{
  "id": "uuid",
  "sku": "DOG-FOOD-001",
  "slug": "premium-dog-food",
  "name": "Premium Dog Food",
  "description": "High-protein formula...",
  "ai_description": "AI-generated detailed description...",
  "price": 29.99,
  "original_price": 39.99,
  "discount_percent": 25,
  "currency": "USD",
  "category": "FOOD",
  "breed_groups": ["DOG"],
  "suitable_for": {
    "life_stages": ["ADULT", "SENIOR"],
    "conditions": ["hip_health"],
    "allergen_free": ["chicken", "wheat"]
  },
  "rating": 4.5,
  "review_count": 128,
  "images": ["https://...", "https://..."],
  "inventory": 500,
  "is_in_stock": true,
  "tags": ["grain-free", "high-protein"],
  "seo": {
    "title": "Premium Dog Food - Grain Free",
    "description": "Best grain-free dog food for adult dogs...",
    "keywords": ["dog food", "grain-free", "premium"]
  },
  "region_availability": ["US", "CA", "DE", "FR"],
  "related_products": ["uuid-1", "uuid-2"],
  "created_at": "2025-01-01T00:00:00Z"
}
```

### 3.3 智能推荐
```
GET /products/recommendations?pet_id={pet_id}&limit=10
```

**Response 200**:
```json
{
  "items": [...],
  "recommendation_reason": "Based on your Golden Retriever Buddy (Adult)",
  "algorithm": "pet_profile"
}
```

### 3.4 创建商品
```
POST /products
Authorization: Bearer <token>
```

**Request Body** (ProductCreateDTO):
```json
{
  "name": {
    "ar": "طوق جلد فاخر للكلاب",
    "de": "Premium Leder Hundehalsband",
    "en": "Premium Leather Dog Collar",
    "fr": "Collier en cuir premium pour chien"
  },
  "description": {
    "ar": "طوق جلد طبيعي متين...",
    "de": "Langlebiges echtes Lederhalsband...",
    "en": "Durable genuine leather collar...",
    "fr": "Collier en cuir véritable durable..."
  },
  "category_id": "COLLARS_LEASHES",
  "pet_types": ["DOG"],
  "price": 12.50,
  "currency": "USD",
  "images": [
    "https://cdn.example.com/products/collar-01.jpg",
    "https://cdn.example.com/products/collar-02.jpg"
  ],
  "supplier_id": "sup_gulf_pet_01",
  "supplier_sku": "GLF-CLR-001",
  "specifications": {
    "material": "Genuine Leather",
    "sizes": ["S", "M", "L"],
    "colors": ["Brown", "Black"]
  },
  "status": "draft"
}
```

**字段说明**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|:---:|------|
| name | object | ✅ | 多语言标题 {ar, de, en, fr} |
| description | object | ✅ | 多语言描述 {ar, de, en, fr} |
| category_id | string | ✅ | 品类标识 |
| pet_types | string[] | ✅ | 适用宠物类型，如 ["DOG", "CAT"] |
| price | number | ✅ | 成本价 |
| currency | string | ❌ | 成本价币种，默认 USD |
| images | string[] | ❌ | 图片 URL 数组 |
| supplier_id | string | ✅ | 供应商 ID |
| supplier_sku | string | ✅ | 供应商侧 SKU |
| specifications | object | ❌ | 规格参数（尺寸、材质等） |
| status | string | ❌ | 默认 draft，可选 draft / active / inactive |

**Response 201**:
```json
{
  "id": "uuid",
  "sku": "DOG-COLLAR-001",
  "slug": "premium-leather-dog-collar",
  "name": {
    "ar": "طوق جلد فاخر للكلاب",
    "de": "Premium Leder Hundehalsband",
    "en": "Premium Leather Dog Collar",
    "fr": "Collier en cuir premium pour chien"
  },
  "description": {
    "ar": "طوق جلد طبيعي متين...",
    "de": "Langlebiges echtes Lederhalsband...",
    "en": "Durable genuine leather collar...",
    "fr": "Collier en cuir véritable durable..."
  },
  "category_id": "COLLARS_LEASHES",
  "pet_types": ["DOG"],
  "price": 12.50,
  "currency": "USD",
  "images": [
    "https://cdn.example.com/products/collar-01.jpg",
    "https://cdn.example.com/products/collar-02.jpg"
  ],
  "supplier_id": "sup_gulf_pet_01",
  "supplier_sku": "GLF-CLR-001",
  "specifications": {
    "material": "Genuine Leather",
    "sizes": ["S", "M", "L"],
    "colors": ["Brown", "Black"]
  },
  "status": "draft",
  "rating": 0,
  "review_count": 0,
  "created_at": "2025-06-24T10:30:00Z"
}
```

**Response 401**:
```json
{
  "detail": "Not authenticated"
}
```

---

### 3.5 更新商品
```
PATCH /products/{product_id}
Authorization: Bearer <token>
```

**Request Body** (ProductUpdateDTO — 所有字段可选):
```json
{
  "name": {
    "en": "Premium Leather Dog Collar - Updated"
  },
  "price": 14.00,
  "status": "active"
}
```

**字段说明**:

除 `product_id` 外，所有 3.4 中的字段均可选传，仅更新传入的字段。未传入的字段保持不变。

**Response 200**:
```json
{
  "id": "uuid",
  "sku": "DOG-COLLAR-001",
  "slug": "premium-leather-dog-collar",
  "name": {
    "ar": "طوق جلد فاخر للكلاب",
    "de": "Premium Leder Hundehalsband",
    "en": "Premium Leather Dog Collar - Updated",
    "fr": "Collier en cuir premium pour chien"
  },
  "description": {
    "ar": "طوق جلد طبيعي متين...",
    "de": "Langlebiges echtes Lederhalsband...",
    "en": "Durable genuine leather collar...",
    "fr": "Collier en cuir véritable durable..."
  },
  "category_id": "COLLARS_LEASHES",
  "pet_types": ["DOG"],
  "price": 14.00,
  "currency": "USD",
  "images": [
    "https://cdn.example.com/products/collar-01.jpg"
  ],
  "supplier_id": "sup_gulf_pet_01",
  "supplier_sku": "GLF-CLR-001",
  "specifications": {
    "material": "Genuine Leather",
    "sizes": ["S", "M", "L"],
    "colors": ["Brown", "Black"]
  },
  "status": "active",
  "rating": 4.2,
  "review_count": 35,
  "updated_at": "2025-06-24T11:00:00Z"
}
```

**Response 404**:
```json
{
  "detail": "Product not found"
}
```

---

## 4. 购物车接口

### 4.1 获取购物车
```
GET /cart
Authorization: Bearer <token>
```

**Response 200**:
```json
{
  "items": [
    {
      "product_id": "uuid",
      "name": "Premium Dog Food",
      "price": 29.99,
      "quantity": 2,
      "subtotal": 59.98,
      "image": "https://..."
    }
  ],
  "subtotal": 59.98,
  "tax": 4.80,
  "shipping": 0.00,
  "discount": 0.00,
  "total": 64.78,
  "currency": "USD"
}
```

### 4.2 添加商品到购物车
```
POST /cart/items
Authorization: Bearer <token>
```

**Request Body**:
```json
{
  "product_id": "uuid",
  "quantity": 1
}
```

### 4.3 更新购物车商品
```
PATCH /cart/items/{product_id}
Authorization: Bearer <token>
```

**Request Body**:
```json
{
  "quantity": 3
}
```

### 4.4 删除购物车商品
```
DELETE /cart/items/{product_id}
Authorization: Bearer <token>
```

### 4.5 清空购物车
```
DELETE /cart
Authorization: Bearer <token>
```

---

## 5. 订单接口

### 5.1 创建订单
```
POST /orders
Authorization: Bearer <token>
```

**Request Body**:
```json
{
  "shipping_address": {
    "name": "John Doe",
    "line1": "123 Main St",
    "line2": "Apt 4B",
    "city": "Los Angeles",
    "state": "CA",
    "postal_code": "90001",
    "country": "US",
    "phone": "+1234567890"
  },
  "coupon_code": "SAVE10",
  "payment_method": "stripe"
}
```

**Response 201**:
```json
{
  "order_number": "PET-20250115-0001",
  "status": "PENDING",
  "items": [...],
  "subtotal": 59.98,
  "tax": 4.80,
  "shipping": 0.00,
  "discount": 6.00,
  "total": 58.78,
  "currency": "USD",
  "payment_intent_id": "pi_xxxxx",
  "created_at": "2025-01-15T10:00:00Z"
}
```

### 5.2 获取订单列表
```
GET /orders
Authorization: Bearer <token>
```

**Query Params**:
- `status`: PENDING, PAID, SHIPPED, DELIVERED, CANCELLED
- `limit`: 20
- `offset`: 0

### 5.3 获取订单详情
```
GET /orders/{order_number}
Authorization: Bearer <token>
```

### 5.4 取消订单
```
POST /orders/{order_number}/cancel
Authorization: Bearer <token>
```

**Request Body**:
```json
{
  "reason": "Changed my mind"
}
```

### 5.5 订单追踪
```
GET /orders/{order_number}/tracking
Authorization: Bearer <token>
```

**Response 200**:
```json
{
  "tracking_number": "1Z999AA10123456784",
  "carrier": "UPS",
  "status": "IN_TRANSIT",
  "estimated_delivery": "2025-01-20",
  "events": [
    {
      "status": "SHIPPED",
      "location": "Los Angeles, CA",
      "timestamp": "2025-01-16T08:00:00Z",
      "description": "Package picked up by carrier"
    },
    {
      "status": "IN_TRANSIT",
      "location": "Phoenix, AZ",
      "timestamp": "2025-01-17T14:00:00Z",
      "description": "In transit"
    }
  ]
}
```

---

## 6. AI 聊天接口

### 6.1 发送消息 (SSE 流式)
```
POST /ai/chat/stream
Authorization: Bearer <token>
```

**Request Body**:
```json
{
  "message": "My dog has itchy skin, what should I use?",
  "conversation_id": "uuid",  // optional, for continuing chat
  "pet_id": "uuid"            // optional, for personalized response
}
```

**Response**: `text/event-stream`

```
event: message_start
data: {"conversation_id": "uuid", "timestamp": "2025-01-15T10:00:00Z"}

event: chunk
data: {"content": "I", "recommendations": []}

event: chunk
data: {"content": "'d recommend", "recommendations": []}

event: chunk
data: {"content": " a hypoallergenic shampoo", "recommendations": [{"product_id": "uuid", "name": "..."}]}

event: message_end
data: {"content": "Full response text...", "recommendations": [...], "tokens_used": 150}
```

### 6.2 获取对话历史
```
GET /ai/conversations
Authorization: Bearer <token>
```

### 6.3 获取单次对话
```
GET /ai/conversations/{conversation_id}
Authorization: Bearer <token>
```

### 6.4 删除对话
```
DELETE /ai/conversations/{conversation_id}
Authorization: Bearer <token>
```

---

## 7. 区域接口

### 7.1 获取区域列表
```
GET /regions
```

**Response 200**:
```json
{
  "items": [
    {
      "code": "US",
      "name": "United States",
      "currency": "USD",
      "languages": ["en"],
      "tax_rate": 0.08,
      "tax_name": "Sales Tax",
      "payment_methods": ["stripe", "paypal", "apple_pay"],
      "shipping_methods": ["usps", "ups", "fedex"],
      "is_active": true
    },
    {
      "code": "DE",
      "name": "Deutschland",
      "currency": "EUR",
      "languages": ["de", "en"],
      "tax_rate": 0.19,
      "tax_name": "VAT",
      "payment_methods": ["stripe", "paypal", "klarna"],
      "shipping_methods": ["dhl", "dpd"],
      "is_active": true
    }
  ]
}
```

### 7.2 获取当前区域
```
GET /regions/current
```

**Response 200**:
```json
{
  "code": "US",
  "currency": "USD",
  "locale": "en-US",
  "tax_rate": 0.08,
  "payment_methods": ["stripe", "paypal"],
  "shipping_methods": ["usps", "ups"]
}
```

### 7.3 切换区域
```
POST /regions/switch
Authorization: Bearer <token>
```

**Request Body**:
```json
{
  "region_code": "DE"
}
```

---

## 8. Webhook (Stripe → Backend)

### 8.1 Stripe Webhook
```
POST /webhooks/stripe
Content-Type: application/json
X-Signature: <stripe-signature>
```

**Handled Events**:
- `checkout.session.completed` → 支付成功，更新订单状态
- `invoice.paid` → 订阅付款成功
- `charge.refunded` → 退款

---

## 9. 错误响应格式

所有错误统一格式:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": [
      {
        "field": "email",
        "message": "Invalid email format"
      }
    ],
    "request_id": "req_xxxxx"
  }
}
```

### 错误码

| 错误码 | HTTP 状态 | 说明 |
|--------|----------|------|
| VALIDATION_ERROR | 400 | 参数校验失败 |
| UNAUTHORIZED | 401 | 未认证或 token 过期 |
| FORBIDDEN | 403 | 权限不足 |
| NOT_FOUND | 404 | 资源不存在 |
| DUPLICATE | 409 | 资源已存在 |
| RATE_LIMITED | 429 | 请求过于频繁 |
| PAYMENT_FAILED | 402 | 支付失败 |
| INTERNAL_ERROR | 500 | 服务器内部错误 |
| AI_SERVICE_UNAVAILABLE | 503 | AI 服务暂时不可用 |
*（内容由AI生成，仅供参考）*
