# RBAC 实现执行计划

> 创建：2026-07-21 | 分支：`feature/rbac-implementation`
> 技术路线：Casbin RBAC + decorator 守卫 + Soybean v-permission

---

## 阶段总览

| Phase | 名称 | 状态 | 依赖 |
|-------|------|------|------|
| Phase 0 | 基础设施（ORM + Casbin + Auth） | ✅ 已完成 | - |
| Phase 1 | 路由迁移 | ✅ 已完成 | Phase 0 |
| Phase 2 | Seed 数据 + 部署验证 | ✅ 已完成 | Phase 1 |
| Phase 3 | Admin 前端权限适配 | ✅ 已完成 | Phase 2 |
| Phase 4 | 用户/角色管理 UI | ✅ 已完成 | Phase 3 |
| Phase 5 | 端到端测试 + 安全审计 | ⬜ 待开始 | Phase 4 |

---

## Phase 0: 基础设施 ✅

| 任务 | 文件 | 状态 |
|------|------|------|
| ORM 模型 (admin_users/roles/permissions/role_permissions/admin_user_roles) | `backend/src/.../models.py` | ✅ |
| Casbin enforcer 工厂 | `backend/src/.../casbin_enforcer.py` | ✅ |
| Casbin 模型配置 | `backend/casbin_model.conf` | ✅ |
| Admin Auth Service (login/me) | `backend/src/.../admin_auth_service.py` | ✅ |
| get_current_admin 依赖 | `backend/src/.../dependencies.py` | ✅ |
| require_permission 守卫 | `backend/src/.../dependencies.py` | ✅ |
| Admin Router 挂载 | `backend/src/.../admin/v1/router.py` | ✅ |

---

## Phase 1: 路由迁移 ✅

| 任务 | 文件 | 状态 |
|------|------|------|
| products → require_permission("products", "view"/"create"/"edit") | `admin/v1/products.py` | ✅ |
| orders → require_permission("orders", "view"/"review"/"procure"/"refund") | `admin/v1/orders.py` | ✅ |
| pricing → require_permission("pricing", "manage") | `admin/v1/pricing.py` | ✅ |
| shipments → require_permission("shipments", "manage") | `admin/v1/shipments.py` | ✅ |
| suppliers → require_permission("suppliers", "manage") | `admin/v1/suppliers.py` | ✅ |
| users → require_permission("users", "view"/"manage") | `admin/v1/users.py` | ✅ |
| settings → require_permission("settings", "manage") | `admin/v1/settings.py` | ✅ |
| dashboard → require_permission("dashboard", "view") | `admin/v1/dashboard.py` | ✅ |
| chat_requests → require_permission("chat", "manage") | `admin/v1/chat_requests.py` | ✅ |
| 全局残留 require_role/get_current_user_id 清理 | `admin/v1/*.py` | ✅ |

---

## Phase 2: Seed 数据 + 部署验证 ✅

> 完成时间：2026-07-21

### Step 2.1: 更新 seed_admin.py

**完成**：

- 重写 `backend/seed_admin.py`，基于新 RBAC 模型（`ORMAdminUser` + `ORMRole` + `ORMPermission`）
- 预设 1 个超管（`admin@forge.dev / admin123`）
- 预设 4 角色：`super_admin` / `admin` / `operator` / `support`
- 预设 16 权限码（与路由守卫完全对齐）：

| 资源 | 权限 |
|------|------|
| products | view, create, edit |
| orders | view, review, procure, refund |
| pricing | manage |
| shipments | manage |
| suppliers | manage |
| users | view, manage |
| settings | manage |
| dashboard | view |
| chat | manage |

- 角色→权限 关联 + Casbin 策略同步
- 自动创建表结构（`Base.metadata.create_all`）

### Step 2.2: 更新 Dockerfile

- 添加 `COPY casbin_model.conf .`（容器内 `/app/casbin_model.conf`）
- `pyproject.toml` 添加 `psycopg2-binary>=2.9.0`（Casbin adapter 同步驱动）

### Step 2.3: 重建 + 种子

- `podman-compose build --no-cache backend` + `restart backend`
- `podman exec forge-backend python /app/seed_admin.py` 成功
- 发现路由权限与种子不匹配（路由使用细粒度 `products:view/create/edit`），已修复种子与路由对齐

### Step 2.4: 验证

| 测试 | 方法 | 预期 | 状态 |
|------|------|------|------|
| Admin Login | `POST /api/admin/v1/auth/login` | 200 + token + roles+permissions | ✅ |
| 无 token 访问 | `GET /api/admin/v1/{任意}` | 401 | ✅ |
| super_admin 全模块通过 | Casbin enforce 6 个资源 | 全部 True | ✅ |
| 未注册用户拒绝 | Casbin enforce `nobody@test.com` | 全部 False | ✅ |
| API 9 模块权限守卫 | GET 请求含 valid token | 9/9 通过 | ✅ |
| 登录返回权限列表 | 登录响应 `user.permissions` | 15 条 | ✅ |

---

## Phase 3: Admin 前端权限适配 ✅

| 任务 | 文件 | 状态 |
|------|------|------|
| API URL 修正 `/api/v1/auth/*` → `/api/admin/v1/auth/*` | `admin/src/service/api/auth.ts` | ✅ |
| Auth Store 适配 roles[] + permissions[] | `admin/src/store/modules/auth/index.ts` | ✅ |
| 12 处路由 meta.roles 对齐后端 | `admin/src/router/routes/index.ts` | ✅ |
| VITE_STATIC_SUPER_ROLE → super_admin | `admin/.env` | ✅ |
| v-permission 按钮级权限指令 | `admin/src/plugins/permission.ts` | ✅ |
| UserInfo 类型补充 permissions | `admin/src/typings/api/auth.d.ts` | ✅ |
| Docker 重建 + 部署验证 | `docker-compose build admin` | ✅ |

---

## Phase 4: 用户/角色管理 UI ✅

### Step 4.1: 管理员用户列表页

| 功能 | 说明 |
|------|------|
| 表格展示 | 邮箱 / 显示名 / 角色标签 / 状态 / 最后登录 |
| 搜索 | 按邮箱或名称搜索 |
| 新增 | 弹窗表单（邮箱、密码、显示名、角色多选） |
| 编辑 | 可修改显示名、状态、密码 |
| 角色分配 | 独立 Modal，多选角色 |

### Step 4.2: 角色管理页

| 功能 | 说明 |
|------|------|
| 角色列表 | 名称 / 显示名 / 描述 / 系统标记 / 权限标签 |
| 新增/编辑 | 弹窗表单（名称、显示名、描述、权限按模块 checkbox） |
| 删除 | 系统角色禁止删除，自定义角色可删除 |
| 权限分配 | 按模块分组（Products / Orders / Pricing 等） |

### Step 4.3: 后端 API 补充

| API | 方法 | 文件 | 状态 |
|-----|------|------|------|
| `GET /api/admin/v1/admin-users/` | GET | `admin_users.py` | ✅ |
| `POST /api/admin/v1/admin-users/` | POST | `admin_users.py` | ✅ |
| `PUT /api/admin/v1/admin-users/{id}` | PUT | `admin_users.py` | ✅ |
| `PUT /api/admin/v1/admin-users/{id}/roles` | PUT | `admin_users.py` | ✅ |
| `DELETE /api/admin/v1/admin-users/{id}` | DELETE | `admin_users.py` | ✅ |
| `GET /api/admin/v1/roles/` | GET | `admin_roles.py` | ✅ |
| `POST /api/admin/v1/roles/` | POST | `admin_roles.py` | ✅ |
| `PUT /api/admin/v1/roles/{id}` | PUT | `admin_roles.py` | ✅ |
| `DELETE /api/admin/v1/roles/{id}` | DELETE | `admin_roles.py` | ✅ |
| `GET /api/admin/v1/roles/permissions` | GET | `admin_roles.py` | ✅ |

### Step 4.4: 修复

- `psycopg2-binary` 未安装 → 重建 backend 镜像
- `admin_roles.py` Casbin 同步使用 `asyncio.to_thread` + 同步 enforcer（修复 `db.sync_session` 不存在问题）

---

## Phase 5: 端到端测试 + 安全审计 ⬜

- [ ] 所有 admin 端点权限矩阵测试
- [ ] JWT 过期测试
- [ ] 并发访问测试
- [ ] Casbin 策略热重载测试
- [ ] 前端按钮级权限正确性

---

## 状态图例

| 图标 | 含义 |
|------|------|
| ✅ | 已完成 |
| 🔄 | 进行中 |
| ⬜ | 待开始 |
| ❌ | 失败/阻塞 |

---

*最后更新：2026-07-21*
