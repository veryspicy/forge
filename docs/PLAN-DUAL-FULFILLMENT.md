---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 14f48488fead00d28e11c31f9845685c_6015233fad0711f1b128525400f8a581
    ReservedCode1: aCwYGOKq/QEHR3E6Z/KG6emZ+j3t68QmHxWIfZAQjp79PPjAR1GDMZxWx/zZfI5bDeUdZuxTIbIeHNYcmRdgSnNO7cpfYMktC9cbPr5A0u8kMBiSD9dsCzhwbjEm4RjfquZSUsO3UoQh9GHhAIe27U1Rx6aKnVjIckAWZAmCDOnEFWGmQeOso/v4fSo=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 14f48488fead00d28e11c31f9845685c_6015233fad0711f1b128525400f8a581
    ReservedCode2: aCwYGOKq/QEHR3E6Z/KG6emZ+j3t68QmHxWIfZAQjp79PPjAR1GDMZxWx/zZfI5bDeUdZuxTIbIeHNYcmRdgSnNO7cpfYMktC9cbPr5A0u8kMBiSD9dsCzhwbjEm4RjfquZSUsO3UoQh9GHhAIe27U1Rx6aKnVjIckAWZAmCDOnEFWGmQeOso/v4fSo=
---

# PLAN：Shop 双模式履约（自采购 / 一件代发）改造方案

> 状态：**已定稿待实施**（决策方向经用户确认「按建议来」）
> 分支：`feature/admin-order-management`（挂起分支上继续演进，不单独从 dev 另开分支）
> 关联文档：`docs/DEV-RULES.md`（§1 版本管理、§13 质量门槛、§14 数据安全、§19 方案对标评审）

---

## 1. 背景

Forge Shop 需同时支持两种履约来源：

| 模式 | 说明 | 库存行为 |
|------|------|----------|
| `self`（自采购/备货） | 商品由本地仓备货，下单即扣本地库存 | 下单校验 + 扣减 |
| `dropship`（一件代发） | 商品由供应商直发，本地不备货 | 跳过库存校验，下单不扣减 |

### 1.1 现存问题（已定位）

1. **采购被错误塞进订单主状态机**：`admin_procure_order` 将 `order.status` 置为 `procuring`，而 `mark_shipped` 只接受 `pending/confirmed/processing` —— 订单一旦进入 `procuring` 便无法发货，且无「撤销采购」入口，只能退款或改库（`order_repo.py:492-522`、`:435-459`）。
2. **无履约模式字段**：`products` 仅有 `supplier_id`（migration 0013 加列 / 0016 补外键），无法区分商品来源，`create_order` 对**所有**商品无条件校验并扣减库存，代发商品库存为 0 时下单直接被拒（`order_repo.py:307-318`）。
3. **order_items 无履约快照**：只记 `product_id/name/sku/price/quantity/image`，商品后续改履约方式会导致历史订单归属漂移（`models.py:653-665`）。
4. **无待采购视图**：代发/自采购订单无法按供应商聚合出采购清单。

### 1.2 行业对标（DEV-RULES §19 强制）

| 维度 | 行业主流（Shopify / 聚水潭 / 旺店通） | 本方案 |
|------|--------------------------------------|--------|
| 采购载体 | 独立单据（Shopify PO、聚水潭采购单+采购入库单、旺店通采购单据），**不写订单主状态** | 第一期做「待采购清单」（按供应商聚合 + 导出），不建 PO 实体 |
| 订单主状态 | 只管履约：`pending→confirmed→processing→shipped→delivered` | 沿用，**移除 `procuring` 写入路径** |
| 发货粒度 | 以包裹（fulfillment/shipment）为单位，支持部分发货 | `shipments` 表已具备（`supplier_id/carrier/tracking_number/status/events`），直接复用 |
| 代发库存 | 不占本地库存 | `create_order` 按 mode 分叉，dropship 跳过校验与扣减 |
| 混合订单 | 不拆单，行级记录来源 | 订单行打履约快照，不拆单 |

---

## 2. 决策定稿

| # | 决策 | 结论 |
|---|------|------|
| D1 | 履约模式载体 | `products` 新增显式字段 `fulfillment_mode ∈ {self, dropship}`，默认 `self`；`dropship` 强制关联 `supplier_id` |
| D2 | 混合订单 | **不拆单**；在 `order_items` 打履约快照（mode + supplier），发货以 `shipments` 为单位，订单支持部分发货语义 |
| D3 | 代发库存 | 下单时 `dropship` 行跳过库存校验与扣减；取消/退款时同样不回补 |
| D4 | 采购实现 | **不建 PO 实体**。`procure` 端点降级为「仅写 `procurement_info` 标记 + 不迁移主状态」；新增「待采购清单」（按供应商聚合 + CSV 导出） |
| D5 | 历史数据兼容 | 已存在 `procuring/procure_failed` 订单：保留其可发货 / 可退款能力（守卫集合保留），但**不再产生新的写入路径** |

---

## 3. 数据层变更

### 3.1 migration `0033_products_fulfillment_mode`（新建）

| 表 / 列 | 变更 | 说明 |
|---------|------|------|
| `products.fulfillment_mode` | `VARCHAR(20) NOT NULL DEFAULT 'self'` + CHECK `in ('self','dropship')` + 索引 | 老商品自动落 `self` |
| `order_items.fulfillment_mode` | `VARCHAR(20) NULL` | 履约快照；历史行留空按 `self` 解释 |
| `order_items.supplier_id` | `UUID NULL`（**不建 FK**，快照语义） | 供应商变更/停用不影响历史订单 |
| `order_items.supplier_sku` | `VARCHAR(255) NULL` | 采购下单时直接可用 |

回滚：`alembic downgrade -1` 删除上述列。

### 3.2 ORM 同步（`models.py`）

- `ORMProduct` 增加 `fulfillment_mode`（与 `supplier_id` 并列）
- `ORMOrderItem` 增加 `fulfillment_mode / supplier_id / supplier_sku`

---

## 4. 接口层变更

### 4.1 商品（`api/admin/v1/products.py`）

1. `ProductCreate` / `ProductUpdate` 增加 `fulfillment_mode: str | None`
2. 校验：`fulfillment_mode == 'dropship'` 时 `supplier_id` 必填（缺失返回 `VALIDATION_ERROR`）
3. 导入/导出列 `EXPORT_COLUMNS` 增加 `fulfillment_mode`（`REQUIRED_IMPORT_COLUMNS` 不变，导入默认 `self`）

### 4.2 下单（`repositories/order_repo.py`）

- `create_order` 按 `product.fulfillment_mode` 分叉：
  - `self`：维持现状（校验 `inventory >= qty` 并扣减）
  - `dropship`：仅校验商品 `status == active`，**跳过库存校验与扣减**
- 写入 `ORMOrderItem` 时带上 `fulfillment_mode / supplier_id / supplier_sku` 快照
- `_restore_inventory`：仅回补 `self` 行（`fulfillment_mode != 'dropship'`）

### 4.3 订单（`api/admin/v1/orders.py`）

1. `AdminShipPackage` 增加可选 `supplier_id`；`_new_shipment` 用它填充 `shipments.supplier_id`（缺省保持 `"MANUAL"`）
2. `procure` 端点：改为只写 `procurement_info`（`status: "requested"`），**不再改 `order.status`**；订单停留在 `processing`，随时可发货
3. 新增 `GET /api/admin/v1/orders/purchase-list`：聚合「含 dropship 行且未发货」的订单，按 `supplier_id` 分组返回（订单号、SKU、数量、地址摘要）
4. 新增 `GET /api/admin/v1/orders/purchase-list/export`：CSV 导出（复用现有 export 的 StreamingResponse 写法）

---

## 5. 前端变更（admin）

| 文件 | 变更 |
|------|------|
| `admin/src/views/products-new/index.vue` | 表单增加「履约方式」单选（自采购/一件代发）+「供应商」下拉（`GET /suppliers` 取 `id/name`），选代发时供应商必填 |
| `admin/src/views/products-detail/index.vue` | 同上（编辑态回填 `fulfillment_mode`） |
| `admin/src/views/orders-detail/index.vue` | 订单行展示履约方式徽标 + 供应商；发货弹窗每包裹可选供应商；`REFUNDABLE_STATUSES` 保留历史 `procuring` 兼容 |
| `admin/src/views/orders/index.vue` | 增加「待采购清单」入口（跳转/抽屉 + 导出按钮） |
| `admin/src/locales/langs/zh-cn.ts` / `en-us.ts` | 补齐 `fulfillmentMode` / `dropship` / `purchaseList` 等文案（复用已预留的 `supplierId`/`supplierSku`） |

> admin 无 HMR：源码变更后必须 `build --no-cache` + `up -d --force-recreate`（DEV-RULES §3.2）。

---

## 6. 实施顺序

```
P1 数据层   ：0033 migration + models.py + 容器内执行 + 备份
P2 后端逻辑 ：products 校验 → create_order 分叉 → _restore_inventory → procure 降级 → purchase-list/export
P3 前端     ：商品表单 → 订单详情 → 待采购清单 → i18n → 重建 admin
P4 验证     ：质量门槛（ruff/format/mypy；admin typecheck/lint）+ e2e + 需求逐条核对
```

每阶段独立提交（Conventional Commits），互不混合。

---

## 7. 验证清单（端到端，DEV-RULES §10）

| # | 验证点 | 手段 | 期望 |
|---|--------|------|------|
| 1 | 代发商品下单 | 调下单接口，库存 0 的 dropship 商品 | 下单成功，商品 `inventory` 不变 |
| 2 | 自采购商品下单 | 同上，self 商品 | 库存校验生效并扣减 |
| 3 | 混合订单 | 同时含 self + dropship 行 | 下单成功，行快照 mode/supplier 正确 |
| 4 | 代发订单发货 | `POST /orders/{no}/ship` | 状态 `processing→shipped`，`shipments.supplier_id` = 供应商 |
| 5 | 采购不卡发货 | `POST /orders/{no}/procure` 后立即发货 | 主状态仍为 `processing`，发货成功（回归原卡死 bug） |
| 6 | 待采购清单 | `GET /orders/purchase-list` | 按供应商聚合，仅含未发货 dropship 行 |
| 7 | 导出 | `GET /orders/purchase-list/export` | CSV 可下载，字段与清单一致 |
| 8 | 代发订单取消/退款 | 后台取消 | 库存不回补（dropship 行） |
| 9 | 历史 procuring 订单 | 对历史数据执行发货/退款 | 仍可正常流转（兼容路径有效） |
| 10 | 商品表单 | admin 页面新建/编辑代发商品 | 保存成功，列表回显履约方式 |

---

## 8. 明确不做（本期边界）

1. **不建 `procurement_orders` 独立表 / PO 实体**（对单人开发过度设计，待采购清单已覆盖第一期诉求）
2. **不拆单**（混合订单按行承载来源）
3. **不做行级部分发货**（按包裹粒度已满足；行级拆分留待有真实业务压力时演进）
4. **不做部分退款**（维持整单退款）
5. **不接真实物流商 API**（`tracking_url` 维持 mock）

---

## 9. 风险

| 风险 | 影响 | 缓解 |
|------|------|------|
| 挂起分支继续演进导致分支过大 | 验证通过前无法合并 dev | 按 P1-P4 分阶段提交，便于回滚与 review |
| 历史 `procuring` 数据残留 | 前端/守卫集合不兼容会拒单 | D5：保留兼容读取集合，仅移除写入路径 |
| `order_items` 新增列 NULL | 统计/导出按 mode 分支时 NPE | 读取侧统一 `mode or 'self'` 兜底 |
| admin 重建遗漏 | 页面看不到新字段 | §11.2 容器产物 grep 核对 `fulfillment_mode` |
*（内容由AI生成，仅供参考）*
