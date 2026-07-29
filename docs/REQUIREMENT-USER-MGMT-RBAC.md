# RBAC 用户权限管理系统 — 需求文档 v2.0

> 版本：v2.0 | 更新：2026-07-21
> 参考调研：Shopify / Magento / WooCommerce / go-admin / Casbin / Keycloak / Spatie

---

## 1. 业务目标

为 Forge 管理后台实现完整的 RBAC 用户权限管理，替代当前占位的 `require_role` 假守卫。

| 目标 | 描述 |
|------|------|
| 权限鉴权 | 基于 Casbin RBAC 引擎，支持 `resource:action` 粒度权限检查 |
| 角色管理 | 预设角色 + 自定义角色，角色→权限多对多关联 |
| 用户管理 | B 端管理员独立于 C 端用户，admin_users 与 users 分表 |
| 前端控制 | 路由级 + 按钮级权限，Soybean 原生路由过滤 + v-permission 指令 |

---

## 2. 数据模型

### 2.1 ER 图

```
admin_users  ──M:N──  admin_user_roles  ──M:N──  roles  ──M:N──  role_permissions  ──M:N──  permissions
                                                                    │
                                                              casbin_rule (Casbin Adapter 自动管理)
```

### 2.2 表结构

| 表 | 说明 | 关键字段 |
|----|------|---------|
| `admin_users` | B 端管理员 | id, email, password_hash, display_name, is_active |
| `roles` | 角色 | id, name (唯一), display_name, is_system |
| `permissions` | 权限码 | id, code (唯一，格式 `resource:action`), display_name, module |
| `role_permissions` | 角色-权限关联 | role_id FK, permission_id FK (联合主键) |
| `admin_user_roles` | 管理员-角色关联 | admin_user_id FK, role_id FK (联合主键) |
| `casbin_rule` | Casbin 策略表 | p_type, v0(role), v1(resource), v2(action) |

### 2.3 预设角色与权限

| 角色 | 权限码 |
|------|--------|
| `super_admin` | 全部 12 个权限 |
| `admin` | products:manage, orders:manage, pricing:manage, shipments:manage, suppliers:manage, users:manage, settings:manage, dashboard:view |
| `operator` | products:manage, orders:manage, pricing:manage, shipments:view, dashboard:view |
| `support` | orders:view, shipments:view, dashboard:view, ai_probe:use |

权限码全量：

| 模块 | permission code | 说明 |
|------|----------------|------|
| products | products:manage | 商品增删改查 |
| orders | orders:manage | 订单管理（含审核） |
| orders | orders:view | 订单只读 |
| pricing | pricing:manage | 定价规则 + 促销管理 |
| shipments | shipments:manage | 物流管理 |
| shipments | shipments:view | 物流只读 |
| suppliers | suppliers:manage | 供应商管理 |
| users | users:manage | 管理员用户管理 |
| settings | settings:manage | 系统设置 |
| settings | settings:view | 设置只读 |
| dashboard | dashboard:view | 仪表盘查看 |
| ai_probe | ai_probe:use | AI 探针使用 |

---

## 3. 技术选型（已实施）

### 3.1 后端

| 组件 | 选型 | 理由 |
|------|------|------|
| RBAC 引擎 | Casbin (pycasbin + casbin-sqlalchemy-adapter) | PERM 模型解耦策略与业务，策略存 PostgreSQL |
| 鉴权模型 | RBAC with Roles (`casbin_model.conf`) | `g(r.sub, p.sub)` → `r.obj == p.obj && r.act == p.act` |
| 权限守卫 | FastAPI Depends + `require_permission(resource, action)` | 声明式鉴权，与 FastAPI DI 无缝集成 |
| 用户认证 | AdminAuthService + JWT + bcrypt | admin_users 表独立认证 |
| ORM | SQLAlchemy 2.0 async + M2M relationship | 支持 async selectinload 预加载关联 |

### 3.2 前端

| 组件 | 选型 | 理由 |
|------|------|------|
| 框架 | Soybean Admin (Vue 3 + Naive UI) | 已有路由级 meta.roles 过滤 |
| 按钮权限 | v-permission 自定义指令 | 参考 go-admin 的 `v-permission="['products:edit']"` |
| 权限 UI | 权限树（checkbox tree） | 参考 Orchid Laravel 权限树交互 |

---

## 4. 执行计划（见 PLAN-RBAC-IMPLEMENTATION.md）

## 5. 验收标准

- [x] 使用 `admin@forge.dev` 登录，返回 roles: ["super_admin"]，permissions: [15个]
- [x] 无 token 访问 `/api/admin/v1/products` 返回 401
- [ ] 仅有 `support` 角色的用户访问 `POST /api/admin/v1/products` 返回 403
- [ ] 仅有 `support` 角色的用户访问 `GET /api/admin/v1/dashboard/stats` 正常返回
- [ ] 前端侧边栏根据角色过滤可见菜单项
- [ ] 前端按钮根据权限指令显示/隐藏

---

## 6. 实施状态

| 阶段 | 状态 | 说明 |
|------|------|------|
| 后端基础设施 | ✅ 已完成 | ORM + Casbin + Auth Service + 依赖守卫 |
| 路由迁移 | ✅ 已完成 | 全部 9 模块迁移至 `require_permission` |
| 种子数据 | ✅ 已完成 | 1 超管 + 4 角色 + 16 权限 + Casbin 策略 |
| 部署验证 | ✅ 已完成 | 9/9 API 端点权限验证通过 |
| 前端权限适配 | ⬜ 待开始 | v-permission 指令 + 路由适配 |
| 用户/角色管理 UI | ⬜ 待开始 | CRUD 页面 |
| 端到端测试 | ⬜ 待开始 | - |

## 7. 最终权限码定义

| 资源 | 权限码 | 说明 |
|------|--------|------|
| products | `products:view`, `products:create`, `products:edit` | 商品查看/新增/编辑 |
| orders | `orders:view`, `orders:review`, `orders:procure`, `orders:refund` | 订单查看/审核/采购/退款 |
| pricing | `pricing:manage` | 定价规则 + 促销管理 |
| shipments | `shipments:manage` | 物流管理 |
| suppliers | `suppliers:manage` | 供应商管理 |
| users | `users:view`, `users:manage` | 用户查看/管理 |
| settings | `settings:manage` | 系统设置 |
| dashboard | `dashboard:view` | 仪表盘 |
| chat | `chat:manage` | AI 探针 |

## 8. 角色→权限映射（实际）

| 权限 | super_admin | admin | operator | support |
|------|:--:|:--:|:--:|:--:|
| products:view | ✅ | ✅ | ✅ | |
| products:create | ✅ | ✅ | ✅ | |
| products:edit | ✅ | ✅ | ✅ | |
| orders:view | ✅ | ✅ | ✅ | ✅ |
| orders:review | ✅ | ✅ | ✅ | |
| orders:procure | ✅ | ✅ | ✅ | |
| orders:refund | ✅ | ✅ | | |
| pricing:manage | ✅ | ✅ | ✅ | |
| shipments:manage | ✅ | ✅ | ✅ | |
| suppliers:manage | ✅ | ✅ | | |
| users:view | ✅ | ✅ | | |
| users:manage | ✅ | ✅ | | |
| settings:manage | ✅ | ✅ | | |
| dashboard:view | ✅ | ✅ | ✅ | ✅ |
| chat:manage | ✅ | | | ✅ |

## 9. 技术实现细节

| 层级 | 技术 | 说明 |
|------|------|------|
| 权限引擎 | Casbin (pycasbin) | RBAC model.conf，SQLAlchemy Adapter 持久化到 casbin_rule 表 |
| 鉴权守卫 | `Depends(require_permission(resource, action))` | 闭包工厂，asyncio.to_thread 调用同步 enforcer |
| 身份认证 | JWT + `get_current_admin` | Bearer token → admin_users 表，含 roles + permissions eager load |
| ORM | SQLAlchemy 2.0 async | 五表：admin_users / roles / permissions / role_permissions / admin_user_roles |
| 种子 | `backend/seed_admin.py` | 幂等 upsert，自动 create_all + sync Casbin 策略 |
| 模型文件 | `backend/casbin_model.conf` | [request_definition] r=sub,obj,act; [matchers] g(r.sub,p.sub)&&r.obj==p.obj&&r.act==p.act |
