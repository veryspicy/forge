---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 14f48488fead00d28e11c31f9845685c_0e0b98e46fd411f1b2f55254006c9bbf
    ReservedCode1: RmWTM34s4/+1Isz4SCVkF7dC08mCuZxemerLjDdmFCsAFhdCkSNi94l7ee/eGS2kFK4j1R1YLUVNxddPjYCxJa8RqpaRRYjAOxOwNvGOF3Yq0jD0fj4nZzwOO48PZc7bLYLbh2sY+Nh6ZmzCApd5TMca1oQ2y+UDlJhdaIcc7F7iXA3Pe+1ocLF3KAM=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 14f48488fead00d28e11c31f9845685c_0e0b98e46fd411f1b2f55254006c9bbf
    ReservedCode2: RmWTM34s4/+1Isz4SCVkF7dC08mCuZxemerLjDdmFCsAFhdCkSNi94l7ee/eGS2kFK4j1R1YLUVNxddPjYCxJa8RqpaRRYjAOxOwNvGOF3Yq0jD0fj4nZzwOO48PZc7bLYLbh2sY+Nh6ZmzCApd5TMca1oQ2y+UDlJhdaIcc7F7iXA3Pe+1ocLF3KAM=
---



﻿# Forge — 总体架构文档

## 1. 项目概述

Forge 是一个全球化宠物用品 AI 独立站，采用模块化单体 + DDD 架构，部署在 OCI K3s 双区域集群上。

### 1.1 目标市场
- **Phase 1**: 北美 (US/CA) — 美元结算，英文界面
- **Phase 2**: 欧洲 (DE/FR/ES) — 欧元结算，多语言 + VAT
- **Phase 3**: 中东 (SA/AE) — 阿拉伯语 RTL + Mada 支付

### 1.2 核心商业价值
1. **宠物数字档案** — 基于品种/年龄/健康状况的个性化推荐
2. **AI 养宠顾问** — RAG 驱动的实时问答 + 商品推荐
3. **Dropshipping 模式** — 零库存代发，轻资产运营

### 1.3 技术原则
- **零预算启动**: 全部使用开源/免费方案
- **DDD 驱动设计**: 聚合边界清晰，未来可平滑拆微服务
- **模块化单体**: MVP 阶段单进程，降低运维复杂度
- **全球化就绪**: i18n + 多币种 + 区域配置内置
- **K8s Native**: 利用 K3s 原生能力，不引入额外中间件

---

## 2. 技术栈总览

| 层级 | 技术选型 | 版本 | 理由 |
|------|---------|------|------|
| **前端** | Nuxt 3 + Vue 3 + TS | 3.14+ | Vue 生态熟练，SSR 友好 SEO |
| **UI** | TailwindCSS + Shadcn-vue | 4.x | 原子化 CSS，组件丰富 |
| **状态** | Pinia | 2.2+ | Vue 官方推荐，TypeScript 友好 |
| **国际化** | nuxt-i18n | 2.1+ | 路由级多语言 + RTL 支持 |
| **后端** | Python 3.12 + FastAPI | 0.115+ | AI 生态第一，异步原生 |
| **ORM** | SQLAlchemy 2.0 (async) | 2.0+ | DDD 仓储模式完美支持 |
| **迁移** | Alembic | 1.14+ | Python 生态标准 |
| **AI** | LangChain + OpenAI API | 0.3+ | RAG 生态最成熟 |
| **向量** | pgvector (PG 扩展) | 0.5+ | 与 PG 同库，零额外依赖 |
| **数据库** | PostgreSQL 16 | 16.x | 关系型 + 向量搜索一体 |
| **缓存** | Redis 7 Cluster | 7.x | 会话/缓存/限流/队列 |
| **消息** | Apache RocketMQ 5.3 | 5.3+ | 事务消息 + 你熟悉 |
| **对象存储** | MinIO | latest | S3 兼容，K3s 内部署 |
| **容器** | Docker + Docker Compose | 27+ | 本地开发 + CI 构建 |
| **编排** | K3s (Rancher) | 1.31+ | 轻量 K8s，适合边缘 |
| **Ingress** | Traefik (K3s 内置) | 3.x | 自动 HTTPS + 路由 |
| **CI/CD** | Jenkins + ArgoCD + Harbor | - | 你指定的技术栈 |
| **支付** | Stripe | - | 支持 135+ 币种 |
| **CDN** | Cloudflare | - | 免费层 + 全球边缘 |
| **MCP** | Python MCP SDK | 1.x | 大模型 Agent 对接管理后台 |

---

## 3. 架构分层

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Presentation Layer                           │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  Nuxt 3 SPA/SSR (Cloudflare Pages / K3s Pod)                │    │
│  │  ├── 多语言路由 (/en/, /de/, /ar/)                           │    │
│  │  ├── 响应式布局 (Mobile First)                               │    │
│  │  ├── AI Chat Widget (WebSocket)                              │    │
│  │  └── PWA 支持 (离线缓存)                                     │    │
│  └─────────────────────────────────────────────────────────────┘    │
└────────────────────────────────────────────────┬────────────────────┘
                                                 │ HTTPS
┌────────────────────────────────────────────────▼────────────────────┐
│                      API Gateway Layer                              │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Traefik Ingress (K3s 内置)                                  │   │
│  │  ├── SSL/TLS (cert-manager)                                 │   │
│  │  ├── 路由分发 (/api/* → backend, /* → frontend)             │   │
│  │  ├── Middleware (限流/安全头/StripPrefix)                    │   │
│  │  └── 健康检查 (Liveness/Readiness)                           │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  FastAPI Monolith (Backend Pod)                              │   │
│  │  ├── REST API (JSON)                                         │   │
│  │  │   ├── /api/v1/*          消费者 API                        │   │
│  │  │   ├── /api/admin/v1/*    管理后台 API (Phase 2)            │   │
│  │  │   └── /mcp/*             MCP Server (Phase 5)             │   │
│  │  ├── WebSocket (AI Chat 实时)                                │   │
│  │  ├── JWT Authentication                                     │   │
│  │  ├── RBAC (Admin / Operator / Support)                      │   │
│  │  └── Request Validation (Pydantic v2)                       │   │
│  └─────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────┬────────────────────┘
                                                 │ 进程内调用
┌────────────────────────────────────────────────▼────────────────────┐
│                        Domain Layer (DDD)                           │
│                                                                     │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌───────────┐ │
│  │ PetProfile   │ │   Product    │ │    Order     │ │  Region   │ │
│  │  Aggregate   │ │  Aggregate   │ │  Aggregate   │ │ Aggregate │ │
│  │              │ │              │ │              │ │           │ │
│  │ - Pet        │ │ - Product    │ │ - Order      │ │ - Region  │ │
│  │ - Breed      │ │ - Category   │ │ - OrderItem  │ │ - Currency│ │
│  │ - Health     │ │ - Pricing    │ │ - Shipping   │ │ - Payment │ │
│  │ - Lifecycle  │ │ - SEO        │ │ - Status     │ │ - Regs    │ │
│  │              │ │              │ │   Machine    │ │           │ │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └─────┬─────┘ │
│         │                │                 │               │       │
│  ┌──────┴────────┐ ┌─────┴────────┐ ┌──────┴───────┐              │
│  │   Supplier    │ │  PricingRule │ │   Shipment   │              │
│  │   Aggregate   │ │  + Promotion │ │   Aggregate  │              │
│  │   (Phase 1)   │ │   (Phase 4)  │ │   (Phase 3)  │              │
│  │               │ │              │ │              │              │
│  │ - Supplier    │ │ - Rule       │ │ - Tracking   │              │
│  │ - API Config  │ │ - Promotion  │ │ - Carrier    │              │
│  │ - SKU Map     │ │ - Engine     │ │ - Events     │              │
│  └───────┬───────┘ └──────┬───────┘ └──────┬───────┘              │
│          │                │                 │                      │
│  ┌──────▼────────────────▼─────────────────▼───────────────▼─────┐ │
│  │              Domain Services (跨聚合协调)                      │ │
│  │  ├── PetRecommendationService                                 │ │
│  │  ├── OrderFulfillmentService                                  │ │
│  │  ├── PricingAndTaxService                                     │ │
│  │  └── RegionConfigurationService                               │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              AI Domain (独立聚合边界)                        │   │
│  │  ├── PetAssistant (RAG Pipeline)                            │   │
│  │  ├── ContentGenerator (产品描述/博客)                        │   │
│  │  ├── RecommendationEngine (混合推荐)                         │   │
│  │  ├── EmbeddingService (向量化)                               │   │
│  │  ├── MCP Server (大模型 Agent 对接 — Phase 5)               │   │
│  │  └── SupplierSearchPipeline (AI 探针 — Phase 6)             │   │
│  └─────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────┬────────────────────┘
                                                 │
┌────────────────────────────────────────────────▼────────────────────┐
│                     Infrastructure Layer                            │
│                                                                     │
│  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐   │
│  │ Persistence      │ │ External APIs    │ │ Messaging        │   │
│  │                  │ │                  │ │                  │   │
│  │ - PostgreSQL     │ │ - OpenAI API     │ │ - RocketMQ       │   │
│  │ - pgvector       │ │ - Stripe         │ │ - Redis Pub/Sub  │   │
│  │ - Redis          │ │ - ShipStation    │ │                  │   │
│  │ - MinIO (S3)     │ │ - SendGrid       │ │                  │   │
│  └──────────────────┘ └──────────────────┘ └──────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. 部署架构

### 4.1 基础设施

```
┌─────────────────────────────────────────────────────────────┐
│                    全球流量入口                               │
│                                                             │
│  Cloudflare CDN                                             │
│  ├── DNS (GeoDNS 智能路由)                                  │
│  ├── Edge Cache (静态资源 + HTML)                           │
│  └── WAF (基础防护)                                         │
│       │                                                     │
│       ▼                                                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              OCI Load Balancer (入口)                │   │
│  │  ├── 健康检查: HTTP GET /health                     │   │
│  │  ├── 路由: /frontend → frontend-svc:3000            │   │
│  │  ├── 路由: /api → api-gateway-svc:8000              │   │
│  │  └── SSL Termination                                │   │
│  └─────────────────────────────────────────────────────┘   │
│       │                                                     │
│       ▼ Private Network                                     │
│  ┌──────────────┐            ┌──────────────┐              │
│  │ 🇺🇸 US-West  │            │ 🇪🇺 EU-West  │              │
│  │ K3s Cluster  │            │ K3s Cluster  │              │
│  │ (主)         │            │ (主)         │              │
│  └──────┬───────┘            └──────┬───────┘              │
│         │                          │                        │
│  ┌──────▼───────┐            ┌─────▼────────┐              │
│  │ Bastion-PRIM  │            │ Bastion-Main  │              │
│  │ (出口代理)    │            │ (出口代理)    │              │
│  └──────────────┘            └───────────────┘              │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 K3s 命名空间

| 命名空间 | 用途 | 服务 |
|---------|------|------|
| `forge-public` | 前端 + API (可对外) | frontend, backend, auth |
| `forge-ai` | AI 推理服务 | ai-chat, ai-recommender |
| `forge-data` | 数据存储 (仅内部) | postgres, redis, minio |
| `forge-mq` | 消息队列 | rocketmq-namesrv, broker, proxy |

### 4.3 服务部署清单

| 服务 | 镜像 | Replicas | 资源限制 |
|------|------|----------|---------|
| frontend | harbor/forge/frontend | 3 | 0.5C/512Mi |
| backend | harbor/forge/backend | 3 | 1C/1Gi |
| ai-service | harbor/forge/ai-service | 2 | 1C/2Gi |
| postgres | postgres:16 + pgvector | 3 (1M+2S) | 1C/2Gi |
| redis | redis:7-alpine | 6 (3M+3S) | 0.5C/512Mi |
| rocketmq-proxy | rocketmq:5.3.1 | 2 | 0.5C/1Gi |
| rocketmq-broker | rocketmq:5.3.1 | 2 | 2C/4Gi |
| rocketmq-namesrv | rocketmq:5.3.1 | 2 | 0.5C/512Mi |
| minio | minio/minio | 4 | 1C/2Gi |

---

## 5. 数据流

### 5.1 用户请求流

```
User → Cloudflare CDN → OCI LB → Traefik Ingress
                                    ├── / → frontend Pod (Nuxt SSR)
                                    └── /api/* → backend Pod (FastAPI)
                                                        ├── 读 DB → PostgreSQL
                                                        ├── 读缓存 → Redis
                                                        ├── 发消息 → RocketMQ
                                                        └── 调 AI → AI Service
```

### 5.2 订单创建流 (事件驱动)

```
1. 用户提交订单 → POST /api/v1/orders
2. Backend: 创建订单记录 (DB 事务)
3. Backend: 发送事务消息 → TOPIC_ORDER:TAG_CREATE
4. 异步消费:
   ├── Inventory Service: 扣减库存
   ├── AI Service: 生成个性化订单描述
   ├── Notification Service: 发送确认邮件
5. Stripe Webhook → backend 接收支付结果
6. Backend: 更新订单状态 → 发送 TAG_PAY 消息
7. 异步消费:
   ├── Shipping Service: 创建运单
   ├── Notification: 发货通知
```

### 5.3 AI 聊天流

```
1. 前端 WebSocket 连接 → backend /ws/chat
2. Backend: 获取用户宠物档案
3. Backend: 调用 RAG Pipeline
   ├── 用户问题 → Embedding
   ├── pgvector 相似度检索 (Top-K)
   ├── 构建 Prompt (宠物档案 + 检索结果 + 问题)
   └── OpenAI GPT-4o 生成回复
4. Backend: 流式返回 (SSE)
5. Backend: 保存对话到 DB + 缓存到 Redis
```

---

## 6. 安全架构

| 层面 | 措施 |
|------|------|
| **网络** | K8s NetworkPolicy (仅 LB 入站 + 跳板机出站) |
| **传输** | TLS 1.3 (cert-manager 自动续签) |
| **认证** | JWT (Access 24h + Refresh 7d) |
| **授权** | RBAC (用户/管理员) |
| **API** | 速率限制 (Redis 滑动窗口) |
| **支付** | Stripe 托管，不接触卡号 |
| **数据** | 敏感字段 AES-256 加密 (DB) |
| **合规** | GDPR (EU 区域), CCPA (US 区域) |

---

## 7. 国际化设计

### 7.1 路由策略
- 前缀模式: `/en/products`, `/de/products`, `/ar/products`
- 默认语言: 英语 (`/products` 等价于 `/en/products`)
- RTL 支持: 阿拉伯语自动切换 `dir="rtl"`

### 7.2 翻译管理
- 静态翻译: `locales/{en,de,fr,es,ar}.json`
- 动态翻译: AI 辅助翻译 (OpenAI API)
- 翻译审核: 人工审核后入库

### 7.3 区域感知
```python
# 每个区域独立的配置
region_config = {
    "na": {"currency": "USD", "locale": "en-US", "tax": "sales_tax"},
    "eu": {"currency": "EUR", "locale": "de-DE", "tax": "vat"},
    "me": {"currency": "SAR", "locale": "ar-SA", "tax": "vat"},
}
```

---

## 8. 监控与可观测性 (Phase 2+)

| 工具 | 用途 | 阶段 |
|------|------|------|
| Prometheus | 指标采集 | Phase 2 |
| Grafana | 可视化仪表盘 | Phase 2 |
| Loki | 日志聚合 | Phase 2 |
| Jaeger | 分布式追踪 | Phase 3 |

---

## 9. 演进路线

| Phase | 时间 | 目标 | 新增能力 |
|-------|------|------|---------|
| **P1: MVP** | 2-3 周 | 北美上线 | 商品浏览 + AI 顾问 + 支付 |
| **P2: 欧洲** | 4-6 周 | 多语言 + VAT | 德法西意 + Klarna + SEO |
| **P3: 中东** | 7-9 周 | RTL + 本地支付 | 阿拉伯语 + Mada + 斋月营销 |
| **P4: 增长** | 10-12 周 | 订阅 + 定制 | 定期配送 + AI 定制设计 |
| **P5: 微服务** | 12+ 周 | 拆分 + Nacos | 服务注册 + 独立扩缩容 |

---

## 10. 关键决策记录 (ADR)

### ADR-001: 为什么选模块化单体而非微服务？
- **决策**: MVP 阶段使用 FastAPI 单体，内部按 DDD 聚合隔离
- **理由**: 零预算团队，降低运维复杂度，加快交付速度
- **后果**: 代码层面聚合边界清晰，未来可直接提取为独立进程

### ADR-002: 为什么用 RocketMQ 而非 Redis Queue？
- **决策**: 引入 RocketMQ 作为消息中间件
- **理由**: 团队熟悉 RocketMQ，事务消息对订单场景至关重要
- **后果**: 增加约 5 Core / 12Gi 资源，但换来可靠的消息保证

### ADR-003: 为什么不用 Nacos/Consul？
- **决策**: 使用 K8s 原生 Service DNS + ConfigMap
- **理由**: 模块化单体不需要服务注册，K8s 已提供替代能力
- **后果**: 拆微服务时可平滑引入 Nacos

### ADR-004: 为什么选 Python 而非 Java？
- **决策**: 后端使用 Python + FastAPI
- **理由**: AI 生态 Python 绝对领先，RAG/Embedding 开发效率高 3-5 倍
- **后果**: 类型安全不如 Java，但 Pydantic + mypy 可弥补
---

## 11. Frontend 架构详解

### 11.1 前台 (Storefront)

Nuxt 3 SPA/SSR，面向消费者。布局、路由、组件分层详见 `FRONTEND-SURVEY.md`。

### 11.2 管理后台 (Admin Dashboard)

独立于前台的完整子系统，复用 Nuxt 3 + Vue 3 技术栈。

**布局架构**：

```
┌──────────────────────────────────────────────────────────┐
│  Admin Layout (layouts/admin.vue)                        │
│  ┌──────────────┬───────────────────────────────────────┐│
│  │ Sidebar      │  Top Bar (面包屑 + 用户菜单)          ││
│  │ (240px 可折叠)│  ─────────────────────────────────── ││
│  │              │                                      ││
│  │ 仪表盘        │  <slot /> 内容区                      ││
│  │ 商品管理      │                                      ││
│  │ 订单管理      │                                      ││
│  │ 供应商        │                                      ││
│  │ 定价引擎      │                                      ││
│  │ AI客服       │                                      ││
│  │ 设置         │                                      ││
│  │              │                                      ││
│  └──────────────┴───────────────────────────────────────┘│
└──────────────────────────────────────────────────────────┘
```

**路由守卫 (`middleware/auth.ts`)**：
- 检查 `useAuth().isAuthenticated`，未登录跳转 `/login`
- `/admin/**` 路由当前已登录即可访问（后续收紧为三角色 RBAC）

**组件分层**：

| 层 | 目录 | 职责 |
|----|------|------|
| 布局 | `layouts/admin.vue` | 侧边栏 + 顶栏 + 内容区插槽 |
| 页面 | `pages/admin/*.vue` | 7 个功能页面，定义 `definePageMeta({ layout: 'admin', middleware: 'auth' })` |
| 公共组件 | `components/admin/` | AdminSidebar / StatCard / DataTable / StatusBadge / OrderDetailPanel / ChatStatusBadge |
| 状态管理 | `stores/admin.ts` | Pinia Setup Store：侧边栏状态 + 仪表盘数据 |
| API 适配 | `composables/useAdminApi.ts` | `$fetch.create` 封装，baseURL `localhost:8000/api/admin/v1`，20 个具名导出函数 |

**交互模式**：
- Drawer 右侧滑入 / Modal 居中缩放，均带 backdrop 过渡
- 防抖搜索 300ms、骨架屏加载态、行展开 max-height 动画
- 批量操作多选后滑入操作栏
- 状态筛选 pill 多选模式，Toggle 使用纯 CSS peer-checked

**设计体系**：
- 工业精准风格（industrial precision）
- 状态驱动色彩：订单状态机 8 种 oklch 色码映射
- 定价层级可视化：四级优先级缩进 + 颜色深浅
- 零第三方 UI 框架：纯 Tailwind CSS 4 手写

*（内容由AI生成，仅供参考）*
*（内容由AI生成，仅供参考）*
