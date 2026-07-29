# 模块需求文档 — 后端 (FastAPI + DDD)

## 1. 模块概述

**技术栈**: Python 3.12 + FastAPI + SQLAlchemy (async) + Pydantic v2 + LangChain

**架构**: 模块化单体，DDD 分层设计

**部署**: K3s Pod，3 replicas，ClusterIP:8000

---

## 2. 分层架构

```
src/forge/
├── main/                    # 入口层
│   ├── application.py       # FastAPI 应用初始化
│   ├── dependencies.py      # DI 依赖
│   └── middleware/          # 中间件
│       ├── auth.py          # JWT 认证
│       ├── i18n.py          # 国际化
│       └── rate_limit.py    # 速率限制
│
├── api/                     # API 路由层
│   ├── v1/
│   │   ├── router.py        # 路由聚合
│   │   ├── products.py      # 商品 API
│   │   ├── pets.py          # 宠物档案 API
│   │   ├── orders.py        # 订单 API
│   │   ├── auth.py          # 认证 API
│   │   ├── ai_chat.py       # AI 聊天 API
│   │   └── regions.py       # 区域 API
│   └── websocket/
│       └── chat.py          # WebSocket 聊天
│
├── domain/                  # 领域层 (核心)
│   ├── pet_profile/
│   │   ├── models.py        # 实体 + 值对象
│   │   ├── repository.py    # 仓储接口 (Protocol)
│   │   ├── service.py       # 领域服务
│   │   └── events.py        # 领域事件
│   ├── product/
│   │   ├── models.py
│   │   ├── repository.py
│   │   └── events.py
│   ├── order/
│   │   ├── models.py
│   │   ├── repository.py
│   │   ├── state_machine.py
│   │   └── events.py
│   ├── region/
│   │   ├── models.py
│   │   └── repository.py
│   └── ai/
│       ├── models.py
│       └── services.py
│
├── application/             # 应用层
│   ├── services/
│   │   ├── pet_service.py   # 宠物档案应用服务
│   │   ├── product_service.py
│   │   ├── order_service.py
│   │   └── ai_service.py
│   ├── dtos/
│   │   └── __init__.py      # Pydantic DTOs
│   └── commands.py          # 命令对象
│
└── infrastructure/          # 基础设施层
    ├── persistence/
    │   ├── database.py      # SQLAlchemy 异步引擎
    │   ├── repositories/
    │   │   ├── pet_repo.py  # PetProfile 仓储实现
    │   │   ├── product_repo.py
    │   │   └── order_repo.py
    │   └── models.py        # ORM 模型
    ├── external/
    │   ├── openai_client.py # OpenAI API 封装
    │   ├── stripe_client.py # Stripe API 封装
    │   └── shipping_client.py
    └── ai/
        ├── rag_pipeline.py  # RAG 管道
        ├── embedding.py     # Embedding 服务
        └── recommendation.py # 推荐引擎
```

---

## 3. 核心业务逻辑

### 3.1 宠物档案 (PetProfile)

**领域规则**:
1. 创建档案时自动计算生命周期阶段
2. 体重必须在品种合理范围内
3. 过敏原不能为空
4. 生命周期阶段变更时发布事件

**应用服务**:
```python
class PetService:
    async def create_profile(
        self,
        owner_id: UUID,
        data: PetProfileCreateDTO,
    ) -> PetProfile:
        # 1. 验证数据
        # 2. 创建领域模型
        # 3. 计算生命周期
        # 4. 持久化
        # 5. 发布 PetProfileCreated 事件
        # 6. 触发推荐更新
```

### 3.2 商品管理 (Product)

**领域规则**:
1. 售价 = 成本 × (1 + 利润率)，利润率 10%-500%
2. SKU 全局唯一
3. Slug 由 name 自动生成
4. 区域可用性校验
5. 适合宠物范围校验

**应用服务**:
```python
class ProductService:
    async def list_products(
        self,
        filters: ProductFilters,
        region: str,
        locale: str,
    ) -> PaginatedResponse[ProductResponse]:
        # 1. 应用区域过滤
        # 2. 应用品类/品种/价格筛选
        # 3. 排序
        # 4. 分页
        # 5. 返回 DTO
```

### 3.3 订单处理 (Order)

**状态机**:
```
PENDING → CONFIRMED → PAID → PROCESSING → SHIPPED → DELIVERED
   │                                                     │
   └────────────── CANCELLED ←───────────────────────────┘
                                        │
                                   RETURNED
```

**应用服务**:
```python
class OrderService:
    async def create_order(
        self,
        user_id: UUID,
        items: list[OrderItemCreateDTO],
        address: ShippingAddress,
        coupon_code: str | None,
        region: str,
    ) -> OrderResponse:
        # 1. 验证购物车商品存在且库存充足
        # 2. 应用优惠码
        # 3. 计算税费 (区域感知)
        # 4. 计算运费
        # 5. 创建订单 (DB 事务)
        # 6. 扣减库存 (Redis 分布式锁)
        # 7. 发送事务消息到 RocketMQ
        # 8. 返回 Stripe PaymentIntent
```

**RocketMQ 事务消息流程**:
```python
# 1. 发送半消息
half_msg = await rocketmq.send_half_message(
    topic="TOPIC_ORDER",
    tag="TAG_CREATE",
    body={"order_id": order_id, ...},
)

# 2. 执行本地事务 (扣库存 + 创建订单记录)
local_result = await self.execute_local_transaction(order)

# 3. 根据结果提交或回滚
if local_result.success:
    await rocketmq.commit(half_msg.message_id)
else:
    await rocketmq.rollback(half_msg.message_id)
```

### 3.4 AI 聊天 (RAG Pipeline)

**流程**:
```python
class AIService:
    async def chat(
        self,
        user_id: UUID,
        message: str,
        pet_id: UUID | None = None,
        conversation_id: UUID | None = None,
    ) -> AsyncGenerator[str, None]:
        # 1. 获取宠物档案 (如果有)
        pet_info = await self.get_pet_info(pet_id)
        
        # 2. 构建系统 Prompt
        system_prompt = self.build_system_prompt(pet_info)
        
        # 3. 检索相关知识 (RAG)
        #    a. 将用户问题转为 embedding
        #    b. pgvector 相似度搜索
        #    c. 获取 Top-K 相关文档片段
        contexts = await self.rag_retrieve(message, k=5)
        
        # 4. 构建用户 Prompt
        user_prompt = self.build_user_prompt(
            message=message,
            pet_info=pet_info,
            contexts=contexts,
        )
        
        # 5. 流式调用 OpenAI
        async for chunk in self.openai.stream_chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            model="gpt-4o",
        ):
            # 6. 提取推荐商品 (从 AI 回复中)
            recommendations = self.extract_recommendations(chunk)
            
            # 7. SSE 推送
            yield f"data: {json.dumps({'chunk': chunk, 'recommendations': recommendations})}\n\n"
        
        # 8. 保存对话记录
        await self.save_conversation(...)
```

### 3.5 推荐引擎

**三种算法组合**:
```python
class RecommendationEngine:
    async def recommend(
        self,
        user_id: UUID,
        pet_id: UUID | None = None,
        algorithm: str = "hybrid",
        limit: int = 10,
    ) -> list[Product]:
        sources = []
        
        # 1. 基于宠物档案推荐 (权重 40%)
        if pet_id:
            pet = await self.pet_repo.get_by_id(pet_id)
            score = 0.4
            sources.append((
                await self._recommend_by_pet(pet),
                score,
            ))
        
        # 2. 协同过滤推荐 (权重 30%)
        score = 0.3
        sources.append((
            await self._recommend_collaborative(user_id),
            score,
        ))
        
        # 3. 季节性推荐 (权重 30%)
        score = 0.3
        sources.append((
            await self._recommend_seasonal(),
            score,
        ))
        
        # 4. 加权合并 + 去重
        return self._combine_and_rank(sources, limit)
```

---

## 4. 中间件

### 4.1 认证中间件

```python
class AuthMiddleware:
    """JWT 认证中间件"""
    
    async def authenticate(self, request: Request) -> User | None:
        # 1. 从 Authorization header 读取 Bearer token
        # 2. 验证 token 签名和有效期
        # 3. 检查 Redis 中是否在黑名单
        # 4. 返回 User 对象或 None
```

### 4.2 国际化中间件

```python
class I18nMiddleware:
    """请求语言检测中间件"""
    
    async def process(self, request: Request):
        # 1. 优先级: URL locale > Cookie > Accept-Language > Default
        # 2. 设置 request.state.locale
        # 3. 设置 request.state.region (从 cookie 或 IP)
```

### 4.3 速率限制中间件

```python
class RateLimitMiddleware:
    """Redis 滑动窗口限流"""
    
    LIMITS = {
        "/api/v1/products": {"requests": 200, "window": 60},
        "/api/v1/pets": {"requests": 100, "window": 60},
        "/api/v1/ai/chat": {"requests": 30, "window": 60},
        "/api/v1/auth/login": {"requests": 5, "window": 60},
    }
    
    async def check(self, request: Request) -> bool:
        key = f"ratelimit:{request.client.host}:{request.url.path}"
        return await self.redis.rate_limit(key, **self.LIMITS[request.url.path])
```

---

## 5. 数据库模型 (ORM)

### 5.1 PetProfile

```python
class PetProfileModel(Base):
    __tablename__ = "pet_profiles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    breed = Column(Enum(Breed), nullable=False)
    birthday = Column(Date, nullable=False)
    weight = Column(Float, nullable=True)
    gender = Column(Enum(Gender), nullable=False)
    spayed_neutered = Column(Boolean, default=False)
    health_notes = Column(JSON, default=list)
    allergies = Column(JSON, default=list)
    lifecycle = Column(Enum(LifeStage), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 索引
    __table_args__ = (
        Index("ix_pet_profiles_owner", "owner_id"),
        Index("ix_pet_profiles_breed", "breed"),
    )
```

### 5.2 Product

```python
class ProductModel(Base):
    __tablename__ = "products"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    sku = Column(String(50), unique=True, nullable=False, index=True)
    slug = Column(String(200), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    ai_description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    cost = Column(Numeric(10, 2), nullable=False)
    category = Column(Enum(ProductCategory), nullable=False, index=True)
    breed_groups = Column(JSON, nullable=False)
    suitable_for = Column(JSON, nullable=True)
    tags = Column(JSON, default=list)
    inventory = Column(Integer, default=0)
    rating = Column(Numeric(3, 2), default=0)
    review_count = Column(Integer, default=0)
    images = Column(JSON, default=list)
    region_availability = Column(JSON, default=list)
    is_ai_generated = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        CheckConstraint("price > 0"),
        CheckConstraint("inventory >= 0"),
    )
```

### 5.3 Order

```python
class OrderModel(Base):
    __tablename__ = "orders"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    order_number = Column(String(20), unique=True, nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING, nullable=False)
    subtotal = Column(Numeric(12, 2), nullable=False)
    tax = Column(Numeric(12, 2), default=0)
    shipping_cost = Column(Numeric(12, 2), default=0)
    discount = Column(Numeric(12, 2), default=0)
    total = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="USD")
    shipping_address = Column(JSON, nullable=False)
    items = Column(JSON, nullable=False)
    payment_intent_id = Column(String(200), nullable=True)
    tracking_number = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        Index("ix_orders_user", "user_id", "created_at"),
        Index("ix_orders_status", "status"),
    )
```

---

## 6. 健康检查端点

```python
@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """K8s 健康检查端点"""
    checks = {}
    
    # DB 连接
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "healthy"
    except Exception:
        checks["database"] = "unhealthy"
    
    # Redis 连接
    try:
        await redis_client.ping()
        checks["redis"] = "healthy"
    except Exception:
        checks["redis"] = "unhealthy"
    
    # RocketMQ 连接
    try:
        resp = await httpx.AsyncClient().get("http://rocketmq-proxy:8081/health")
        checks["rocketmq"] = "healthy" if resp.status_code == 200 else "unhealthy"
    except Exception:
        checks["rocketmq"] = "unhealthy"
    
    status = "healthy" if all(v == "healthy" for v in checks.values()) else "degraded"
    
    return JSONResponse(
        status_code=200 if status == "healthy" else 503,
        content={"status": status, "checks": checks},
    )
```
