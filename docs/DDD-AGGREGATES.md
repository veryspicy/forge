---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 14f48488fead00d28e11c31f9845685c_0f9399446fcb11f1986d525400d9a7a1
    ReservedCode1: wg1wsG1IULma47qXPBbIattfjfhGHQUL0927EHhgSnzf01y4vR7GtesuaXz1Z57iuNTRQjQmSgjiiOBq/KNIIx4NUns57mRcvTQUVeFPR205tccvS5HAP6+zFaLI1HjYSmFXny8WJEIJqUnyoY8lcUILtijrTlKPqPTXMtdijOdJfn7oTobB4IsR8EQ=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 14f48488fead00d28e11c31f9845685c_0f9399446fcb11f1986d525400d9a7a1
    ReservedCode2: wg1wsG1IULma47qXPBbIattfjfhGHQUL0927EHhgSnzf01y4vR7GtesuaXz1Z57iuNTRQjQmSgjiiOBq/KNIIx4NUns57mRcvTQUVeFPR205tccvS5HAP6+zFaLI1HjYSmFXny8WJEIJqUnyoY8lcUILtijrTlKPqPTXMtdijOdJfn7oTobB4IsR8EQ=
---

﻿# DDD 聚合设计文档

## 1. 聚合根 (Aggregate Roots)

### 1.1 PetProfile 聚合

**职责**: 管理用户的宠物档案数据，包括品种、健康记录、生命周期阶段。

**聚合根**: `PetProfile`

**实体**:
- `PetProfile`: 聚合根，包含所有宠物信息
- `HealthRecord`: 健康记录（疫苗、疾病、用药）
- `Allergy`: 过敏原

**值对象**:
- `BreedInfo`: 品种信息（品种名、体型、平均寿命）
- `WeightRange`: 体重范围（min, max, unit）
- `LifeStage`: 生命周期阶段（PUPPY_KITTEN / ADULT / SENIOR）

**领域服务**:
- `PetProfileService`: CRUD 操作
- `LifecycleCalculator`: 根据生日自动计算生命周期阶段

**仓储接口**:
```python
class PetProfileRepository(Protocol):
    async def create(profile: PetProfile) -> PetProfile: ...
    async def get_by_id(id: UUID) -> PetProfile | None: ...
    async def get_by_owner(owner_id: UUID) -> list[PetProfile]: ...
    async def update(profile: PetProfile) -> PetProfile: ...
    async def delete(id: UUID) -> bool: ...
```

**不变量**:
1. 一只宠物必须有品种和名字
2. 体重必须在品种合理范围内
3. 生命周期阶段由生日自动计算，不可手动修改
4. 过敏原不能为空列表

**领域事件**:
- `PetProfileCreated(pet_id, owner_id, breed)`
- `PetProfileUpdated(pet_id, changes: list[str])`
- `LifeStageChanged(pet_id, from: LifeStage, to: LifeStage)`
- `HealthRecordAdded(pet_id, record_type, notes)`

---

### 1.2 Product 聚合

**职责**: 管理商品信息、定价、品类、适用宠物范围。

**聚合根**: `Product`

**实体**:
- `Product`: 聚合根
- `ProductImage`: 商品图片
- `Review`: 用户评价（Phase 2）

**值对象**:
- `Money`: 金额（value, currency）
- `ProductCategory`: 品类（FOOD / TOYS / HEALTH / ACCESSORIES / GROOMING / LITTER）
- `BreedGroup`: 宠物群体（DOG / CAT / BIRD / SMALL_ANIMAL / REPTILE / FISH）
- `PriceRange`: 价格范围（min, max）
- `SEOData`: SEO 元数据（title, description, keywords）

**领域服务**:
- `PricingService`: 定价计算（成本 + 利润率 = 售价）
- `TaxCalculationService`: 税费计算（区域感知）
- `ProductSearchService`: 商品搜索

**仓储接口**:
```python
class ProductRepository(Protocol):
    async def create(product: Product) -> Product: ...
    async def get_by_id(id: UUID) -> Product | None: ...
    async def get_by_slug(slug: str) -> Product | None: ...
    async def list(filters: ProductFilters) -> tuple[list[Product], int]: ...
    async def search(query: str, limit: int) -> list[Product]: ...
    async def update(product: Product) -> Product: ...
    async def delete(id: UUID) -> bool: ...
    async def get_by_category(category: ProductCategory) -> list[Product]: ...
    async def get_suitable_for_pet(pet_id: UUID) -> list[Product]: ...
```

**不变量**:
1. 售价必须大于成本价
2. 利润率必须在允许范围内 (10%-500%)
3. 每个 SKU 唯一
4. slug 由 name 自动生成，唯一
5. 商品必须至少属于一个品类

**领域事件**:
- `ProductCreated(product_id, sku, category)`
- `ProductPriceChanged(product_id, old_price, new_price)`
- `ProductInventoryChanged(product_id, old_qty, new_qty)`
- `ProductSEOUpdated(product_id, seo_data)`

---

### 1.3 Order 聚合

**职责**: 管理订单生命周期，从创建到交付/退款的全流程。

**聚合根**: `Order`

**实体**:
- `Order`: 聚合根
- `OrderItem`: 订单项
- `ShippingAddress`: 收货地址

**值对象**:
- `Money`: 金额（value, currency）
- `OrderNumber`: 订单编号（格式: PET-YYYYMMDD-NNNN）
- `OrderStatus`: 订单状态机
- `Coupon`: 优惠码

**状态机**:
```
PENDING → CONFIRMED → PAID → PROCESSING → SHIPPED → DELIVERED
   │                                                     │
   └────────────── CANCELLED ←───────────────────────────┘
                                        │
                                   RETURNED
```

**合法转换**:
- PENDING → CONFIRMED (用户确认)
- CONFIRMED → PAID (支付成功)
- PAID → PROCESSING (仓库处理)
- PROCESSING → SHIPPED (发货)
- SHIPPED → DELIVERED (签收)
- 任意状态 → CANCELLED (取消)
- DELIVERED → RETURNED (退货)

**领域服务**:
- `OrderProcessingService`: 订单处理流程
- `CouponValidator`: 优惠码验证
- `ShippingCalculator`: 运费计算

**仓储接口**:
```python
class OrderRepository(Protocol):
    async def create(order: Order) -> Order: ...
    async def get_by_id(id: UUID) -> Order | None: ...
    async def get_by_number(number: str) -> Order | None: ...
    async def get_by_user(user_id: UUID, limit: int, offset: int) -> list[Order]: ...
    async def update(order: Order) -> Order: ...
    async def transition_status(order: Order, new_status: OrderStatus) -> Order: ...
    async def get_pending_orders(before: datetime) -> list[Order]: ...  # 超时未支付
```

**不变量**:
1. 订单总金额 = Σ(商品单价 × 数量) + 运费 - 优惠 - 税费
2. 状态转换必须符合状态机规则
3. 已发货订单不能取消
4. 订单编号全局唯一
5. 支付成功后才能进入 PROCESSING 状态

**领域事件**:
- `OrderCreated(order_id, order_number, user_id, total)`
- `OrderPaid(order_id, payment_intent_id, amount)`
- `OrderShipped(order_id, tracking_number, carrier)`
- `OrderDelivered(order_id)`
- `OrderCancelled(order_id, reason)`
- `OrderRefunded(order_id, amount)`

**RocketMQ 消息映射**:
```
OrderCreated → TOPIC_ORDER:TAG_CREATE (事务消息)
OrderPaid    → TOPIC_ORDER:TAG_PAY
OrderShipped → TOPIC_ORDER:TAG_SHIP
OrderCancelled → TOPIC_ORDER:TAG_CANCEL
```

---

### 1.4 Region 聚合

**职责**: 管理区域配置，包括货币、语言、税率、支付方式、物流方式。

**聚合根**: `Region`

**值对象**:
- `RegionCode`: 区域代码 (US, DE, FR, ES, SA, AE...)
- `Currency`: 货币信息 (code, symbol, decimal_places)
- `TaxConfig`: 税务配置 (rate, name, included_in_price)
- `PaymentMethod`: 支付方式 (stripe, paypal, klarna, mada...)
- `ShippingMethod`: 物流方式 (usps, ups, dhl, aramex...)
- `LanguageConfig`: 语言配置 (locale, direction, i18n_bundle)

**领域服务**:
- `RegionConfigurationService`: 区域配置管理
- `CurrencyConverter`: 汇率转换
- `TaxCalculator`: 税费计算

**仓储接口**:
```python
class RegionRepository(Protocol):
    async def get_by_code(code: str) -> Region | None: ...
    async def list_active() -> list[Region]: ...
    async def update_config(code: str, config: dict) -> Region: ...
```

**不变量**:
1. 每个区域代码唯一
2. 税率必须在 0%-30% 之间
3. 区域必须至少有一种支付方式

---

### 1.5 Supplier 聚合（Phase 1 新增）

**职责**: 管理供应商档案、API 接入配置、SKU 映射关系。

**聚合根**: `Supplier`

**实体**:
- `Supplier`: 聚合根，包含供应商核心信息
- `SupplierRegion`: 供应商发货地区

**值对象**:
- `ApiConfig`: API 接入配置（base_url, auth_type, credentials）
- `SupplierStatus`: 供应商状态（ACTIVE / SUSPENDED / TERMINATED）

**领域服务**:
- `SupplierService`: 供应商 CRUD + 软删除

**仓储接口**:
```python
class SupplierRepository(Protocol):
    async def create(supplier: Supplier) -> Supplier: ...
    async def get_by_id(id: UUID) -> Supplier | None: ...
    async def list_active() -> list[Supplier]: ...
    async def list_by_region(region: str) -> list[Supplier]: ...
    async def update(supplier: Supplier) -> Supplier: ...
    async def deactivate(id: UUID) -> Supplier: ...
```

**不变量**:
1. 供应商名称全局唯一
2. API 接入时 base_url 和 auth_type 必填
3. 至少关联一个发货地区
4. 软删除：deactivate 仅设 `is_active=False`，不物理删除（保留历史订单关联）

**工厂方法**: `create_supplier(name, contact_info, regions)` — 初始化时 `is_active=True`。

---

### 1.6 Order 聚合扩展（Phase 3 新增）

**变更范围**: 在现有 Order 状态机（1.3节）基础上扩展管理后台审核与采购状态。

**新增状态**:

```
PAID → PENDING_REVIEW → PROCURING → SHIPPED  (走审核-采购流程)
                │              │
                ▼              ▼
            CANCELLED     PROCURE_FAILED
```

**新增状态转换**:

| 转换 | 触发 | 前置条件 |
|---|---|---|
| PAID → PENDING_REVIEW | `submit_for_review()` | 当前状态为 PAID |
| PENDING_REVIEW → PROCURING | `approve()` | 当前状态为 PENDING_REVIEW |
| PENDING_REVIEW → CANCELLED | `reject(reason)` | 当前状态为 PENDING_REVIEW，记录驳回原因 |
| PROCURING → SHIPPED | 采购完成发货 | 当前状态为 PROCURING |
| PROCURING → PROCURE_FAILED | `mark_procure_failed(reason)` | 当前状态为 PROCURING |

**新增业务方法**:

```python
class Order:
    def submit_for_review(self) -> None: ...
    def approve(self) -> None: ...
    def reject(self, reason: str) -> None: ...
    def start_procurement(self) -> None: ...
    def mark_procure_failed(self, reason: str) -> None: ...
```

**新增不变量**:
1. 只有 PAID 状态的订单才能提交审核
2. 已发货（SHIPPED）订单不能再审核/驳回
3. 审核驳回必须提供原因
4. 采购失败必须记录原因

---

### 1.7 Shipment 聚合（Phase 3 新增）

**职责**: 管理物流追踪全生命周期，独立于 Order 聚合（订单与物流解耦）。

**聚合根**: `Shipment`

**实体**:
- `Shipment`: 聚合根
- `ShipmentEvent`: 物流事件（扫描时间、地点、状态描述）

**值对象**:
- `TrackingNumber`: 物流单号
- `Carrier`: 物流商（DHL / USPS / FedEx / Aramex 等）
- `ShipmentStatus`: 物流状态

**状态机**:

```
PENDING → PICKED_UP → IN_TRANSIT → OUT_FOR_DELIVERY → DELIVERED
                                                          │
                                                       FAILED
```

**领域服务**:
- `ShipmentService`: 创建物流单、更新追踪、查询事件

**仓储接口**:
```python
class ShipmentRepository(Protocol):
    async def create(shipment: Shipment) -> Shipment: ...
    async def get_by_id(id: UUID) -> Shipment | None: ...
    async def get_by_order(order_id: UUID) -> list[Shipment]: ...
    async def update(shipment: Shipment) -> Shipment: ...
    async def get_by_tracking(tracking_number: str) -> Shipment | None: ...
```

**不变量**:
1. tracking_number 全局唯一
2. 状态转换必须符合状态机规则
3. DELIVERED 后 tracking_number 不可修改（冻结）
4. 每个物流事件必须有时间戳和描述
5. 必须先有 PICKED_UP 才能进入运输状态

---

### 1.8 PricingRule + Promotion 聚合（Phase 4 新增）

**职责**: 管理定价规则（区域差异化定价公式）和促销活动（满减/优惠券/会员价），提供统一的最终价格计算引擎。

**聚合根**: `PricingRule`、`Promotion`

**PricingRule 实体**:
- `PricingRule`: 定价规则（区域倍率 + 固定运费）
- 支持按优先级排序，高优先级规则先匹配

**PricingRule 值对象**:
- `Money`: 金额（value, currency）
- `RegionCode`: 目标区域代码

**Promotion 实体**:
- `Promotion`: 促销活动
- `PromotionType`: THRESHOLD_DISCOUNT / COUPON / MEMBER_PRICE

**Promotion 值对象**:
- `TimeRange`: 活动有效时间（start_time, end_time）
- `DiscountValue`: 折扣值（满减金额 / 优惠券面额 / 折扣百分比）

**领域服务 — PricingEngine**:

```python
class PricingEngine:
    def calculate_final_price(
        self,
        product: Product,
        region: RegionCode,
        manual_override: Money | None = None,
    ) -> Money:
        """四级优先级计算最终售价"""
        # 1. 手动覆盖 (最高优先级)
        if manual_override:
            return manual_override
        # 2. 促销活动
        promo_price = self._apply_promotions(product, region)
        if promo_price:
            return promo_price
        # 3. 区域定价规则
        region_rule = self._match_region_rule(region)
        if region_rule:
            return region_rule.apply(product.cost_price)
        # 4. 全局默认规则
        return self._global_rule.apply(product.cost_price)
```

**四级优先级**: 手动覆盖 > 促销 > 区域定价 > 全局默认

**促销叠加控制**:
- `stackable=True`: 可与同类促销叠加
- `stackable=False`: 不可叠加，取最优价
- 叠加顺序：会员价 → 满减 → 优惠券

**仓储接口**:
```python
class PricingRuleRepository(Protocol):
    async def create(rule: PricingRule) -> PricingRule: ...
    async def list_active() -> list[PricingRule]: ...
    async def get_by_region(region: str) -> list[PricingRule]: ...
    async def update(rule: PricingRule) -> PricingRule: ...

class PromotionRepository(Protocol):
    async def create(promotion: Promotion) -> Promotion: ...
    async def list_active(now: datetime) -> list[Promotion]: ...
    async def get_by_type(promo_type: PromotionType) -> list[Promotion]: ...
```

**不变量**:
1. 定价规则倍率必须 > 1.0（售价不能低于成本）
2. 促销活动必须有有效时间范围
3. expire_time < now 的促销自动失效
4. 成本价为负时拒绝计算

---

## 2. 聚合间关系

```
User (1) ──── (N) PetProfile
User (1) ──── (N) Order
Order (N) ──── (N) Product (通过 OrderItem)
PetProfile ──── Product (suitable_for 关联)
Region ──── Order (order_currency)
Region ──── Product (region_availability)

--- 管理后台新增 (Phase 1-4) ---
Supplier (1) ──── (N) Product (supplier_id + supplier_sku)
Order (1) ──── (N) Shipment (order_id)
PricingRule ──── Region (region_code)
Promotion ──── Product (applicable_products)
```

**聚合间引用规则**:
- 聚合内: 直接引用对象
- 聚合间: 仅引用 ID，不直接引用对象
- 跨聚合查询: 通过 Application Service 协调

**示例**:
```python
# ✅ 正确: 跨聚合只引用 ID
order = Order(
    id=uuid4(),
    user_id=user_id,          # 引用 User 聚合
    items=[                  # 引用 Product 聚合
        OrderItem(
            product_id=product_id,  # 只存 ID
            name="Product Name",    # 冗余快照
            price=Decimal("29.99"),
            quantity=1,
        )
    ],
    region_code="US",         # 引用 Region 聚合
)

# ❌ 错误: 跨聚合直接引用对象
order = Order(
    user=user_object,         # 不要这样做
    products=[product_obj],   # 不要这样做
)
```

---

## 3. 限界上下文 (Bounded Contexts)

| 限界上下文 | 聚合 | 职责 |
|-----------|------|------|
| **Catalog Context** | Product, Category | 商品信息管理 |
| **Customer Context** | User, PetProfile | 用户和宠物数据 |
| **Order Context** | Order, OrderItem | 订单全流程 |
| **Payment Context** | Payment, Refund | 支付和退款 |
| **Shipping Context** | Shipping, Tracking | 物流和追踪 |
| **AI Context** | Conversation, Recommendation | AI 服务和推荐 |
| **Region Context** | Region, Currency | 区域和本地化 |
| **Notification Context** | Email, SMS, Push | 通知服务 |
| **Admin Context** (Phase 1-4) | Supplier, PricingRule, Promotion, Shipment | 管理后台运营能力 |

---

## 4. 反聚合设计

### 4.1 为什么 Order 包含 OrderItem 而非独立聚合？

**决策**: OrderItem 作为 Order 的子实体，而非独立聚合根。

**理由**:
1. OrderItem 没有独立的业务意义，不能脱离订单存在
2. 订单创建时需要原子性地创建 Order + 多个 OrderItems
3. 减少跨聚合事务的复杂度

### 4.2 为什么 PetProfile 是独立聚合？

**决策**: PetProfile 作为独立聚合根。

**理由**:
1. 宠物档案有独立的生命周期（创建、更新、归档）
2. 可以被多个上下文引用（推荐、聊天、个性化）
3. 查询模式独立（按 owner 查询、按 breed 搜索）

---

## 5. 仓储实现策略

### 5.1 PostgreSQL 仓储 (SQLAlchemy)

```python
# 接口定义 (Domain Layer)
class PetProfileRepository(Protocol):
    async def create(profile: PetProfile) -> PetProfile: ...

# 实现 (Infrastructure Layer)
class SQLAlchemyPetProfileRepository:
    def __init__(self, db_session: AsyncSession):
        self.session = db_session

    async def create(self, profile: PetProfile) -> PetProfile:
        # 领域模型 → ORM 模型
        orm_model = PetProfileModel.from_domain(profile)
        self.session.add(orm_model)
        await self.session.commit()
        await self.session.refresh(orm_model)
        # ORM 模型 → 领域模型
        return PetProfileModel.to_domain(orm_model)
```

### 5.2 pgvector 向量仓储

```python
class VectorRepository:
    """存储和检索商品 Embedding"""
    
    async def upsert_embedding(
        self, product_id: UUID, embedding: list[float], metadata: dict
    ):
        """插入或更新向量"""
        await self.conn.execute(
            """INSERT INTO product_embeddings 
               (product_id, embedding, metadata) 
               VALUES ($1, $2, $3)
               ON CONFLICT (product_id) DO UPDATE 
               SET embedding = $2, metadata = $3""",
            product_id, embedding, metadata,
        )

    async def similarity_search(
        self, query_embedding: list[float], k: int = 5
    ) -> list[tuple[UUID, float]]:
        """余弦相似度搜索"""
        result = await self.conn.execute(
            """SELECT product_id, 1 - (embedding <=> $1) as similarity
               FROM product_embeddings
               ORDER BY similarity DESC LIMIT $2""",
            query_embedding, k,
        )
        return result.fetchall()
```

### 5.3 Redis 仓储

```python
class RedisRepository:
    """会话、缓存、限流"""
    
    async def set_session(self, user_id: str, data: dict, ttl: int):
        await self.redis.hset(f"session:{user_id}", mapping=data)
        await self.redis.expire(f"session:{user_id}", ttl)

    async def get_session(self, user_id: str) -> dict:
        return await self.redis.hgetall(f"session:{user_id}")

    async def rate_limit(self, key: str, max_requests: int, window: int) -> bool:
        """滑动窗口限流"""
        pipe = self.redis.pipeline()
        pipe.zremrangebyscore(key, 0, time.time() - window)
        pipe.zadd(key, {str(time.time()): time.time()})
        pipe.zcard(key)
        pipe.expire(key, window)
        results = pipe.execute()
        return results[2] <= max_requests
```

### 5.4 RocketMQ 仓储 (消息发布)

```python
class RocketMQPublisher:
    """发布领域事件到 RocketMQ"""
    
    async def publish(self, event: DomainEvent):
        """发布领域事件"""
        await self.producer.send(
            topic=event.topic,
            tag=event.tag,
            body=event.to_dict(),
            keys=event.keys,
        )

class RocketMQConsumer:
    """消费 RocketMQ 消息"""
    
    @consumer.subscribe(topic="TOPIC_ORDER", tag="TAG_CREATE")
    async def handle_order_created(self, message: dict):
        """处理订单创建事件"""
        # 异步扣减库存
        await self.inventory_service.deduct(
            product_id=message["product_id"],
            quantity=message["quantity"],
        )
```
*（内容由AI生成，仅供参考）*
