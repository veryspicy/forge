# Forge 商品体系改造设计（分类树 + 商品类型规格模板 + SKU 自动编号 + 轻量品牌）

> 状态：设计稿（待用户确认决策点后进入实施）
> 关联：DEV-RULES.md / GIT-WORKFLOW.md / INFRA-BASELINE.md

---

## 1. 背景与目标

当前 Forge 商品体系为早期 MVP 形态，规格属性、分类、品牌均为"单字段/单枚举"存储，无法支撑全球化宠物用品独立站的导航、筛选与运营诉求：

| 现状 | 问题 |
|------|------|
| `products.category` String(50) 单层枚举（如 FOOD） | 无层级，无法支撑前台导航/分类筛选页/SEO 分类页 |
| `products.brand` String(255) 纯字符串 | 无品牌实体，无法筛选与品牌运营 |
| `product_variants.attributes` JSONB，前端手填 JSON 文本 | 反人类、无约束、无法索引筛选 |
| 变体 `sku` 必填手工编号 | 无自动生成规则，易重易乱 |

改造目标（对齐 mall-admin-web 设计，但用 Forge 自有 Naive UI 组件实现，不引入参考代码）：

1. 商品分类树：一级/二级（表结构预留三级），支撑前台导航与筛选
2. 商品类型（规格模板）：类型挂规格键，商品选类型自动带出规格
3. SKU 编号自动生成：系统辅助生成 + 商家可改，DB 唯一约束兜底
4. 属性建模混合模式：规格关系表为权威定义，`attributes` JSONB 降级为读快照
5. 轻量品牌：`brands` 表替换字符串字段
6. SKU 编辑对齐 mall-admin-web：弹窗内嵌可编辑表格，行内直接改价格/库存/预警值

---

## 2. 现状盘点

### 2.1 表结构（相关部分）

**products**（SPU 粒度）
- `sku` String(100) unique（商品货号/业务编号）
- `category` String(50) NOT NULL index（单层枚举：FOOD 等）
- `brand` String(255) NULL
- `supplier_id` / `supplier_sku` / `supplier_product_id`（供应商链路）
- `inventory` / `is_new` / `is_recommend` / `sort_order` / `sales` / `audit_status`
- `name_translations` / `description_translations`（多语言 JSONB）

**product_variants**（SKU 粒度，migration 0019）
- `id` UUID PK，`product_id` FK（级联删除）
- `sku` String(100) NOT NULL unique（当前必填手工填）
- `name` String(255) NOT NULL
- `attributes` JSONB NOT NULL default '{}'（当前前端手填 JSON）
- `price` / `cost` / `inventory` / `status` / `is_default`

### 2.2 API

- `VariantCreate.sku: str`（必填）；`ProductService._validate_variant` 强制 sku 非空
- `create_variant` / `update_variant` 均做 sku 全局唯一校验（`ProductSkuConflictError`）
- C 端 `GET /api/v1/products` 支持 `category`（精确匹配单层字符串）与 `sort` 多档排序

### 2.3 前端

- `admin/src/views/products-new/index.vue`：变体弹窗表单（sku/name/attributesText 手填 JSON/price/cost/inventory/status/is_default）
- `admin/src/views/products/index.vue`：商品列表（已对齐 mall 列表布局）
- `products-detail`：详情页

---

## 3. 行业调研结论（摘要）

来源：search-agent 调研 + mall（macrozheng）表结构核对（DeepWiki）

| 议题 | 行业结论 |
|------|---------|
| SKU 编号 | 无统一标准；主流"系统辅助生成 + 商家可改"双轨；格式 `品类-属性-序列`（如 `TSH-BLK-M-001`），长度 8~16 位；唯一性建议 DB 唯一索引硬约束（Shopify 仅告警） |
| 属性建模 | 混合模式：关系表（规格名/值/关联）管权威定义保证可索引筛选，SKU 表冗余 JSON 快照供读路径直出；纯 JSON 弱约束、纯 EAV 查询复杂，均不推荐 |
| mall 分类树 | `pms_product_category` parent_id 自关联多级；Forge 做 2 级（预留 3 级）即可 |
| mall 商品类型 | `pms_product_attribute_category` + attribute（type 0=规格/1=参数）；本质是规格模板，商品按类型套用 |
| mall 品牌 | `pms_brand`（名称/首字母/logo/排序/显示状态/品牌故事）；Forge 自营，做轻量版 |

---

## 4. 目标设计

### 4.1 数据模型

#### 4.1.1 商品分类树 `product_categories`

```
id            BIGINT PK autoincrement
parent_id     BIGINT NULL, FK self（NULL=一级；二级指向一级 id）
name          VARCHAR(100) NOT NULL
slug          VARCHAR(150) NOT NULL UNIQUE   -- SEO 友好，C 端筛选用
icon          VARCHAR(500) NULL              -- 图标 URL
sort          INT NOT NULL DEFAULT 0
status        VARCHAR(20) NOT NULL DEFAULT 'active'   -- active / inactive
level         INT NOT NULL DEFAULT 1          -- 冗余层级 1/2（预留 3）
created_at / updated_at
INDEX ix_product_categories_parent_id(parent_id)
```

约束：同一 parent 下 name/slug 唯一；删除分类前须确认无子分类与无商品引用（或软删 status='inactive'）。

#### 4.1.2 轻量品牌 `brands`

```
id            BIGINT PK autoincrement
name          VARCHAR(100) NOT NULL UNIQUE
logo          VARCHAR(500) NULL
show_status   BOOLEAN NOT NULL DEFAULT true
sort          INT NOT NULL DEFAULT 0
created_at / updated_at
```

#### 4.1.3 商品类型（规格模板）

**product_types**

```
id            BIGINT PK autoincrement
name          VARCHAR(100) NOT NULL UNIQUE    -- 如 服饰 / 食品 / 玩具
status        VARCHAR(20) NOT NULL DEFAULT 'active'
sort          INT NOT NULL DEFAULT 0
created_at / updated_at
```

**product_type_specs**（类型 → 规格键模板）

```
id               BIGINT PK autoincrement
product_type_id  BIGINT NOT NULL FK product_types（级联删除）
spec_key         VARCHAR(50) NOT NULL          -- 如 颜色 / 尺码
sort             INT NOT NULL DEFAULT 0
UNIQUE(product_type_id, spec_key)
```

#### 4.1.4 商品规格（SPU 级实例）

**product_spec_keys**（SPU 实际使用的规格键）

```
id           BIGINT PK autoincrement
product_id   BIGINT NOT NULL FK products（级联删除）
spec_key     VARCHAR(50) NOT NULL              -- 从类型模板带出，可增删
sort         INT NOT NULL DEFAULT 0
UNIQUE(product_id, spec_key)
```

**product_spec_values**（规格键下的可选值）

```
id             BIGINT PK autoincrement
spec_key_id    BIGINT NOT NULL FK product_spec_keys（级联删除）
value          VARCHAR(100) NOT NULL           -- 如 Black / M
sort           INT NOT NULL DEFAULT 0
UNIQUE(spec_key_id, value)
```

**variant_specs**（变体 ↔ 规格值关联，决定 SKU 组合）

```
id           BIGINT PK autoincrement
variant_id   BIGINT NOT NULL FK product_variants（级联删除）
spec_key_id  BIGINT NOT NULL FK product_spec_keys
spec_value_id BIGINT NOT NULL FK product_spec_values
UNIQUE(variant_id, spec_key_id)
```

#### 4.1.5 存量表变更

**products** 新增列：
- `category_id` BIGINT NULL FK product_categories（过渡期与 `category` 字符串双写；C 端接口切换后移除 `category`）
- `brand_id` BIGINT NULL FK brands（过渡期与 `brand` 字符串双写）
- `product_type_id` BIGINT NULL FK product_types（选型后带出规格模板）

**product_variants** 变更：
- `sku` 保持 NOT NULL UNIQUE（生成/编辑双轨，DB 唯一索引兜底不变）
- `attributes` JSONB 保留为**读快照**：由变体/规格变更事件重建为 `{spec_key: value}`，不再作为输入

#### 4.1.6 数据流

```
创建类型 → 定义规格键模板（product_type_specs）
创建商品 → 选类型（product_type_id）→ 自动带出规格键（product_spec_keys）
定义规格值（product_spec_values）→ 生成 SKU 组合（variant_specs）→ 每组合一条 product_variants
变体/规格变更 → 事件同步 → 重建 variant.attributes 快照 + 重算 products.inventory（复用 sync_product_inventory）
```

### 4.2 SKU 编号自动生成规则

格式：`{商品货号}-{规格短码}`，短码按规格键 sort 排序拼接，每个规格值取"首字母大写字母+数字"缩写（去空格/特殊字符，≤4 位）。

示例：
- 商品货号 `PET-1001`，规格 颜色=Black / 尺码=M → `PET-1001-BLK-M`
- 无规格单 SKU → `PET-1001-01`

规则细节：
1. **生成时机**：创建变体时 `sku` 为空 → 后端自动生成；非空则按商家填写
2. **冲突兜底**：生成结果与已有 sku 冲突 → 追加 `-2`、`-3` 递增序号
3. **可编辑**：自动生成后允许商家覆盖（行业双轨做法），编辑时走既有全局唯一校验
4. **唯一性**：依赖 `ix_product_variants_sku` UNIQUE 索引硬约束
5. 实现位置：`ProductService._generate_variant_sku(db, product, spec_values)`，在 `create_variant` 入口判断

### 4.3 API 设计

**Admin（/api/admin/v1）**

| 资源 | 方法 | 说明 |
|------|------|------|
| `/categories` | GET | 返回树形（一次查全量组树，带 status 过滤） |
| `/categories` | POST/PUT/DELETE | 分类 CRUD；删除前校验子分类/商品引用 |
| `/brands` | GET/POST/PUT/DELETE | 品牌 CRUD（列表带 logo/排序） |
| `/product-types` | GET/POST/PUT/DELETE | 商品类型 CRUD，GET 单个返回 specs 模板 |
| `/product-types/{id}/specs` | PUT | 保存类型规格键模板（全量替换） |
| `/products` POST | — | ProductCreate 增 `category_id`/`brand_id`/`product_type_id` |
| `/products/{id}` PUT | — | ProductUpdate 同步支持 |
| `/products/{id}/variants` POST | — | VariantCreate.sku 改为 `str \| None`，空则自动生成 |
| `/products/{id}/variants/{vid}` PUT | — | 行内编辑保存（价格/库存/成本/预警值/规格值） |
| `/products/{id}/variants/{vid}` DELETE | — | 删除变体（同步重算） |

**C 端（/api/v1）**

| 资源 | 说明 |
|------|------|
| `/categories` | 分类树（status=active），供导航/筛选页 |
| `/brands` | 品牌列表（show_status=true） |
| `/products` | `category` 参数升级为 slug 匹配叶子分类（含父分类归集子分类）；`brand` 参数可选 |

### 4.4 前端交互设计（admin，Naive UI 自有组件）

1. **商品分类页**：新增菜单；树形表格（NTree 或 NDataTable 树模式），一级/二级展开；行内操作：新增子分类/编辑/停用/删除
2. **商品类型页**：新增菜单；类型列表 + 规格键模板编辑器（可增删规格键、排序）
3. **品牌管理页**：新增菜单；品牌列表（logo 缩略图 + 名称 + 显示开关 + 排序）
4. **商品新建/编辑**：
   - 分类：级联选择器（NCascader，两级）
   - 品牌：NSelect 下拉（可搜索，支持"无品牌"）
   - 类型：NSelect 选择后自动带出规格键模板，可增删规格键
   - 规格值：按规格键维护值列表
5. **SKU 编辑（核心改造）**：对齐 mall-admin-web 截图——弹窗内嵌可编辑表格：
   - 列：SKU 编号（自动生成，只读展示）/ 规格组合（下拉选择已维护的规格值）/ 销售价格（NInputNumber 行内编辑）/ 商品库存（NInputNumber）/ 库存预警值（新增）/ 操作（删除行、新增 SKU 行）
   - 去掉 attributesText 手填 JSON 文本框
   - 新增 SKU 行时自动生成编号并展示，保存走 batch 接口（或逐行 PUT）

### 4.5 数据迁移与存量处理

1. 新 migration（编号续 0027 之后）：
   - 建 5 张新表（categories/brands/product_types/product_type_specs/product_spec_keys/product_spec_values/variant_specs）
   - products 加 `category_id` / `brand_id` / `product_type_id` 三列（NULL 起步）
2. 存量数据校正脚本（放 `temp/`，容器内执行）：
   - 现有枚举 category 值 → 创建一级分类同名，products.category_id 关联
   - 现有 brand 字符串 → brands 表去重落库，products.brand_id 关联
   - 现有变体 attributes 解析为规格键/值 → 回填 product_spec_keys/values/variant_specs（仅对结构规整数据，脏数据保留原 JSON）
3. 数据库操作必须容器内执行：`podman exec forge-backend alembic upgrade head`，变更前 `pg_dump` 备份

### 4.6 兼容性

- C 端现有 `/api/v1/products?category=` 在过渡期继续用 `category` 字符串；接口切换为 slug 匹配时保持行为等价（存量枚举值即一级分类 slug）
- `sync_product_inventory` 库存聚合逻辑不变，仅触发点扩展（变体规格变更同样触发）
- 列表页已有 SKU 库存聚合、多档排序、站点配置均不受影响

---

## 5. 实施计划

分支：`feature/product-catalog-refactor`（从 dev 切出；开工前先归集当前未提交改动）

| 阶段 | 内容 | 涉及文件 | 验证 |
|------|------|---------|------|
| 1. 数据库层 | migration（新表+products 新列）；ORM models 扩展 | `backend/migrations/versions/0028_*.py`、`backend/src/forge/infrastructure/persistence/models.py` | 容器内 alembic upgrade；`\d` 核对 |
| 2. 后端 API | 分类/品牌/类型 CRUD + specs 子资源；ProductCreate/Update 扩展；VariantCreate.sku 可选 + 自动生成；变体行内编辑与批量保存；attributes 快照同步；C 端 categories/brands | `backend/src/forge/api/admin/v1/categories.py`、`brands.py`、`product_types.py`、`products.py`、`backend/src/forge/application/services/product_service.py`、`product_repo.py` | pytest（新增用例）+ 接口 curl + ruff/mypy |
| 3. 前端 | 三个管理页 + 商品表单改造 + SKU 行内编辑表格 + 路由/菜单 | `admin/src/views/categories/index.vue`、`brands/index.vue`、`product-types/index.vue`、`products-new/index.vue`、`products-detail/index.vue` | pnpm typecheck/lint；browser-agent 实机验证 |
| 4. 部署验证 | admin `build --no-cache` + `--force-recreate`；backend 重启；端到端 | — | §10 链路核对 + 用户实测 |

质量门槛（§13）：backend ruff/mypy；admin typecheck/lint；提交 Conventional Commits；验证通过前不合 dev。

---

## 6. 决策点（待确认）

| # | 决策项 | 默认建议 |
|---|--------|---------|
| D1 | SKU 自动生成后是否允许商家修改 | 允许（行业双轨），仅校验唯一 |
| D2 | 无规格单 SKU 编号是否加 `-01` 后缀 | 加（保持格式统一） |
| D3 | 分类 slug 是否必填 | 必填（SEO + C 端筛选），提供自动生成 |
| D4 | 分类/品牌删除策略 | 软删（status='inactive'），避免破坏历史商品 |
| D5 | 库存预警值字段 | 变体表新增 `low_stock_threshold`，本轮落地 |
| D6 | 规格键模板是否允许 SPU 级增删 | 允许（模板带出后可增删） |
| D7 | 变体保存形态 | 逐行 PUT（与现有接口一致），不做批量事务接口 |
