---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 14f48488fead00d28e11c31f9845685c_95781cfbae7811f1b128525400f8a581
    ReservedCode1: uz0LLezIafuADR/lq2yaHOOTlxNqPqUNJY69+5+GYQslMA4gHZMePb1O8cQmUc81taBcuWorbungc4FS7S5EUIBaYMLfizT/tTk7DDY0w5VKXihuEu+S8JgWjKRR/+NvhcZp2B1uezkWe+KZAqwLksb5roBMTev9hh+LIOZ5eZKCOTy2qLd/u7tMzWI=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 14f48488fead00d28e11c31f9845685c_95781cfbae7811f1b128525400f8a581
    ReservedCode2: uz0LLezIafuADR/lq2yaHOOTlxNqPqUNJY69+5+GYQslMA4gHZMePb1O8cQmUc81taBcuWorbungc4FS7S5EUIBaYMLfizT/tTk7DDY0w5VKXihuEu+S8JgWjKRR/+NvhcZp2B1uezkWe+KZAqwLksb5roBMTev9hh+LIOZ5eZKCOTy2qLd/u7tMzWI=
---

# 售后（退货/退款）与物流能力建设规划（一期）

> 版本：v1（评审中，未定稿前不进入实施）
> 日期：2026-09-12
> 关联：`PLAN-DUAL-FULFILLMENT.md`、`DEV-RULES.md`（§1 版本管理、§5 执行前计划、§14 数据与发布安全、§19 方案对标评审）
> 覆盖范围：订单管理 9 项问题清单全部（P0/P1/P2），其中第 8 项 C 端退货通道与第 7 项物流供应商 API 为一期新增能力主体

---

## 0. 结论先行

1. **方向成立**：退货/退款按"业务动作驱动状态 + 资金动作独立"建模，与 Shopify / Medusa / Saleor / Sylius 主线一致；Forge 已有的行级退款（`order_items.refunded_quantity` + `orders.refunded_amount/refunds`）正是该范式的基础，本期只需补齐"退货申请单"这一业务载体。
2. **一期可交付**：9 项问题全部覆盖，拆 3 个批次（Batch 1 缺陷修复 → Batch 2 退货退款通道 → Batch 3 物流供应商 API），每批独立分支、独立验证，互不阻塞。
3. **关键取舍**：一期**不做**自动网关原路退款（人工确认 + 凭证号），**不做**换货/维修的实际履约流转（字段预留）；物流一期做"表 + 适配器 + 手动兜底"，轨迹接第三方聚合服务，自动取号在渠道配置就绪后开启。
4. **待决策项 4 条**（见 §10），需老板拍板后定稿实施。

---

## 1. 需求清单与批次映射

| # | 问题描述 | 层级 | 根因（已核实） | 归属批次 |
|---|---|---|---|---|
| 1 | 未登录加购无登录触发 | P0 | `portal-web/app/stores/cart.ts` 的 `addItem` 吞掉 401，未跳登录 | Batch 1 |
| 2 | 未付款订单取消时显示退款选项 | P0 | admin 取消弹窗未判断 `payment_status`，无条件显示退款勾选 | Batch 1 |
| 3 | 已取消订单仍显示"去支付" | P0 | C 端订单页 `canPay` 未排除 `cancelled` | Batch 1 |
| 4 | 退款订单无法删除 + 删除无二次确认 | P1 | `canDelete` 仅允许 `delivered/cancelled`；删除走系统默认 confirm | Batch 1 |
| 5 | 拒单后点退款失败且无原因（应自动退全款并展示流向） | P0（后端）/ P1（前端） | 拒单置 `cancelled`，被 `_REFUND_BLOCKED_ORDER_STATUSES` 拦截；错误未透传前端 | Batch 1 |
| 6 | 卡号显示优化（分组/脱敏） | P1 | 前端直接展示原始串 | Batch 1 |
| 7 | 物流供应商 API 管理 + 自动取号 | P2 | 无物流供应商模型与适配器 | Batch 3 |
| 8 | C 端缺退货申请通道；admin 单方退款后 C 端仍显"已发货" | P2 | 无 return 实体与 C 端入口；退款未回推 C 端状态 | Batch 2 |
| 9 | admin 状态值仍显英文 | P0 | `admin/src/locales/langs/zh-cn.ts` 缺订单状态值映射 | Batch 1 |

批次划分：

- **Batch 1 — 订单体验缺陷修复**：问题 1/2/3/4/5/6/9（无 migration，纯前后端逻辑与文案）
- **Batch 2 — 退货退款通道（C 端 + admin）**：问题 8（含 migration `0036`）
- **Batch 3 — 物流供应商 API 管理**：问题 7（含 migration `0037`）

---

## 2. 行业对标（§19.2 六步之一：先锚定权威基准）

调研覆盖 Shopify（行业基准）、Medusa v2、Saleor、Vendure、Sylius、django-oscar，来源见 §9。

### 2.1 横向对比表

| 维度 | Shopify（基准） | Medusa | Saleor | Vendure | Sylius | django-oscar | Forge 本期取舍 |
|---|---|---|---|---|---|---|---|
| 退货实体 | Return（独立对象） | Return（独立） | 无独立实体，挂 fulfillment | 核心无，插件/企业版自建 | Plus / RMA 插件 `OrderReturn` | 无，事件模型 | 独立 `return_requests` |
| 退款实体 | Refund（独立） | `OrderTransaction` | `OrderGrantedRefund` | `Refund`（状态机） | `CreditMemo` + `RefundPayment` | `PaymentEvent` | 沿用 `orders.refunds` JSONB 流水（含 return_id） |
| 换货/索赔 | `exchangeLineItem` | Exchange + Claim | `replaceFulfillment` + draft 订单 | 企业版 | `replacement` / `repair` | 自建 | 字段预留，不做流转 |
| 退货与退款解耦 | 严格解耦 | 解耦 | 解耦 | 解耦 | 模块独立 | 事件分离 | 严格解耦（收货 ≠ 退款） |
| 部分退货 | 行级 | 行级 + 良品/坏品 | 行级 + replace | 插件 | 行级 | 行级事件 | 行级，良品/坏品分离 |
| 退货状态机 | REQUESTED→OPEN→CLOSED | requested→received→canceled | 订单级 RETURNED | 插件自建 | draft→new→completed | 无内置 | 9 态（见 §5） |
| 幂等 | API 约束 | `idempotency_key` + 恢复点 | 单路径退款约束 | 状态机 | 命令去重 | 自实现 | `idempotency_key` + 唯一约束 |
| 超时关闭 | 无内置 | 无内置 | 无内置 | 无内置 | 无内置 | 无 | 自实现 `auto_close_at` + 定时任务 |
| C 端自助 | Customer Accounts | Storefront API | 无（需自建） | Shop GraphQL | 账户区 | 需自建 | 新增 C 端申请入口 |
| 凭证/照片 | ReverseDelivery | `shipping_data` | reverseDelivery | 插件附件 | PDF 退货单 | 需自建 | `evidence` JSONB |
| 退货运费承担 | 可选退 | 单独处理 | 单独处理 | 自定义 | RMA 收集账户 | 需自建 | 申请单字段 + 手续费率 |

### 2.2 借鉴对象与理由

- **骨架抄 Medusa**：Return / Refund 双实体并列、行级 `received_quantity` 与 `damaged_quantity` 分离（良品回库、坏品不回库），状态机简单可落地。
- **C 端语义抄 Shopify**：客户自助发起（`orderRequestReturn`）→ 后台审批（approve/decline）→ 收货 → 打款，且退货动作本身不触发退款，退款必须显式触发。
- **凭证思路抄 Sylius**：每次退款生成可追溯的凭证号（`credit_memo_no`），与资金流水一一对应，便于对账与 C 端展示"退款流向"。
- **状态时机抄 Vendure**：退款走独立状态机（pending → settled → failed），失败可重试但禁止重复打款。

---

## 3. 对标评审结论（§19.3：亮点 / 差距 / 合理性）

### 3.1 已在行业主线上的亮点（保留，不折腾）

| 项 | 现状 | 行业对照 |
|---|---|---|
| 行级退款 | `order_items.refunded_quantity` + 订单级累计 `refunded_amount` | 等同 Saleor per-line refund、Sylius `OrderItemUnitRefund` |
| 取消与退款收敛单入口 | 取消带 `refund` 参数自动退全款 | 优于 Vendure（取消与退款分离易漏） |
| 税按行分摊 | 退款税按退款行小计占 `subtotal` 分摊 | 与 Saleor / Shopify 税处理语义一致 |
| 履约与资金分离 | 采购状态落商品行，不动订单主状态 | 与 Oscar 事件模型一致 |

### 3.2 差距与修正项

| # | 差距 | 行业做法 | 本期修正 |
|---|---|---|---|
| G1 | 无退货业务实体，客户无处发起 | Medusa `Return` / Shopify `Return` | 新增 `return_requests` + `return_items` |
| G2 | 退款只有资金流水，无业务上下文 | Shopify refund 必须挂 return | `refunds` 流水项强制携带 `return_id`（仅退款场景可为空并标注来源） |
| G3 | 拒单（拒收）无自动退款路径 | Shopify 可对已拒收订单直接 refund | 拒单语义改为"进入退货流程"，自动生成 `refund_only` 申请并全款退 |
| G4 | 退款不推进/回推 C 端状态 | Shopify webhook `refunds/create` 推 C 端 | admin 退款成功后回写 C 端订单展示状态 |
| G5 | 无退款幂等保护 | Medusa `idempotency_key` + 恢复点 | `idempotency_key` 唯一约束 + 退款金额上限校验（≤ `refundable_amount`） |
| G6 | 无退货申请超时关闭 | 各系统同样缺失（需自建） | `auto_close_at` + 定时任务置 `auto_closed` |
| G7 | 无退货物流单号回填与凭证 | Shopify `reverseDelivery`、Sylius PDF | `return_carrier/return_tracking_no` + `evidence` JSONB |
| G8 | 物流供应商无模型，取号靠手填 | 行业用 carrier adapter（quote/label/track） | 新增 provider/channel 表 + `ShippingAdapter` 接口 + 手动兜底 |

### 3.3 合理性评估（主动简化及演进路径）

| 简化项 | 理由 | 演进路径 |
|---|---|---|
| 退款不新建独立表，沿用 `orders.refunds` JSONB | 现有 admin 退款链路已按此实现，一期避免双写与数据迁移风险 | 退款笔数/对账需求上来后抽 `refunds` 表，JSONB 作为历史兼容 |
| 不做网关自动原路退款 | 各支付渠道退款接口与密钥就绪度未知，贸然自动化风险高 | 接入渠道退款 API 后，`refund_method=original_payment` 走自动，人工降级为兜底 |
| 不做换货/维修流转 | 一期 C 端诉求集中在退货退款/仅退款，换货涉及新订单生成与差价结算 | `resolution` 枚举预留 `exchange/repair`，二期补履约链路 |
| 物流先做"表 + 适配器 + 手动"，轨迹后置 | 自动取号依赖承运商账号与面单接口，接入周期不可控 | 适配器先落地，凭证就绪后只增渠道实现，不改上层 |

---

## 4. 数据模型设计

### 4.1 `return_requests`（退货/退款申请主表，migration 0036）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | UUID PK | |
| rma_no | String(32) UNIQUE | RMA 编号，格式 `RMA-YYYYMMDD-XXXX` |
| order_id / order_number | UUID FK / String(50) | 关联订单，冗余单号便于列表与对账 |
| user_id | UUID | 申请人 |
| created_by | String(16) | `customer` / `admin`（admin 拒单自动生成时为 admin） |
| type | String(16) | `return_refund`（已发货退货退款）/ `refund_only`（未发货仅退款、拒单） |
| resolution | String(16) | `refund`（一期） / `exchange` / `repair`（预留） |
| status | String(20) | 见 §5 状态机 |
| reason_code / reason_note | String(32) / Text | 结构化原因 + 补充说明 |
| customer_note / internal_note | Text | 客户备注 / 客服内部备注 |
| evidence | JSONB | 凭证图片 URL 列表 |
| return_carrier / return_tracking_no / return_shipped_at | String / DateTime | 客户回填的退货物流（问题 7 复用载体） |
| refund_amount | Numeric(12,2) | 该申请关联退款金额（分批退款时为累计） |
| refund_basis | JSONB | 退款构成明细：items / tax / shipping / restock_fee |
| refund_method | String(16) | `original_payment` / `manual` |
| credit_memo_no | String(32) | 退款凭证号（抄 Sylius） |
| idempotency_key | String(64) UNIQUE | 防重复提交 |
| auto_close_at | DateTime | 超时关闭时间（默认创建 +14 天） |
| created_at / updated_at / approved_at / received_at / refunded_at / closed_at / canceled_at | DateTime | 关键节点时间戳 |

### 4.2 `return_items`（行级明细）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | UUID PK | |
| return_id | UUID FK `return_requests.id` ON DELETE CASCADE | |
| order_item_id | UUID FK `order_items.id` | |
| quantity | Integer | 申请退货数量（校验 ≤ 已购 - 已退） |
| received_quantity | Integer | 仓库实收良品数 |
| damaged_quantity | Integer | 实收坏品数（不回库） |
| unit_refund_amount | Numeric(12,2) | 行单价快照 |
| restock | Boolean | 是否回补库存（代发行强制 false） |

### 4.3 退款记账（沿用现有结构，不新增表）

退款写入 `orders.refunds`（JSONB 数组）并累加 `orders.refunded_amount`，同时累加 `order_items.refunded_quantity`。每笔记录扩展字段：

```json
{
  "return_id": "uuid|null",
  "credit_memo_no": "CM-20260912-0001",
  "amount": 128.00,
  "items": [{"order_item_id": "...", "quantity": 1, "amount": 128.00}],
  "tax": 0.00,
  "shipping": 0.00,
  "restock": true,
  "operator": "admin",
  "payment_status_before": "paid",
  "payment_status_after": "partially_refunded",
  "created_at": "2026-09-12T10:00:00"
}
```

### 4.4 物流表（migration 0037）

**`logistics_providers`**

| 字段 | 类型 | 说明 |
|---|---|---|
| id | UUID PK | |
| code | String(64) UNIQUE | `yanwen` / `yuntu` / `17track` / `manual` |
| name | String(128) | 显示名 |
| provider_type | String(16) | `carrier`（承运商）/ `aggregator`（轨迹聚合） |
| auth_type | String(16) | `token` / `oauth2` / `apikey` / `none` |
| credentials | JSONB | 加密后的密钥（复用 `supplier_credentials` 同款加密与脱敏约定） |
| config | JSONB | 超时、重试、面单格式等 |
| enabled / priority | Boolean / Integer | 启停与优先级 |
| created_at / updated_at | DateTime | |

**`logistics_channels`**：`id / provider_id FK / code / name / countries(JSONB) / max_weight / size_limit(JSONB) / price_rule(JSONB) / enabled`

**`shipments` 扩列**：`provider_id` / `channel_id` / `label_url` / `tracking_status` / `last_tracked_at`（轨迹事件沿用现有 `events` JSONB）

**`shipping_quote_logs`**（可选，P2）：记录 `quote/create_shipment/track` 调用入参与响应，便于排障。

### 4.5 ORM 契约约束（§13.5.6）

- 所有 `DateTime` 列显式赋值 `datetime.now()`（naive），禁止依赖数据库默认值参与业务判断；
- `NOT NULL` 数值列（`refund_amount` 等）在 Python 侧显式给初值，禁止留 `None`。

---

## 5. 状态机与业务规则

### 5.1 退货申请状态机

```
customer 发起 (type=return_refund | refund_only)
      │
      ▼
  requested ──admin approve──► approved ──┬─► received ──► refunding ──► refunded ──► closed
      │                                   │      （仓库验货：良品/坏品、是否回库）
      │                                   └─(refund_only)─────────────────► refunded ──► closed
      ├──admin reject──► rejected
      ├──customer cancel──► canceled
      └──超时 auto_close_at──► auto_closed
```

| 状态 | 触发动作 | 副作用 |
|---|---|---|
| `requested` | 客户提交 / admin 拒单自动生成 | 写申请单；不冻结资金、不改库存 |
| `approved` | admin 审核通过 | 通知客户寄回（`return_refund`）；`refund_only` 可直接进退款 |
| `received` | 仓库验货 | 写 `received_quantity/damaged_quantity`；`restock=true` 且非代发行 → 回补库存；**不改资金** |
| `refunding` | admin 发起退款 | 写 `orders.refunds` + `refunded_amount` + `order_items.refunded_quantity`；生成 `credit_memo_no` |
| `refunded` | 资金流水落库成功 | 回推 C 端订单状态；同步 `payment_status`（paid → partially_refunded / refunded） |
| `closed` | 退款完成 / 无货可退 | 终态 |
| `rejected` / `canceled` / `auto_closed` | 审批驳回 / 客户撤销 / 超时 | 终态；不可回退 |

### 5.2 硬规则

1. **入库与打款解耦**：`received` 只动库存与状态；退款必须由 `refund` 动作显式触发，禁止在收货环节直接改 `payment_status`。
2. **退款幂等**：`idempotency_key` 唯一约束；退款前校验 `退款金额 ≤ refundable_amount`；同一申请同一时刻只允许一笔 `refunding`。
3. **拒单语义修正（问题 5）**：admin 拒收/拒单不再直接置订单 `cancelled`，而是置为售后流程入口：已付款 → 自动生成 `refund_only` 申请并退全款；未付款 → 直接取消。退款失败必须把渠道错误原文透传前端（禁止吞错）。
4. **C 端状态一致性（问题 8）**：退款成功后，C 端订单展示状态由 `退款中/已退款` 覆盖"已发货"，以订单级 `payment_status` + 退款流水为准，`status` 仅表达履约进度。
5. **超时关闭**：定时任务（复用现有调度能力）扫描 `requested/approved` 且超 `auto_close_at` 的申请 → `auto_closed`，写内部备注。
6. **不可逆约束**：`received` 之后客户不可撤销；已关闭申请不可再退款。
7. **代发不回库**：`order_items.fulfillment_mode = dropship` 的行，退货退款时不回补库存（延续双履约基线）。
8. **运费策略**：`return_refund` 默认退商品行小计与对应税，原运费默认不退；是否退运费由申请单 `refund_basis.shipping` 显式标记，admin 可勾选。

---

## 6. 接口设计

### 6.1 C 端（`backend/src/forge/api/v1/orders.py` 扩展，或新增 `api/v1/returns.py` 并挂 `/orders` 前缀）

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/orders/{order_number}/returns` | 创建申请（type/items/reason/note/evidence/idempotency_key） |
| GET | `/orders/{order_number}/returns` | 我的申请列表（含状态与退款金额） |
| GET | `/orders/{order_number}/returns/{return_id}` | 申请详情 + 退款流向 |
| POST | `/orders/{order_number}/returns/{return_id}/cancel` | 客户撤销（仅 `requested`） |
| POST | `/orders/{order_number}/returns/{return_id}/ship` | 回填退货物流（carrier/tracking_no） |

### 6.2 admin（新增 `backend/src/forge/api/admin/v1/returns.py` + `/admin/logistics/*`）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/admin/returns` | 列表（status/keyword/日期筛选、分页、导出可选） |
| GET | `/admin/returns/{id}` | 详情（订单、行级明细、凭证、时间线） |
| POST | `/admin/returns/{id}/approve` | 审核通过 |
| POST | `/admin/returns/{id}/reject` | 驳回（原因必填） |
| POST | `/admin/returns/{id}/receive` | 验货入库（良品/坏品数量、是否回库） |
| POST | `/admin/returns/{id}/refund` | 发起退款（金额、是否退运费、凭证号） |
| GET / POST / PUT | `/admin/logistics/providers` | 物流供应商 CRUD 与密钥配置 |
| GET / POST / PUT | `/admin/logistics/channels` | 渠道 CRUD（国家、限重、价格规则） |
| POST | `/admin/orders/{order_number}/shipment/auto-create` | 自动取号出单（渠道就绪时） |
| GET | `/admin/orders/{order_number}/tracking` | 轨迹查询（聚合服务 / 手动单号） |

### 6.3 适配器接口（`infrastructure/logistics/`）

```python
class ShippingAdapter(Protocol):
    def quote(self, req: QuoteRequest) -> QuoteResult: ...
    def create_shipment(self, req: CreateShipmentRequest) -> ShipmentResult: ...
    def label(self, shipment_id: str) -> LabelResult: ...
    def track(self, tracking_no: str, carrier: str) -> list[TrackEvent]: ...
    def cancel(self, shipment_id: str) -> bool: ...
```

实现顺序：`ManualAdapter`（手输单号，永远可用） → `AggregatorAdapter`（17TRACK/AfterShip 轨迹） → 承运商直连（燕文/云途，凭证就绪后）。

---

## 7. 前端改造点

### 7.1 admin（`admin/`，vben）

| 文件 | 改造 |
|---|---|
| `src/views/orders-detail/index.vue` | 取消弹窗按 `payment_status` 显隐退款选项（问题 2）；退款入口文案与流向展示（问题 5）；新增退货申请审核区（Batch 2） |
| `src/views/orders/index.vue` | 删除按钮覆盖退款单、自定义二次确认（问题 4）；卡号分组显示（问题 6）；状态中文（问题 9 联动） |
| `src/locales/langs/zh-cn.ts` / `en-us.ts` | 补订单/支付/退款/退货状态值映射（问题 9） |
| `src/service/api/orders.ts`（新增或扩展） | 退货与物流接口封装 |
| `src/views/logistics/*`（Batch 3 新增） | 物流供应商与渠道管理页 |

### 7.2 C 端（`portal-web/`）

| 文件 | 改造 |
|---|---|
| `app/stores/cart.ts` | 401 触发登录跳转（问题 1） |
| `app/pages/orders/[id].vue` | `canPay` 排除 `cancelled`（问题 3）；新增"申请退货/退款"入口与状态展示（问题 8） |
| `app/pages/orders/index.vue` | 列表状态与退款标识（问题 8） |
| `app/components/OrderStatusBadge.vue` | 补退款/退货状态样式 |
| `app/pages/orders/returns/*`（Batch 2 新增） | 申请表单、详情与退款流向 |

---

## 8. 分批实施计划

> 分支前置：按 §1.1，开工前先确认分支策略（见 §10 待决策 D1）。

### Batch 1 — 订单体验缺陷修复（无 migration）

| 项 | 文件 | 动作 |
|---|---|---|
| 1 | `portal-web/app/stores/cart.ts` | 401 → 跳登录并保留回跳地址 |
| 2 | `admin/src/views/orders-detail/index.vue` | 取消弹窗按 `payment_status` 显隐退款项 |
| 3 | `portal-web/app/pages/orders/[id].vue` | `canPay` 排除 `cancelled` |
| 4 | `admin/src/views/orders/index.vue`、`orders-detail/index.vue` | 退款单可删 + 自定义二次确认 |
| 5 | `backend/src/forge/api/admin/v1/orders.py`、`order_repo.py` | 拒单走自动全款退，错误原文透传；前端展示退款流向 |
| 6 | `admin/src/views/orders/index.vue` | 卡号分组/脱敏显示 |
| 9 | `admin/src/locales/langs/zh-cn.ts`（+`en-us.ts`） | 状态值中文化映射 |

验收：逐项手动复现原缺陷 → 修复后回归（含未登录加购、未付款取消、已取消去支付、拒单退款、状态文案）；后端过 ruff/mypy，前端过 lint/typecheck；Admin 端 `build --no-cache` + 容器重建（无 HMR）。

### Batch 2 — 退货退款通道（C 端 + admin，migration 0036）

1. ORM 三表（`return_requests` / `return_items`）+ repository + 领域规则（幂等、金额上限、行级数量校验）
2. C 端 5 个接口 + admin 7 个接口（含审批/验货/退款）
3. 退款写入扩展 `orders.refunds`（携带 `return_id` / `credit_memo_no`）并回推 C 端状态
4. 超时关闭定时任务
5. 前端：C 端申请与详情页、admin 售后工作台（列表 + 详情 + 审核动作）
6. 端到端验证：下单 → 支付 → 发货 → C 端申请 → admin 审批 → 验货 → 退款 → C 端展示

### Batch 3 — 物流供应商 API 管理（migration 0037）

1. provider/channel 表 + `shipments` 扩列
2. `ShippingAdapter` 协议 + `ManualAdapter` 兜底 + provider 注册表
3. admin 物流管理页（列表、密钥配置脱敏展示、渠道 CRUD、连通性测试按钮）
4. 手动填单号全链路（admin 发货页）+ 轨迹查询接入聚合服务（凭证就绪后开启自动取号）

---

## 9. 验证与交付

- **质量门槛**：backend `ruff` + `mypy`；前端 `lint` + `typecheck`（§13.1）
- **migration**：容器内执行 `podman exec forge-backend alembic upgrade head`，变更前备份（§14.1）
- **端到端**：每批部署后按 §10 执行 API 链路 + 数据链路 + 需求逐条核对，禁止凭"源码存在"宣布完成
- **交付声明**：每批完成以 `yyb-product` 声明产出物；合并 dev 需老板明确验证通过（§1.3），并经 `merge-dev.ps1` 门禁（§1.5）

## 10. 待决策项（定稿前需老板拍板）

| # | 决策点 | 建议方案 | 备选 |
|---|---|---|---|
| D1 | Batch 1 的分支基线 | 第 2/4/5 项改动与挂起分支 `feature/admin-order-management` 同文件同区域，建议在该分支上继续开发，验证通过后一并合 dev；Batch 2/3 从 dev 另开新分支 | 先把挂起分支合 dev，再从 dev 切 Batch 1 分支 |
| D2 | 退货申请超时关闭时长 | 14 天 | 7 天 / 30 天 / 不自动关闭 |
| D3 | 退款方式一期范围 | 人工确认退款 + 凭证号（`credit_memo_no`），不接网关自动原路退 | 接入网关自动退款（依赖渠道 API 就绪度） |
| D4 | 物流轨迹服务选型 | 先落适配器 + 手动单号；轨迹接 17TRACK（需其 API Key，可由老板提供） | AfterShip / 暂不接轨迹 |

---

## 11. 来源索引

- Shopify：https://shopify.dev/docs/apps/build/orders-fulfillment/returns-apps/build-return-management 、https://shopify.dev/docs/apps/build/orders-fulfillment/returns-apps/migrate-to-return-processing 、https://shopify-dev.shopifycloud.com/docs/api/admin-graphql/2026-01/queries/return
- Medusa：https://docs.medusajs.com/modules/orders/returns 、https://docs.medusajs.com/resources/commerce-modules/order/return 、https://docs.medusajs.com/modules/orders/claims
- Saleor：https://docs.saleor.io/developer/order/order-fulfillment 、https://saleor.io/blog/refund-reasons-returns-per-line 、https://docs.saleor.io/api-reference/orders/enums/order-granted-refund-status-enum
- Vendure：https://docs.vendure.io/current/core/reference/typescript-api/payment/refund-process 、https://deepwiki.com/vendurehq/vendure/4.1.2-payment-processing
- Sylius：https://github.com/mad-coders/sylius-rma-plugin 、https://github.com/Sylius/RefundPlugin 、https://sylius.com/blog/sylius-plus-module-overview-returns-management-rma
- django-oscar：https://django-oscar.readthedocs.io/en/3.0.0/howto/how_to_set_up_order_processing.html 、https://deepwiki.com/django-oscar/django-oscar/6.3-shipping-and-payment-events
*（内容由AI生成，仅供参考）*
