---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 14f48488fead00d28e11c31f9845685c_0c9cd1426fd411f1897e5254002afed2
    ReservedCode1: roUcpV435y17/+KR7FIqKDylDW8ts6UiDdvf///uOyiMdVOITyn6sA+EU7Q9Z01Rf+++pUP+ph/dUMsuhh1lvY+k5UMG3hMOLlsF4SD+AzmcmyaFAei10JUiPrcNZDBwqbV6N8vMYtf3kDR36BabxTf5Qgi3DWQZZprbLZpfhaf1iin9dX0atsLqhkQ=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 14f48488fead00d28e11c31f9845685c_0c9cd1426fd411f1897e5254002afed2
    ReservedCode2: roUcpV435y17/+KR7FIqKDylDW8ts6UiDdvf///uOyiMdVOITyn6sA+EU7Q9Z01Rf+++pUP+ph/dUMsuhh1lvY+k5UMG3hMOLlsF4SD+AzmcmyaFAei10JUiPrcNZDBwqbV6N8vMYtf3kDR36BabxTf5Qgi3DWQZZprbLZpfhaf1iin9dX0atsLqhkQ=
---



# 管理后台后端 — 开发日志

> 记录日期: 2026-06-24  
> 开发范围: 管理后台后端 6 个 Phase（Supplier / Admin路由+权限 / Order扩展+物流 / 定价引擎 / MCP Server / AI Search Pipeline）  
> 测试覆盖: 106 个单元测试，100% 通过

---

## 1. 新增模块架构

管理后台后端分 6 个 Phase 顺序完成：

### Phase 1 — Supplier 供应商聚合根

建立供应商管理基础设施，这是后续所有供应商相关功能的基础。

| 层 | 文件 | 说明 |
|---|---|---|
| Domain | `domain/supplier/models.py` | Supplier 实体 + 工厂方法 `create_supplier()` |
| Infra | `infrastructure/models/supplier_model.py` | `SupplierModel` ORM 映射 |
| Infra | `infrastructure/repositories/supplier_repo.py` | 供应商仓储实现 |
| Application | `application/services/supplier_service.py` | 供应商 CRUD 业务编排 |
| Application | `application/dtos/supplier_dtos.py` | Pydantic v2 数据传输对象 |
| API | `api/v1/suppliers.py` | REST CRUD + 软删除端点，需鉴权 |

**关键设计**：
- 软删除策略：`delete` 仅设 `is_active=False`，不做物理删除
- API 配置（base_url / auth_type / credentials）作为值对象内嵌于 Supplier
- Region 列表支持动态增删，重复添加自动忽略

### Phase 2 — Admin 路由层 + 角色权限

建立管理后台的 API 隔离层和角色权限体系。

| 层 | 文件 | 说明 |
|---|---|---|
| API | `api/admin/v1/router.py` | 管理后台专用路由前缀 `/api/admin/v1` |
| Infra | `main/dependencies.py` | `UserRole` 枚举 + `require_role()` 依赖工厂 |

**三角色定义**：

| 角色 | 枚举值 | 权限范围 |
|---|---|---|
| Admin | `ADMIN` | 全部功能（供应商/定价/系统设置/角色管理） |
| Operator | `OPERATOR` | 商品/订单/定价运营操作 |
| Support | `SUPPORT` | 订单查询/退款/物流查询 |

**当前状态**：开发阶段占位实现 — 所有已认证用户视为 admin。待用户表完善后接入真实角色校验。

### Phase 3 — Order 扩展 + Shipment 物流

**Order 状态机扩展**（在现有状态机基础上新增管理后台相关状态）：

```
原有: PENDING → CONFIRMED → PAID → PROCESSING → SHIPPED → DELIVERED

新增:
PAID → PENDING_REVIEW (提交审核)
PENDING_REVIEW → PROCURING (审核通过)
PENDING_REVIEW → CANCELLED (审核驳回)
PROCURING → SHIPPED (采购完成发货)
PROCURING → PROCURE_FAILED (采购失败)
```

| 新增方法 | 行为 |
|---|---|
| `submit_for_review()` | PAID → PENDING_REVIEW |
| `approve()` | PENDING_REVIEW → PROCURING |
| `reject(reason)` | PENDING_REVIEW → CANCELLED，记录驳回原因 |
| `start_procurement()` | 进入采购流程 |
| `mark_procure_failed(reason)` | PROCURING → PROCURE_FAILED |

**Shipment 聚合根**（独立聚合）：

| 层 | 文件 | 说明 |
|---|---|---|
| Domain | `domain/shipment/models.py` | Shipment 实体 + 状态机 + Events 轨迹 |
| Infra | `infrastructure/repositories/shipment_repo.py` | 物流仓储 |
| Application | `application/services/shipment_service.py` | 物流业务编排 |
| API | `api/v1/shipments.py` | 物流追踪端点 |

**Shipment 状态机**：`PENDING → PICKED_UP → IN_TRANSIT → OUT_FOR_DELIVERY → DELIVERED / FAILED`

**核心字段**：`tracking_number` / `carrier` / `events`（物流事件轨迹列表）

### Phase 4 — PricingRule 定价引擎

| 层 | 文件 | 说明 |
|---|---|---|
| Domain | `domain/pricing/models.py` | PricingRule + Promotion 实体 |
| Infra | `infrastructure/repositories/pricing_repo.py` | 定价仓储 |
| Application | `application/services/pricing_service.py` | 定价计算引擎 |
| API | `api/v1/pricing.py` | 定价规则 CRUD |

**PricingRule**：区域倍率 + 固定运费，按优先级排序匹配。

**Promotion 类型**：

| 类型 | 枚举值 | 说明 |
|---|---|---|
| 满减 | `THRESHOLD_DISCOUNT` | 满 X 减 Y |
| 优惠券 | `COUPON` | 固定金额 / 百分比折扣 |
| 会员价 | `MEMBER_PRICE` | 会员等级折扣 |

**定价引擎 `calculate_final_price` 四级优先级**：

```
1. 手动覆盖价格 (Manual Override) — 最高优先级
2. 促销活动 (Promotion)
3. 区域定价规则 (Region Pricing Rule)
4. 全局默认规则 (Global Default)
```

**叠加控制**：Promotion 支持 `stackable` 属性控制是否可与其他促销叠加。

### Phase 5 — MCP Server

将管理后台能力通过 MCP (Model Context Protocol) 暴露给外部大模型 Agent。

| 文件 | 说明 |
|---|---|
| `mcp/server.py` | MCP Server 主入口 |
| `mcp/tools.py` | 9 个 MCP Tool 定义 |
| `mcp/auth.py` | API Key SHA-256 哈希验证 |
| `mcp/transport.py` | SSE 传输层 (`/mcp/sse` + `/mcp/messages`) |

**9 个 MCP Tools**：

| Tool | 状态 | 说明 |
|---|---|---|
| `create_product` | 已实现 | 创建商品（强制 draft 状态） |
| `update_product` | 已实现 | 更新商品信息 |
| `list_products` | 已实现 | 查询商品列表 |
| `batch_create_products` | 已实现 | 批量创建（单次上限 50） |
| `update_product_price` | 已实现 | 更新商品定价 |
| `set_product_status` | **占位** | 依赖 Product.status 字段（待补全） |
| `list_suppliers` | 已实现 | 查询供应商列表 |
| `get_supplier_products` | **占位** | 依赖 Product.supplier_id 字段（待补全） |
| `get_sales_stats` | **占位** | 需订单模块完善后对接真实数据 |

**鉴权**：API Key 使用 SHA-256 哈希存储，请求时明文比对哈希。

### Phase 6 — AI Search Pipeline

用户通过 AI 聊天发起商品搜索时，后端自动调用供应商 API 搜索匹配商品。

| 文件 | 说明 |
|---|---|
| `infrastructure/ai/supplier_search.py` | 供应商搜索适配器 + Mock 实现 |
| `infrastructure/ai/probe_service.py` | AI 探针服务 |

**适配器模式**：
- `BaseSupplierSearchAdapter` — 抽象接口
- `MockSupplierAdapter` — Mock 实现（当前默认）

**AI 探针流程**：
```
用户提问 → LLM 提取参数（宠物类型/品类/预算）
  → 并行搜索多个供应商
  → 定价计算
  → 低于阈值：自动创建商品（draft）
  → 高于阈值：展示估价 → 人工审核
```

**关键参数**：
- 超时控制：`asyncio.wait_for(30s)`
- 自动创建商品强制 `draft` 状态
- 当前仅 Mock 适配器，后续逐供应商接入真实 API

---

## 2. 关键设计决策

| 决策 | 内容 | 理由 |
|---|---|---|
| **API 隔离** | 消费者 API (`/api/v1`) 与管理后台 API (`/api/admin/v1`) 分离 | 权限模型不同，独立路由便于中间件差异化 |
| **依赖注入集中** | 所有依赖集中在 `forge.main.dependencies` | 统一管理，测试 mock 路径唯一 |
| **软删除** | Supplier 删除设 `is_active=False` | 保留历史订单关联，避免外键断裂 |
| **Mock 优先** | AI 探针和供应商搜索先走 Mock 适配器 | 快速验证流程，后续逐供应商接入真实 API |
| **DDD 四层** | domain → infrastructure → application → api | 与现有架构统一，所有新模块遵循 |

---

## 3. 测试约定

| 项目 | 约定 |
|---|---|
| 测试框架 | pytest + pytest-asyncio |
| Mock 路径 | `forge.main.dependencies`（所有依赖集中位置） |
| 风格 | Arrange-Act-Assert，每个测试独立无副作用 |
| 目录结构 | `tests/unit/{domain,application,infrastructure,api}/test_*.py` |
| API 测试 | FastAPI TestClient + mock dependencies |
| conftest fixtures | `mock_db_session` / `mock_product_repo` / `mock_supplier_repo` / `test_client` 等 |

**已知限制**：
- `require_role` 处于占位期间，`dependency_overrides` 不适用（函数在模块导入时即闭包），API 测试需直接 mock `get_current_user_id`
- 后续 `require_role` 接入真实用户表后，需重新激活相关权限测试

**106 个测试覆盖分布**：

| 模块 | 测试数 |
|---|---|
| `test_supplier.py` | 7 |
| `test_order_extended.py` | 7 |
| `test_shipment.py` | 5 |
| `test_pricing.py` | 13 |
| `test_mcp_auth.py` | 5 |
| `test_supplier_search.py` | 4 |
| `test_probe_service.py` | 4 |
| `test_supplier_service.py` | 7 |
| `test_pricing_service.py` | 3 |
| `test_shipment_service.py` | 5 |
| `test_suppliers_api.py` | 6 |
| `test_pricing_api.py` | 4 |
| `test_admin_router.py` | 2 |
| conftest fixtures | — |

---

## 4. 已知 TODO / 占位项

| 项目 | 状态 | 说明 |
|---|---|---|
| UserRole 检查 | 占位 | 当前所有已认证用户视为 admin，需对接用户表 |
| Product.supplier_id | 待补充 | domain Product 模型需新增 `supplier_id` 字段 |
| Product.status | 待补充 | domain Product 模型需新增 `status` 字段（draft/active/inactive） |
| MCP `set_product_status` | 占位 | 依赖 Product.status 字段 |
| MCP `get_supplier_products` | 占位 | 依赖 Product.supplier_id 字段 |
| MCP `get_sales_stats` | 占位 | 需订单模块完善后对接真实数据 |
| AI 探针超时控制 | 已实现 | `asyncio.wait_for(30s)` |
| 真实供应商 API 适配器 | 占位 | 当前仅 Mock，后续按供应商逐个实现 |

---

## 5. 文档同步状态

| 文档 | 操作 | 说明 |
|---|---|---|
| `REQUIREMENT-ADMIN.md` | 已存在 | 10 章完整需求规格 |
| `API-REFERENCE.md` | 已补充 | 新增 POST/PATCH products 接口 |
| `ROLE-PERMISSION.md` | 已存在 | 三角色权限矩阵 |
| `ARCHITECTURE.md` | **已更新** | 追加新增模块到架构分层 |
| `DDD-AGGREGATES.md` | **已更新** | 追加 Supplier/Shipment/PricingRule/Promotion 聚合根 |
| `DEVELOPMENT-LOG.md` | **新建（本文档）** | 本次 6 个 Phase 开发全过程记录 |
---

# 管理后台前端 — 开发日志

> 记录日期：2026-06-24  
> 开发范围：管理后台前端（基础架构 + 7 个页面 + 6 个公共组件）  
> 技术栈：Nuxt 3.14 / Vue 3.5 / Pinia 2.2 / Tailwind CSS 4 / TypeScript 5.6

---

## 1. 技术栈

- **Nuxt 3.14** (srcDir="app") + Vue 3.5 + TypeScript 5.6
- **Pinia 2.2**（Setup Store 模式）
- **Tailwind CSS 4**（通过 @tailwindcss/vite 插件）
- **oklch 色系**：Sage Green / Warm Amber / Terracotta
- **不使用 Element Plus 或其他 UI 框架**，纯 Tailwind 手写

---

## 2. 架构决策

| 决策 | 方案 | 说明 |
|------|------|------|
| **独立布局** | `layouts/admin.vue` | 240px 可折叠侧边栏 + 顶部面包屑/用户菜单 + 内容区 |
| **路由守卫** | `middleware/auth.ts` | 检查登录状态，未登录跳转 `/login` |
| **API 封装** | `composables/useAdminApi.ts` | 基于 `$fetch.create`，baseURL `localhost:8000/api/admin/v1`，自动 Bearer token 注入，20 个具名导出函数 |
| **状态管理** | `stores/admin.ts` | 侧边栏折叠状态 + 仪表盘数据 |

---

## 3. 设计体系

- **工业精准风格**（industrial precision）
- **状态驱动色彩**：订单状态机 8 种色码映射（amber / blue / indigo / teal / cyan / green / slate / red）
- **定价层级可视化**：四级优先级缩进 + 颜色深浅
- **促销类型色码**：满减=amber / 优惠券=blue / 会员价=purple
- **字体**：延续项目现有字体体系

---

## 4. 公共组件

| 组件 | 文件 | 职责 |
|------|------|------|
| AdminSidebar | `components/admin/AdminSidebar.vue` | 7 项菜单侧边栏，SVG inline 图标，NuxtLink 导航，折叠支持 |
| StatCard | `components/admin/StatCard.vue` | 统计卡片：标题/数值/趋势箭头，oklch 浅色底 |
| DataTable | `components/admin/DataTable.vue` | 通用表格：排序/多选 checkbox/loading 骨架/空状态/分页器 |
| StatusBadge | `components/admin/StatusBadge.vue` | 订单状态 8 种色码，圆点+文字 |
| OrderDetailPanel | `components/admin/OrderDetailPanel.vue` | 订单行内展开：商品清单 + 地址 + 7 步状态时间线 + 物流信息 |
| ChatStatusBadge | `components/admin/ChatStatusBadge.vue` | 客服状态 5 种色码 |

---

## 5. 页面清单

| 路由 | 文件 | 核心功能 |
|------|------|----------|
| `/admin` | `pages/admin/index.vue` | 仪表盘：4 统计卡片 + 最近 10 订单 + 待处理提醒 |
| `/admin/products` | `pages/admin/products.vue` | 商品 CRUD + AI 探针自动创建 + 批量操作 + Drawer 表单 |
| `/admin/orders` | `pages/admin/orders.vue` | 8 状态筛选标签栏 + 审核/采购流程 + 行展开详情 + 状态时间线 |
| `/admin/suppliers` | `pages/admin/suppliers.vue` | 供应商管理 + API 配置 + SKU 映射双栏弹窗 |
| `/admin/pricing` | `pages/admin/pricing.vue` | 3 Tab：全局公式/区域定价(拖拽排序)/促销管理 + 四级优先级说明 |
| `/admin/chat-requests` | `pages/admin/chat-requests.vue` | 左列表右对话主从视图 + 人工接管 |
| `/admin/settings` | `pages/admin/settings.vue` | 4 分组：MCP Key/角色权限/系统参数/通知设置 |

---

## 6. 交互模式

- **防抖搜索**：300ms setTimeout 防抖
- **表单弹窗**：Drawer 右侧滑入（slide-in-right）/ Modal 居中缩放（scale-in），均带 backdrop
- **行展开**：max-height transition 动画
- **批量操作**：多选后滑入操作栏，显示选中计数
- **Toggle 开关**：纯 CSS peer-checked 实现
- **状态筛选标签**：pill 多选模式，状态色填充/空心切换
- **加载态**：骨架屏 skeleton screen 代替 spinner

---

## 7. 已知 TODO

| 项目 | 状态 | 说明 |
|------|------|------|
| 商品图片上传 | 占位 | 当前为占位，后续对接 MinIO |
| 供应商 SKU 映射 | Mock | 暂用 mock 数据，待对接真实供应商 API |
| 角色权限严格检查 | 占位 | 当前已登录即可，后续收紧为三角色 RBAC |
| 日期范围筛选器 | 可升级 | 当前为原生 date input，可升级为日期选择组件 |

*（内容由AI生成，仅供参考）*
*（内容由AI生成，仅供参考）*
