"""admin_rbac_matrix_extend

Revision ID: 0025_admin_rbac_matrix_extend
Revises: 0024_admin_users_id_defaults
Create Date: 2026-08-21

RBAC 权限矩阵增量扩展（幂等）：
- 补齐管理类模块权限码（suppliers / supplier_sources / settings /
  site_config / site_profile / admin_roles / admin_users / users / mcp_keys）
- 分配给 admin 角色（super_admin 通配不建关联；operator/support 不授予管理类权限）
- 不触碰已有 21 条业务权限与现有角色-权限关联
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0025_admin_rbac_matrix_extend"
down_revision: str | None = "0024_admin_users_id_defaults"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (module, code, display_name) — 管理类模块权限（仅 admin 及以上）
ADMIN_PERMISSION_DEFS: list[tuple[str, str, str]] = [
    ("suppliers", "suppliers:view", "供应商管理-查看"),
    ("suppliers", "suppliers:manage", "供应商管理-管理"),
    ("supplier_sources", "supplier_sources:view", "货源管理-查看"),
    ("supplier_sources", "supplier_sources:manage", "货源管理-管理"),
    ("settings", "settings:view", "系统设置-查看"),
    ("settings", "settings:manage", "系统设置-管理"),
    ("site_config", "site_config:view", "站点配置-查看"),
    ("site_config", "site_config:manage", "站点配置-管理"),
    ("site_profile", "site_profile:view", "站点资料-查看"),
    ("site_profile", "site_profile:manage", "站点资料-管理"),
    ("admin_roles", "admin_roles:view", "角色管理-查看"),
    ("admin_roles", "admin_roles:manage", "角色管理-管理"),
    ("admin_users", "admin_users:view", "管理员-查看"),
    ("admin_users", "admin_users:manage", "管理员-管理"),
    ("users", "users:view", "用户管理-查看"),
    ("users", "users:manage", "用户管理-管理"),
    ("mcp_keys", "mcp_keys:view", "MCP 密钥-查看"),
    ("mcp_keys", "mcp_keys:manage", "MCP 密钥-管理"),
]

ADMIN_CODES: list[str] = [code for _, code, _ in ADMIN_PERMISSION_DEFS]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("permissions") or not inspector.has_table("role_permissions"):
        # 前置 migration 未建表时跳过（异常场景，保证幂等）
        return

    # ---- 1. 补齐权限码（幂等）----
    for module, code, display in ADMIN_PERMISSION_DEFS:
        op.execute(
            sa.text(
                "INSERT INTO permissions (id, code, display_name, module, created_at) "
                "VALUES (gen_random_uuid(), :code, :display, :module, now()) "
                "ON CONFLICT (code) DO UPDATE SET display_name = EXCLUDED.display_name, module = EXCLUDED.module"
            ).bindparams(code=code, display=display, module=module)
        )

    # ---- 2. 分配给 admin 角色（super_admin 通配；operator/support 不授予）----
    op.execute(
        sa.text(
            "INSERT INTO role_permissions (role_id, permission_id) "
            "SELECT r.id, p.id FROM roles r, permissions p "
            "WHERE r.name = 'admin' AND p.code IN :codes "
            "ON CONFLICT DO NOTHING"
        ).bindparams(sa.bindparam("codes", expanding=True), codes=ADMIN_CODES)
    )


def downgrade() -> None:
    # 仅移除 admin 角色对管理类权限的关联；权限码保留（其它角色可能引用）
    op.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE role_id IN "
            "(SELECT id FROM roles WHERE name = 'admin') "
            "AND permission_id IN (SELECT id FROM permissions WHERE code IN :codes)"
        ).bindparams(sa.bindparam("codes", expanding=True), codes=ADMIN_CODES)
    )
