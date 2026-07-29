# RBAC 权限系统实现计划

> 分支：`feature/rbac-casbin` | 创建：2026-07-20 | 最后更新：2026-07-20

---

## 状态标记说明

| 图标 | 状态 |
|------|------|
| ⬜ | 待执行 |
| 🔄 | 执行中 |
| ✅ | 已完成并验证通过 |
| ❌ | 失败/阻塞 |

---

## Phase 1：后端基础设施

### 1.1 依赖安装与环境准备

| # | 任务 | 文件/操作 | 状态 |
|---|------|----------|------|
| 1.1.1 | 安装 pycasbin + casbin-fastapi-decorator + asyncpg-adapter | `backend/pyproject.toml` | ⬜ |

### 1.2 数据库 Schema

| # | 任务 | 文件/操作 | 状态 |
|---|------|----------|------|
| 1.2.1 | 创建 ORM 模型：AdminUser, Role, Permission, RolePermission, AdminUserRole | `backend/.../models.py` | ✅ 已完成 |
| 1.2.2 | 创建 Alembic migration | `backend/migrations/versions/` | ✅ 已完成（seed create_all 兜底） |
| 1.2.3 | 在容器内执行 migration | `podman exec backend alembic upgrade head` | ✅ 已完成 |
| 1.2.4 | 创建 seed 脚本：预设角色 + 权限 + admin 用户 | `backend/seed_rbac.py` | ✅ 已完成 |

### 1.3 Casbin 授权引擎

| # | 任务 | 文件/操作 | 状态 |
|---|------|----------|------|
| 1.3.1 | 创建 Casbin model 定义 (rbac_model.conf) | `backend/casbin_model.conf` | ✅ 已完成 |
| 1.3.2 | 实现 Enforcer 工厂（sync for now, SQLAlchemy adapter） | `backend/.../casbin_enforcer.py` | ⬜ |
| 1.3.3 | 创建 FastAPI Dependency：get_enforcer | `backend/.../dependencies.py` | ⬜ |
| 1.3.4 | 实现策略同步：role_permissions → casbin_rule | `backend/.../casbin_enforcer.py` | ⬜ |

### 1.4 Admin 认证分离

| # | 任务 | 文件/操作 | 状态 |
|---|------|----------|------|
| 1.4.1 | 实现 AdminAuthService（Admin 独立登录） | `backend/.../services/admin_auth_service.py` | ⬜ |
| 1.4.2 | 实现 `get_current_admin` 依赖（JWT → admin_users 表） | `backend/.../dependencies.py` | ⬜ |
| 1.4.3 | 创建 `/api/admin/v1/auth/login` + `/api/admin/v1/auth/me` | `backend/.../api/admin/v1/auth.py` | ⬜ |
| 1.4.4 | Admin `/me` 返回 roles + permissions 列表 | 同上 | ⬜ |

### 1.5 Admin Users CRUD API

| # | 任务 | 文件/操作 | 状态 |
|---|------|----------|------|
| 1.5.1 | 增强 GET `/api/admin/v1/users`（分页+搜索+角色过滤） | `backend/.../api/admin/v1/users.py` | ⬜ |
| 1.5.2 | 实现 POST `/api/admin/v1/users`（创建管理员） | 同上 | ⬜ |
| 1.5.3 | 实现 PATCH `/api/admin/v1/users/{id}`（更新信息） | 同上 | ⬜ |
| 1.5.4 | 实现 PATCH `/api/admin/v1/users/{id}/roles`（分配角色） | 同上 | ⬜ |
| 1.5.5 | 实现 PATCH `/api/admin/v1/users/{id}/status`（启用/禁用） | 同上 | ⬜ |

### 1.6 Roles CRUD API

| # | 任务 | 文件/操作 | 状态 |
|---|------|----------|------|
| 1.6.1 | 创建 roles router + GET/POST/PATCH/DELETE | `backend/.../api/admin/v1/roles.py` | ⬜ |
| 1.6.2 | 实现 PUT `/api/admin/v1/roles/{id}/permissions` | 同上 | ⬜ |
| 1.6.3 | 创建 permissions GET 接口 | `backend/.../api/admin/v1/permissions.py` | ⬜ |

### 1.7 构建验证

| # | 任务 | 文件/操作 | 状态 |
|---|------|----------|------|
| 1.7.1 | 重建 backend 容器 | `podman-compose restart backend` | ⬜ |
| 1.7.2 | 运行 seed 脚本 | `podman exec backend python seed_rbac.py` | ⬜ |
| 1.7.3 | API 冒烟测试（curl 验证各接口） | shell_executor | ⬜ |

---

## Phase 2：前端改造

### 2.1 Admin Auth 对接

| # | 任务 | 文件/操作 | 状态 |
|---|------|----------|------|
| 2.1.1 | 更新 admin auth store 对接 `/api/admin/v1/auth/*` | `admin/.../store/modules/auth/index.ts` | ⬜ |
| 2.1.2 | 更新 `fetchLogin` / `fetchGetUserInfo` API 路径 | `admin/.../service/api/auth.ts` | ⬜ |
| 2.1.3 | 更新 userInfo 类型定义（permissions 字段） | `admin/.../typings/api/auth.d.ts` | ⬜ |

### 2.2 v-permission 指令

| # | 任务 | 文件/操作 | 状态 |
|---|------|----------|------|
| 2.2.1 | 创建 `v-permission` 指令 | `admin/.../plugins/permission.ts` | ⬜ |
| 2.2.2 | 注册指令到 Vue app | `admin/.../plugins/index.ts` | ⬜ |
| 2.2.3 | 在现有页面按钮上使用 v-permission 替换条件判断 | 各 views/*.vue | ⬜ |

### 2.3 用户管理页增强

| # | 任务 | 文件/操作 | 状态 |
|---|------|----------|------|
| 2.3.1 | 添加新建用户对话框（email+pwd+display_name） | `admin/.../views/users/index.vue` | ⬜ |
| 2.3.2 | 添加启用/禁用操作 | 同上 | ⬜ |
| 2.3.3 | 改造角色分配为多选 | 同上 | ⬜ |
| 2.3.4 | 添加搜索输入框 | 同上 | ⬜ |

### 2.4 角色管理页（新建）

| # | 任务 | 文件/操作 | 状态 |
|---|------|----------|------|
| 2.4.1 | 创建角色列表页（表格+CRUD） | `admin/.../views/roles/index.vue` | ⬜ |
| 2.4.2 | 创建角色编辑：权限树勾选 | 同上 | ⬜ |
| 2.4.3 | 注册路由 `/roles` | `admin/.../router/routes/index.ts` | ⬜ |
| 2.4.4 | 添加 i18n 翻译 | `admin/.../locales/langs/` | ⬜ |

### 2.5 构建验证

| # | 任务 | 文件/操作 | 状态 |
|---|------|----------|------|
| 2.5.1 | 重建 admin 镜像 | `podman-compose build --no-cache admin` | ⬜ |
| 2.5.2 | 重建 admin 容器 | `podman-compose up -d --force-recreate admin` | ⬜ |
| 2.5.3 | 前端功能冒烟测试 | 浏览器验证 | ⬜ |

---

## Phase 3：存量路由权限迁移

### 3.1 后端路由权限改造

| # | 任务 | 文件/操作 | 状态 |
|---|------|----------|------|
| 3.1.1 | products 路由接入 `@guard.require_permission` | `backend/.../api/admin/v1/products.py` | ⬜ |
| 3.1.2 | orders 路由接入权限 | `backend/.../api/admin/v1/orders.py` | ⬜ |
| 3.1.3 | shipments 路由接入权限 | `backend/.../api/admin/v1/shipments.py` | ⬜ |
| 3.1.4 | pricing 路由接入权限 | `backend/.../api/admin/v1/pricing.py` | ⬜ |
| 3.1.5 | suppliers 路由接入权限 | `backend/.../api/admin/v1/suppliers.py` | ⬜ |
| 3.1.6 | dashboard/settings/chat_requests 接入权限 | `backend/.../api/admin/v1/*.py` | ⬜ |

### 3.2 require_role 兼容保留

| # | 任务 | 文件/操作 | 状态 |
|---|------|----------|------|
| 3.2.1 | require_role 改为读取真实角色数据 | `backend/.../dependencies.py` | ⬜ |

### 3.3 构建验证

| # | 任务 | 文件/操作 | 状态 |
|---|------|----------|------|
| 3.3.1 | 重启 backend 容器 | `podman-compose restart backend` | ⬜ |
| 3.3.2 | 权限回归测试（不同角色 token 调用各接口） | shell_executor | ⬜ |

---

## Phase 4：端到端验证

### 4.1 全链路测试

| # | 测试场景 | 预期结果 | 状态 |
|---|---------|---------|------|
| 4.1.1 | Admin 登录 → 获取 token + permissions | 200 + permissions 列表 | ⬜ |
| 4.1.2 | 无 token 访问 admin API | 401 | ⬜ |
| 4.1.3 | operator 角色访问 suppliers 接口 | 403 | ⬜ |
| 4.1.4 | support 角色访问 orders 接口 | 200（仅 view/refund 可操作） | ⬜ |
| 4.1.5 | 创建用户 → 分配角色 → 用新用户登录 | 新用户权限生效 | ⬜ |
| 4.1.6 | 修改角色权限 → 用户权限即时更新 | 权限变更实时生效 | ⬜ |
| 4.1.7 | 禁用用户 → token 失效 | 403 Account deactivated | ⬜ |
| 4.1.8 | 前端按钮级权限：operator 看不到"管理供应商"按钮 | 按钮隐藏 | ⬜ |

### 4.2 容器状态检查

| # | 任务 | 状态 |
|---|------|------|
| 4.2.1 | backend 容器运行正常 + 日志无报错 | ⬜ |
| 4.2.2 | admin 容器运行正常 + 日志无报错 | ⬜ |

---

## 中断恢复指南

如果任务被中断，下次继续时告诉我 **"继续 RBAC 任务"**，我会：

1. 读取 `docs/IMPLEMENTATION-PLAN-RBAC.md`
2. 读取 `docs/DEV-RULES.md`
3. 找到第一个 ⬜ 状态的任务
4. 从该任务继续执行

---

*最后更新：2026-07-20*
