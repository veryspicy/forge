"""users_pet_profiles_id_defaults

Revision ID: 0030_users_pet_profiles_id_defaults
Revises: 0029_products_attributes
Create Date: 2026-09-02

修复 users / pet_profiles 手工建表缺失 id / created_at / updated_at 列 DEFAULT
（与 0024 admin_users 同因：ORM server_default 依赖落空，INSERT 违反 NOT NULL）。
幂等：ALTER COLUMN SET DEFAULT 可重复执行。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0030_users_pet_profiles_id_defaults"
down_revision: str | Sequence[str] | None = "0029_products_attributes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _set_defaults(table: str) -> None:
    for col, default in [
        ("id", "gen_random_uuid()"),
        ("created_at", "now()"),
        ("updated_at", "now()"),
    ]:
        op.execute(sa.text(f"ALTER TABLE {table} ALTER COLUMN {col} SET DEFAULT {default}"))


def upgrade() -> None:
    _set_defaults("users")
    _set_defaults("pet_profiles")


def downgrade() -> None:
    for table in ("users", "pet_profiles"):
        for col in ("id", "created_at", "updated_at"):
            op.execute(sa.text(f"ALTER TABLE {table} ALTER COLUMN {col} DROP DEFAULT"))
