# RBAC 实现执行计划

> **分支**: `feature/rbac-casbin`
> **分支基础**: `dev`
> **开始时间**: 2026-07-20
> **参考文档**: `REQUIREMENT-USER-MGMT-RBAC.md`

---

## 阶段 1：后端 RBAC 基础 （Casbin 授权引擎 + Admin Auth）

### 1.1 数据模型 (DB)

| Task | Status | 说明 |
|---|---|---|
| 1.1.1 `admin_users` 表 | ✅ DONE | 与 customers 分表，email/password_hash/display_name/is_active |
| 1.1.2 `roles` 表 | ✅ DONE | name/display_name/description/is_system |
| 1.1.3 `permissions` 表 | ✅ DONE | code/display_name/module |
| 1.1.4 `role_permissions` 关联表 | ✅ DONE | M2M: role_id ↔ permission_id |
| 1.1.5 `admin_user_roles` 关联表 | ✅ DONE | M2M: admin_user_id ↔ role_id |
| 1.1.6 `casbin_rule` 表（casbin-sqlalchemy-adapter 自动管理） | ✅ DONE | p_type/v0/v1/v2/... |

### 1.2 种子数据

| Task | Status | 说明 |
|---|---|---|
| 1.2.1 预设 20 个权限码 | ✅ DONE | products:/orders:/shipments:/pricing:/suppliers:/ai_probe:/settings:/users:/roles: |
| 1.2.2 预设 4 个角色 | ✅ DONE | super_admin / admin / operator / support |
| 1.2.3 默认 admin 用户 | ✅ DONE | admin@forge.com / admin123，绑定 super_admin |
| 1.2.4 Casbin g-rules 同步 | ✅ FIXED | seed_rbac.py Step-6 已添加 user→role g-rules |

### 1.3 Casbin 集成

| Task | Status | 说明 |
|---|---|---|
| 1.3.1 `casbin_model.conf` | ✅ DONE | PERM metamodel: subject→role→resource:action |
| 1.3.2 Enforcer 工厂 | ✅ DONE | `forge/infrastructure/casbin_enforcer.py` |
| 1.3.3 `require_permission()` FastAPI Depends | ✅ DONE | 通过 Casbin enforce 鉴权 |
| 1.3.4 配置导入解耦 | ✅ DONE | 提取 `config.py`，解决循环导入 |

### 1.4 Admin Auth API

| Task | Status | 说明 |
|---|---|---|
| 1.4.1 `AdminAuthService` | ✅ DONE | `application/services/admin_auth_service.py` |
| 1.4.2 `get_current_admin` Depends | ✅ DONE | 从 admin_users 表查角色+权限 |
| 1.4.3 `POST /api/admin/v1/auth/login` | ✅ DONE | JWT 签发，返回 roles + permissions |
| 1.4.4 `GET /api/admin/v1/auth/me` | ✅ DONE | 返回当前用户 role+permissions |

---

## 阶段 2：Admin 权限保护 API 端点

### 2.1 Products API 保护

| Task | Status | 说明 |
|---|---|---|
| 2.1.1 `GET /api/admin/v1/products` → `require_permission("products","view")` | ⬜ TODO | |
| 2.1.2 `POST /api/admin/v1/products` → `require_permission("products","create")` | ⬜ TODO | |
| 2.1.3 `PUT /api/admin/v1/products/{id}` → `require_permission("products","edit")` | ⬜ TODO | |
| 2.1.4 `DELETE /api/admin/v1/products/{id}` → `require_permission("products","delete")` | ⬜ TODO | |

### 2.2 Orders API 保护

| Task | Status | 说明 |
|---|---|---|
| 2.2.1 `GET /api/admin/v1/orders` → `require_permission("orders","view")` | ⬜ TODO | |
| 2.2.2 `PUT /api/admin/v1/orders/{id}/review` → `require_permission("orders","review")` | ⬜ TODO | |

### 2.3 Users Admin API 保护

| Task | Status | 说明 |
|---|---|---|
| 2.3.1 `GET /api/admin/v1/users` → `require_permission("users","view")` | ⬜ TODO | |
| 2.3.2 `POST /api/admin/v1/users` → `require_permission("users","manage")` | ⬜ TODO | |
| 2.3.3 `PUT /api/admin/v1/users/{id}` → `require_permission("users","manage")` | ⬜ TODO | |

### 2.4 Settings / Roles API 保护

| Task | Status | 说明 |
|---|---|---|
| 2.4.1 `GET /api/admin/v1/settings` → `require_permission("settings","manage")` | ⬜ TODO | |
| 2.4.2 `GET /api/admin/v1/roles` → `require_permission("roles","view")` | ⬜ TODO | |

---

## 阶段 3：前端 Admin 集成

### 3.1 Auth Store 适配

| Task | Status | 说明 |
|---|---|---|
| 3.1.1 Admin login 页面调用 `/api/admin/v1/auth/login` | ⬜ TODO | 替换当前 `/login` 端点 |
| 3.1.2 `/me` 端点切换为 `/api/admin/v1/auth/me` | ⬜ TODO | 返回 roles + permissions |
| 3.1.3 `userInfo.roles` 映射 | ⬜ TODO | 后端 `roles: string[]` → 前端路由过滤 |

### 3.2 按钮级权限指令

| Task | Status | 说明 |
|---|---|---|
| 3.2.1 实现 `v-permission` 指令 | ⬜ TODO | 如 `v-permission="products:edit"` 控制按钮显隐 |
| 3.2.2 在菜单/按钮上添加权限码 | ⬜ TODO | 现有页面的 action 按钮绑定权限 |

### 3.3 用户管理页面

| Task | Status | 说明 |
|---|---|---|
| 3.3.1 Admin Users 列表页 | ⬜ TODO | 表格 CRUD，角色标签 |
| 3.3.2 Admin User 创建/编辑表单 | ⬜ TODO | email/password/display_name/role 选择 |
| 3.3.3 角色管理页 | ⬜ TODO | 角色列表 + 权限码勾选编辑 |

---

## 阶段 4：验证与测试

### 4.1 接口测试

| Task | Status | 说明 |
|---|---|---|
| 4.1.1 Login + /me 测试 | ✅ PASS | admin@forge.com 登录成功，返回 20 permissions |
| 4.1.2 Casbin enforce 测试 | ✅ PASS | ALLOW/DENY 正确 |
| 4.1.3 未登录访问拒绝 | ⬜ TODO | 403 检查 |
| 4.1.4 非授权角色拒绝 | ⬜ TODO | operator 角色访问 settings:manage → 403 |
| 4.1.5 Token 过期处理 | ⬜ TODO | |

### 4.2 功能测试

| Task | Status | 说明 |
|---|---|---|
| 4.2.1 Admin 登录 + 菜单可见性 | ⬜ TODO | super_admin 可见所有菜单 |
| 4.2.2 按钮权限控制 | ⬜ TODO | 编辑/删除按钮按角色显隐 |
| 4.2.3 角色切换后权限刷新 | ⬜ TODO | |
| 4.2.4 密码修改功能 | ⬜ TODO | |

---

**图例**: ✅ DONE = 已完成验证 | ✅ FIXED = 已修复 | ⬜ TODO = 待实现 | 🔲 IN-PROGRESS = 进行中 | ❌ BLOCKED = 被阻塞
