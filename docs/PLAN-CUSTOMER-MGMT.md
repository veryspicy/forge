# PLAN: C 端客户管理（Admin Users 模块重构）

> 分支：feature/customer-mgmt ｜ 状态：实施中 ｜ 创建：2026-09-04

## 1. 背景与现状

Admin 的 Customers（C 端 `users` 表）管理仅前端只读表格 + 错误的"更改角色"弹窗（调 `POST /users/{id}/role`，后端无此路由必 404）；后端仅 `GET /users/` 一个只读端点，缺增删改、详情、状态管理、密码重置。

## 2. 需求范围（用户已确认 2026-09-04）

| # | 需求点 | 决策 |
|---|--------|------|
| 1 | 新增客户 / 管理员代建 | C 端注册为主，**保留管理员后台创建能力** |
| 2 | 扩展字段手机号 | 新增 `phone` 字段，**非必填**，列表可搜索，后期探索用途 |
| 3 | 密码重置 | 首期后台代设密码；**后期需具备邮件重置能力**（本期预留 service 层扩展点） |
| 4 | 删除策略 | 有订单 / 宠物档案的客户**禁止物理删除，仅可冻结**；无业务数据可物理删除 |
| 5 | 前端布局 | 客户详情使用**抽屉 Drawer**（非独立路由页） |

## 3. 字段设计

`users` 表新增：`phone VARCHAR(50) NULL` + 索引（email 已唯一）。不引入手机号唯一约束（非必填、后期探索，避免空串冲突）。

## 4. 后端改动（Phase 1）

| 文件 | 改动 |
|------|------|
| `backend/migrations/versions/0031_users_add_phone.py` | 新增 `phone` 列 + index（幂等） |
| `backend/src/forge/infrastructure/persistence/models.py` | `ORMUser` 增加 `phone` 字段 |
| `backend/src/forge/api/errors.py` | 注册 `CUSTOMER_NOT_FOUND` / `CUSTOMER_CANNOT_DELETE` |
| `backend/src/forge/infrastructure/persistence/repositories/user_repo.py` | list 支持 keyword/status 过滤；create 支持 phone；新增 get_by_id / update / delete / business 关联计数 |
| `backend/src/forge/api/admin/v1/users.py` | 完整 CRUD：GET /（搜索筛选分页）、GET /{id}（含宠物 + 订单聚合）、POST /、PUT /{id}、PUT /{id}/password、DELETE /{id}（保护） |
| `backend/src/forge/api/v1/auth.py` | 登录增加 `is_active` 校验，冻结用户返回 `ACCOUNT_DISABLED` |

权限沿用既有 RBAC：列表/详情 `users:view`，写操作 `users:manage`。
删除保护判定依据：`orders.user_id` / `pet_profiles.owner_id` 存在业务数据 → 拒绝物理删除并提示冻结。
密码 hash 与 C 端注册一致（passlib bcrypt），保证代建客户可直接登录 C 端。

## 5. 前端改动（Phase 2，admin/）

- `admin/src/views/users/index.vue`：整体重构
  - 工具栏：关键词搜索（email/name/phone）+ 状态筛选 + 新增客户按钮（`users:manage`）
  - 列表：姓名 / 邮箱 / 手机号 / 状态(NTag) / 注册时间 / 操作
  - 操作（`users:manage`）：编辑、冻结/解冻、重置密码、删除（危险确认）；行操作"详情"（`users:view`）
  - 客户详情抽屉 Drawer：基础信息 + 宠物档案列表 + 订单统计/列表
- 复用既有 `useAuthStore` 权限判断或 `v-permission` 指令（按仓库既有风格，实施时核对 admin-users 页模式）

## 6. 迁移与部署

1. migration 在容器内执行：`podman exec forge-backend alembic upgrade head`；执行前先 `pg_dump` 备份至 `temp/`
2. Admin 无 HMR：`build --no-cache` + `up -d --force-recreate`
3. 后端 bind mount：重启 backend 容器即可

## 7. 端到端验证清单（§10 / §11.0）

- [ ] migration 落库：`\d users` 见 phone 列 + 索引
- [ ] API 契约：`GET /api/admin/v1/users/?keyword=&status=&page=&page_size=`
- [ ] 代建：`POST /users/` 后可 `POST /api/v1/auth/login` 登录 C 端
- [ ] 冻结：`PUT /users/{id}` is_active=false 后，C 端登录返回 `ACCOUNT_DISABLED`
- [ ] 重置密码：旧密码失效、新密码可登录
- [ ] 删除保护：有订单/宠物档案客户 DELETE → `CUSTOMER_CANNOT_DELETE`；无业务数据客户可删
- [ ] 详情聚合：宠物档案 + 订单统计与 DB 一致
- [ ] 质量门槛：backend ruff/mypy，admin lint/typecheck
- [ ] 前端功能实测（用户验证）：列表搜索/筛选、抽屉详情、冻结/解冻、重置密码、删除

## 8. DoD（§14.4）

质量门槛通过 → e2e 通过 → 用户"验证通过" → merge-dev.ps1 合 dev。
