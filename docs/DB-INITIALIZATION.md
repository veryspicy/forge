# Forge 数据库初始化与 Alembic 迁移权威手册

> 适用范围：本地 dev 库重建、全新环境（生产/预发）空库初始化、老库升级。
> 结论先行：**建表/改表的唯一权威途径是 Alembic 迁移链**（`backend/migrations/versions/`）。仓库内不存在也不维护"独立建表 SQL"；`k8s/database/postgres/init-scripts/01-init.sql` 只建 PostgreSQL 扩展、不建任何业务表。

## 1. 术语与基线

| 项目 | 说明 |
|---|---|
| 迁移链 | `<base>` → `84e64df81995`(initial schema) → `prod_admin_users_bootstrap` → `c11c8ddca4bc` → `0007`~`0032` → `0033_bootstrap_admin_account`(head) |
| 版本表 | `alembic_version.version_num VARCHAR(255)`。alembic 默认建 `VARCHAR(32)`，装不下长 revision id（如 `0030_users_pet_profiles_id_defaults` 共 35 字符）会报 `StringDataRightTruncationError`；`env.py` 已做空库预建加宽版本表，无需手工处理 |
| admin_users | 历史上从未在早期迁移中建表（0008 起即被外键引用）。已在 `84e64df81995` 之后插入幂等 bootstrap 迁移自举该表（老库 has_table 跳过），空库不再断链 |
| 种子数据 | RBAC（roles/permissions）由 `0023_admin_rbac_db` 迁移自带；默认管理员 `admin@forge.dev / admin123` 由 head 迁移 `0033_bootstrap_admin_account` 幂等写入（已存在则跳过，不覆盖密码） |

## 2. 空库/全新库初始化（生产、预发、CI）

按顺序执行以下三步，缺一不可：

```bash
# ① 扩展初始化（幂等，可重复执行）
# 容器场景示例（podman）：
podman exec <postgres-container> psql -U postgres -d forge \
  -f /path/to/k8s/database/postgres/init-scripts/01-init.sql

# ② Alembic 迁移（容器内执行，禁止本地直连业务库）
cd D:\codeRepo\forge\backend
# 将新迁移与 ini 注入运行容器（若镜像已含最新源码可跳过 cp）
podman cp migrations forge-backend:/app/migrations
podman cp alembic.ini forge-backend:/app/alembic.ini   # 容器内需将 sqlalchemy.url 指向 postgres:5432/forge
podman exec forge-backend python -m alembic -c /app/alembic.ini upgrade head

# ③ 验收（必须做，禁止凭"没报错"收工）
podman exec forge-backend python - <<'PY'
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
e = create_async_engine("postgresql+asyncpg://postgres:postgres@postgres:5432/forge")
async def main():
    async with e.connect() as c:
        print("head:", (await c.execute(text("SELECT version_num FROM alembic_version"))).scalar())
        print("admin:", (await c.execute(text("SELECT email, role, is_active FROM admin_users"))).all())
        print("roles/perms:", (await c.execute(text("SELECT (SELECT count(*) FROM roles), (SELECT count(*) FROM permissions)"))).one())
asyncio.run(main())
PY
```

验收通过标准（2026-09-08 实测）：

- `alembic_version = 0033_bootstrap_admin_account`
- `admin_users` 恰有 1 条 `admin@forge.dev / role=super_admin / is_active=t`，bcrypt(`admin123`) 校验通过，且 `admin_user_roles` 关联 super_admin
- `roles = 4`、`permissions = 39`、`admin_user_roles = 1`

## 3. 老库升级（已有数据环境）

```bash
# ① 先备份（必须）
podman exec <postgres-container> pg_dump -U postgres -d forge > forge_backup_$(date +%Y%m%d).sql

# ② 升级
cd D:\codeRepo\forge\backend
podman cp migrations forge-backend:/app/migrations
podman cp alembic.ini forge-backend:/app/alembic.ini
podman exec forge-backend python -m alembic -c /app/alembic.ini upgrade head

# ③ 核对版本与关键数据行数（roles/permissions/admin 不得重复）
```

老库特性：bootstrap 与 0033 均幂等（`has_table` / `ON CONFLICT DO NOTHING`），升级路径只执行缺失 revision，已存在的默认账号密码不会被覆盖。

## 4. 排障速查

| 症状 | 原因 | 处理 |
|---|---|---|
| `StringDataRightTruncationError ... version_num` | 版本表为旧版 `VARCHAR(32)` 且迁移链含 >32 字符 revision id（0030 及以上） | `ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(255);` 后重跑 |
| 0008 外键失败：`admin_users` 不存在 | 使用旧链/绕过 bootstrap 直接跑到 0008 | 确保迁移目录包含 `prod_admin_users_bootstrap.py` 且位于 `84e64df81995` 之后 |
| `alembic upgrade head` 报 migration 目录未初始化 | script_location 相对路径错误（ini 不在迁移所在根目录） | ini 与 migrations 同级放置；容器内统一放 `/app/` |
| 误用 `create_all` | models.py 仅映射不建表，create_all 无任何效果 | 一律走迁移链，见本文档 |
| `File contains no section headers` | ini 带 UTF-8 BOM | 以无 BOM UTF-8 重写 alembic.ini（PowerShell 5.1 `Set-Content -Encoding UTF8` 会带 BOM，改用 `[System.IO.File]::WriteAllText(..., UTF8Encoding($false))`） |

## 5. 新增迁移的固定流程（防止回归）

1. `models.py` 改 ORM → 手写迁移（参照相邻版本，含 `downgrade`）
2. 空库实测：临时起全新 postgres 容器 → 跑 ② 的 upgrade head → 数据验收（见第 2 节）
3. 老库实测：备份后升级 → 核对无重复/无覆盖
4. `ruff check` / `mypy`（backend 门槛）→ Conventional Commits 提交
