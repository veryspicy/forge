"""add_admin_users_role

Revision ID: 0022_admin_rbac_role
Revises: 0021_mcp_server
Create Date: 2026-08-21

Admin RBAC 落地：
- admin_users 增加 role 列（super_admin / operator / support），存量账号默认 super_admin
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0022_admin_rbac_role"
down_revision: str | None = "0021_mcp_server"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "admin_users",
        sa.Column("role", sa.String(20), nullable=False, server_default="super_admin"),
    )
    op.create_index("ix_admin_users_role", "admin_users", ["role"])


def downgrade() -> None:
    op.drop_index("ix_admin_users_role", table_name="admin_users")
    op.drop_column("admin_users", "role")
