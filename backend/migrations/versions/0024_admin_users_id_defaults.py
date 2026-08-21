"""admin_users_id_defaults

Revision ID: 0024_admin_users_id_defaults
Revises: 0023_admin_rbac_db
Create Date: 2026-08-21

补齐 admin_users 表 id / created_at / updated_at 列的 DEFAULT
（手工建表缺失，导致 ORM server_default 依赖落空，新建管理员失败）。
幂等：ALTER COLUMN SET DEFAULT 可重复执行。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0024_admin_users_id_defaults"
down_revision: str | None = "0023_admin_rbac_db"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for col, default in [
        ("id", "gen_random_uuid()"),
        ("created_at", "now()"),
        ("updated_at", "now()"),
    ]:
        op.execute(sa.text(f"ALTER TABLE admin_users ALTER COLUMN {col} SET DEFAULT {default}"))


def downgrade() -> None:
    for col in ("id", "created_at", "updated_at"):
        op.execute(sa.text(f"ALTER TABLE admin_users ALTER COLUMN {col} DROP DEFAULT"))
