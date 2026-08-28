"""admin_rbac_db_authoritative

Revision ID: 0023_admin_rbac_db
Revises: 0022_admin_rbac_role
Create Date: 2026-08-21

RBAC DB 权威化（幂等，兼容表已手工存在场景）：
- 幂等创建 roles / permissions / role_permissions / admin_user_roles
- 补齐已存在表的 id / 时间列 DEFAULT（gen_random_uuid / now()）
- 以 backend/src/forge/main/rbac.py 的 ROLE_PERMISSIONS 矩阵为权威同步权限种子：
  清过时权限、补缺失权限、重建角色-权限关联
- 按 admin_users.role 回填 admin_user_roles 关联（现有账号立即生效）
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0023_admin_rbac_db"
down_revision: str | None = "0022_admin_rbac_role"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# 与 rbac.py 种子定义保持一致：(module, code, display_name)
PERMISSION_DEFS: list[tuple[str, str, str]] = [
    ("dashboard", "dashboard:view", "数据看板-查看"),
    ("products", "products:view", "商品管理-查看"),
    ("products", "products:create", "商品管理-新建"),
    ("products", "products:edit", "商品管理-编辑"),
    ("products", "products:delete", "商品管理-删除"),
    ("products", "products:status", "商品管理-上下架"),
    ("orders", "orders:view", "订单管理-查看"),
    ("orders", "orders:detail", "订单管理-查看详情"),
    ("orders", "orders:review", "订单管理-审核"),
    ("orders", "orders:procure", "订单管理-采购"),
    ("orders", "orders:logistics", "订单管理-物流"),
    ("orders", "orders:refund", "订单管理-退款"),
    ("pricing", "pricing:view", "定价管理-查看"),
    ("pricing", "pricing:manage", "定价管理-管理"),
    ("ai_probe", "ai_probe:view", "AI 探针-查看"),
    ("chat_requests", "chat_requests:view", "咨询请求-查看"),
    ("chat_requests", "chat_requests:manage", "咨询请求-管理"),
    ("resources", "resources:view", "资源管理-查看"),
    ("resources", "resources:upload", "资源管理-上传"),
    ("shipments", "shipments:view", "发货管理-查看"),
    ("shipments", "shipments:manage", "发货管理-管理"),
]

OPERATOR_CODES = [
    "dashboard:view",
    "products:view",
    "products:create",
    "products:edit",
    "products:delete",
    "products:status",
    "orders:view",
    "orders:detail",
    "orders:review",
    "orders:procure",
    "orders:logistics",
    "orders:refund",
    "pricing:view",
    "pricing:manage",
    "ai_probe:view",
    "chat_requests:view",
    "chat_requests:manage",
    "resources:view",
    "resources:upload",
    "shipments:view",
    "shipments:manage",
]

SUPPORT_CODES = [
    "dashboard:view",
    "orders:view",
    "orders:detail",
    "orders:refund",
    "chat_requests:view",
]

# admin 为兼容旧账号 role=admin 的角色，复用 operator 权限
ROLE_PERM_CODES: dict[str, list[str]] = {
    "operator": OPERATOR_CODES,
    "support": SUPPORT_CODES,
    "admin": OPERATOR_CODES,
}

SYSTEM_ROLES: list[tuple[str, str]] = [
    ("super_admin", "超级管理员"),
    ("admin", "管理员"),
    ("operator", "运营"),
    ("support", "客服"),
]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # ---- 1. 幂等建表 ----
    if not inspector.has_table("roles"):
        op.create_table(
            "roles",
            sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("name", sa.String(50), nullable=False),
            sa.Column("display_name", sa.String(100), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        )
        op.create_index("ix_roles_name", "roles", ["name"], unique=True)
    else:
        # 手工建表缺少 DEFAULT，补齐（幂等）
        for col, default in [("id", "gen_random_uuid()"), ("created_at", "now()"), ("updated_at", "now()")]:
            op.execute(sa.text(f"ALTER TABLE roles ALTER COLUMN {col} SET DEFAULT {default}"))

    if not inspector.has_table("permissions"):
        op.create_table(
            "permissions",
            sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("code", sa.String(100), nullable=False),
            sa.Column("display_name", sa.String(200), nullable=False),
            sa.Column("module", sa.String(50), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        )
        op.create_index("ix_permissions_code", "permissions", ["code"], unique=True)
        op.create_index("ix_permissions_module", "permissions", ["module"])
    else:
        for col, default in [("id", "gen_random_uuid()"), ("created_at", "now()")]:
            op.execute(sa.text(f"ALTER TABLE permissions ALTER COLUMN {col} SET DEFAULT {default}"))

    if not inspector.has_table("role_permissions"):
        op.create_table(
            "role_permissions",
            sa.Column("role_id", sa.UUID(), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
            sa.Column(
                "permission_id",
                sa.UUID(),
                sa.ForeignKey("permissions.id", ondelete="CASCADE"),
                primary_key=True,
            ),
        )

    if not inspector.has_table("admin_user_roles"):
        op.create_table(
            "admin_user_roles",
            sa.Column(
                "admin_user_id",
                sa.UUID(),
                sa.ForeignKey("admin_users.id", ondelete="CASCADE"),
                primary_key=True,
            ),
            sa.Column("role_id", sa.UUID(), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
        )

    # ---- 2. 系统角色种子 ----
    for name, display in SYSTEM_ROLES:
        op.execute(
            sa.text(
                "INSERT INTO roles (id, name, display_name, description, is_system, created_at, updated_at) "
                "VALUES (gen_random_uuid(), :name, :display, NULL, true, now(), now()) "
                "ON CONFLICT (name) DO NOTHING"
            ).bindparams(name=name, display=display)
        )

    # ---- 3. 权限种子同步（矩阵权威）----
    op.execute(sa.text("DELETE FROM role_permissions"))
    matrix_codes = [p[1] for p in PERMISSION_DEFS]
    op.execute(
        sa.text("DELETE FROM permissions WHERE code NOT IN :codes").bindparams(
            sa.bindparam("codes", expanding=True),
            codes=matrix_codes,
        )
    )
    for module, code, display in PERMISSION_DEFS:
        op.execute(
            sa.text(
                "INSERT INTO permissions (id, code, display_name, module, created_at) "
                "VALUES (gen_random_uuid(), :code, :display, :module, now()) "
                "ON CONFLICT (code) DO UPDATE SET display_name = EXCLUDED.display_name, module = EXCLUDED.module"
            ).bindparams(code=code, display=display, module=module)
        )

    # ---- 4. 重建角色-权限关联（super_admin 通配，不建关联）----
    for role_name, perm_codes in ROLE_PERM_CODES.items():
        op.execute(
            sa.text(
                "INSERT INTO role_permissions (role_id, permission_id) "
                "SELECT r.id, p.id FROM roles r, permissions p "
                "WHERE r.name = :role AND p.code IN :codes "
                "ON CONFLICT DO NOTHING"
            ).bindparams(sa.bindparam("codes", expanding=True), role=role_name, codes=perm_codes)
        )

    # ---- 5. 按 admin_users.role 回填多对多关联 ----
    op.execute(
        sa.text(
            "INSERT INTO admin_user_roles (admin_user_id, role_id) "
            "SELECT u.id, r.id FROM admin_users u JOIN roles r ON r.name = u.role "
            "WHERE u.role IS NOT NULL "
            "ON CONFLICT DO NOTHING"
        )
    )


def downgrade() -> None:
    op.drop_table("admin_user_roles")
    op.drop_table("role_permissions")
    op.drop_table("permissions")
    op.drop_table("roles")
