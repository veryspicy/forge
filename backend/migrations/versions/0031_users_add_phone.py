"""users_add_phone

Revision ID: 0031_users_add_phone
Revises: 0030_users_pet_profiles_id_defaults
Create Date: 2026-09-04

C 端客户管理扩展：users 表新增 phone 字段（非必填，可搜索，后期探索用途）。
幂等：ADD COLUMN IF NOT EXISTS / CREATE INDEX IF NOT EXISTS 可重复执行。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0031_users_add_phone"
down_revision: str | Sequence[str] | None = "0030_users_id_defaults"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(sa.text("ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(50)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_users_phone ON users (phone)"))


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS ix_users_phone"))
    op.execute(sa.text("ALTER TABLE users DROP COLUMN IF EXISTS phone"))
