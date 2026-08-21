---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 14f48488fead00d28e11c31f9845685c_b83187279d0c11f19155525400826444
    ReservedCode1: 7wvY4pPH415symW1cdVKL2XnuqopREqtLtBxJ4D1CKS/EuY7mCp+FjhOopu7S5Ti915UGq02oZNML1fhZTABrugpktJDCsJ+eDsatzEs44b+ULZLNphZ4N/Ebk3c5RBgWjE0WXYBHxlvs4GnCdRRaD7IoQNza7xkG/DIIhFify9VK76G3hpIFNml1eM=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 14f48488fead00d28e11c31f9845685c_b83187279d0c11f19155525400826444
    ReservedCode2: 7wvY4pPH415symW1cdVKL2XnuqopREqtLtBxJ4D1CKS/EuY7mCp+FjhOopu7S5Ti915UGq02oZNML1fhZTABrugpktJDCsJ+eDsatzEs44b+ULZLNphZ4N/Ebk3c5RBgWjE0WXYBHxlvs4GnCdRRaD7IoQNza7xkG/DIIhFify9VK76G3hpIFNml1eM=
---

# 多供应商货源接入指南（Supplier Provider Guide）

> P2-5 落地。本文说明如何为 Forge 新增一件代发/货源厂商（CJ、AliExpress、DSers 等），复用统一的货源搜索、导入、库存/价格同步、定时任务链路。

## 1. 架构总览

```
backend/src/forge/suppliers/
├── base.py          # SupplierProvider 抽象基类 + 领域异常
├── registry.py      # provider_code → Provider 实例 的全局注册表
├── schemas.py       # SupplierProduct / SupplierSearchResult / SyncSummary DTO
├── bootstrap.py     # 显式 import providers 子包触发注册（避免循环依赖）
└── providers/
    ├── zendrop.py   # 示例厂商：Zendrop（MCP JSON-RPC 2.0 over HTTP）
    └── ...          # 新厂商在此新增
```

数据落位（migration `0020_supplier_mcp`）：

| 表/列 | 用途 |
|---|---|
| `suppliers.provider_code` | 厂商类型标识（manual 供应商可为空） |
| `supplier_credentials` | 厂商凭据（access_token / oauth 等），一供应商一条 |
| `supplier_sync_logs` | 同步日志（manual/scheduled，success/partial/failed） |
| `products.supplier_id / supplier_product_id / supplier_sku` | 本站商品与货源商品的关联 |

对外 API（前缀 `/api/admin/v1/supplier-sources`）：

```
GET    /providers                    已注册厂商列表（元信息）
GET    /{id}/credentials             读取凭据
PUT    /{id}/credentials             保存凭据
GET    /{id}/auth-url                生成 OAuth PKCE 授权链接（可选能力）
POST   /{id}/oauth/callback          授权码换 token（可选能力）
GET    /{id}/search?keyword=         货源搜索
POST   /{id}/import                  按 provider_product_ids 批量导入
POST   /{id}/sync                    手动触发增量同步
GET    /{id}/sync-logs               同步日志
```

Admin UI（`admin/src/views/suppliers/index.vue`）已内置：凭据配置弹窗、货源搜索/勾选导入弹窗、立即同步、同步日志抽屉。**新增厂商无需改 UI**。

## 2. 新增厂商步骤（核心只有 3 步）

### 2.1 实现 Provider 子类

在 `backend/src/forge/suppliers/providers/` 新建 `<vendor>.py`，继承 `SupplierProvider` 并实现 4 个抽象方法：

| 方法 | 职责 | 必实现 |
|---|---|---|
| `search(...)` | 按关键词/热门搜索厂商货源，返回 `SupplierSearchResult` | 是 |
| `get_product(...)` | 按厂商侧 ID 取单个商品最新信息，返回 `SupplierProduct` | 是 |
| `import_product(...)` | 将货源商品写入本站 `products`（draft 草稿），幂等（已导入则更新） | 是 |
| `sync_inventory_price(...)` | 增量同步已导入商品的库存/价格，返回 `SyncSummary` | 是 |
| `build_auth_url / exchange_token` | 可选。支持 OAuth2.0 PKCE 时实现，否则沿用默认 `NotImplementedError` | 否 |

要点：

- `provider_code` 唯一且不可变（存量供应商依赖它路由）；`display_name` 用于 UI 下拉。
- 厂商返回的任意商品结构，在 `search`/`get_product` 内归一化为 `SupplierProduct`（价格转 float、库存转 int、图片转 URL 列表），解析差异收敛在适配器内部。
- `import_product` 必须回填 `supplier_id / supplier_product_id / supplier_sku`，且按 `supplier_id + supplier_product_id` 做幂等（参考 zendrop 实现）。
- 鉴权失败抛 `ProviderAuthError`（API 层映射 401），网络/协议失败抛 `ProviderConnectionError`（映射 502）。
- 文件末尾调用 `register(MyProvider())`。

### 2.2 确保注册生效

`bootstrap.py` 已 `import forge.suppliers.providers`，`providers/__init__.py` 需显式 import 新厂商模块（参考现有 zendrop import）。随后：

- API 路由 `supplier_sources.py` 与调度器 `scheduler.py` 均已 `import forge.suppliers.bootstrap`，自动携带新厂商。
- 校验：`GET /api/admin/v1/supplier-sources/providers` 应能看到新 `provider_code`。

### 2.3 配置凭据并接入

1. Admin 供应商页新建供应商，集成类型选 `dropship`，厂商选新 provider_code。
2. 「凭据」弹窗填入厂商 Access Token（或走 OAuth PKCE 授权链接）。
3. 「搜索货源」→ 勾选 → 导入，商品以 draft 状态进入 `products`。
4. 「立即同步」或等待每日 03:00 定时任务自动增量同步（`scheduler.py` 每日 cron 对所有已配置、启用中的供应商执行）。

## 3. 协议形态参考

- **MCP JSON-RPC 2.0 over HTTP**（Zendrop 官方 MCP Server）：
  `POST https://app.zendrop.com/mcp/v1`，Header `Authorization: Bearer <token>`，Body `{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"get_catalog_product","arguments":{...}}}`。
  Scopes：`catalog:read, my_products:write, orders:read/write, stores:read/write, billing:read`；限流：读 120/min、写 30/min、履约 10/min。
- **REST API**：新厂商如走 HTTP REST，直接在 provider 内用 `httpx` 调用即可，无需改动框架层。

## 4. 配置项

| 配置 | 位置 | 说明 |
|---|---|---|
| `ZENDROP_MCP_URL` | backend 环境变量（`main/config.py` 的 `settings.zendrop_mcp_url`） | Zendrop MCP 端点 |
| `supplier.config.auto_update_price` | 供应商 config JSON | 定时同步是否覆盖本站售价（默认 true） |
| 每日同步时间 | `main/scheduler.py` `_SYNC_HOUR` | 默认 03:00，改动后需重建 backend |

## 5. 验收清单（新增厂商后）

1. `GET /supplier-sources/providers` 返回新厂商元信息。
2. 未配置凭据时 `search` → 400；假 token `search` → 401/502；不存在供应商 → 404。
3. 配置凭据后 `search` 能返回归一化商品（title/price/inventory/images）。
4. `import` 后 `products` 出现 draft 商品，且 `supplier_id / supplier_product_id` 回填正确；重复导入不产生重复行。
5. `sync` 返回日志（success/partial/failed），`sync-logs` 可查。
6. Admin UI 供应商页：凭据保存、搜索弹窗勾选导入、同步日志抽屉均可用。
*（内容由AI生成，仅供参考）*
