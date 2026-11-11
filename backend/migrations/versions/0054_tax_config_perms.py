"""tax config permissions（税费配置）

Revision ID: 0054_tax_config_perms
Revises: 0053_order_tax_snapshot
Create Date: 2026-11-08

新增权限码 ``tax_config:view`` / ``tax_config:manage``，仅授予 admin 角色
（super_admin 走通配 '*'）。定义与 ``forge.main.rbac.ROLE_PERMISSIONS`` 同步。
幂等：ON CONFLICT DO NOTHING / UPDATE，可重复执行。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0054_tax_config_perms"
down_revision: str | Sequence[str] | None = "0053_order_tax_snapshot"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TAX_CONFIG_PERMISSIONS: list[tuple[str, str, str]] = [
    ("tax_config", "tax_config:view", "税费配置-查看"),
    ("tax_config", "tax_config:manage", "税费配置-管理"),
]


def upgrade() -> None:
    for module, code, display in TAX_CONFIG_PERMISSIONS:
        op.execute(
            sa.text(
                "INSERT INTO permissions (id, code, display_name, module, created_at) "
                "VALUES (gen_random_uuid(), :code, :display, :module, now()) "
                "ON CONFLICT (code) DO UPDATE SET display_name = EXCLUDED.display_name, module = EXCLUDED.module"
            ).bindparams(code=code, display=display, module=module)
        )
        op.execute(
            sa.text(
                "INSERT INTO role_permissions (role_id, permission_id) "
                "SELECT r.id, p.id FROM roles r, permissions p "
                "WHERE r.name = 'admin' AND p.code = :code "
                "ON CONFLICT DO NOTHING"
            ).bindparams(code=code)
        )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE permission_id IN "
            "(SELECT id FROM permissions WHERE code IN ('tax_config:view', 'tax_config:manage'))"
        )
    )
    op.execute(sa.text("DELETE FROM permissions WHERE code IN ('tax_config:view', 'tax_config:manage')"))
