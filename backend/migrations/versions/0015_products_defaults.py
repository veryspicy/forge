"""add_products_defaults

Revision ID: 0015_products_defaults
Revises: 0014_products_id_default
Create Date: 2026-08-18

修复：products 表其余缺失数据库默认值的列（初始 migration 只建列未设 DEFAULT，
ORM 的 server_default 不落到存量库，INSERT 缺列即报 NOT NULL 违反）。
- created_at / updated_at：SET DEFAULT now()（ORM 声明 server_default="now()"）
- cost：SET DEFAULT 0（成本价创建时可省略，API 层默认 0.0）
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0015_products_defaults"
down_revision: str | None = "0014_products_id_default"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE products ALTER COLUMN cost SET DEFAULT 0")
    op.execute("ALTER TABLE products ALTER COLUMN created_at SET DEFAULT now()")
    op.execute("ALTER TABLE products ALTER COLUMN updated_at SET DEFAULT now()")


def downgrade() -> None:
    op.execute("ALTER TABLE products ALTER COLUMN updated_at DROP DEFAULT")
    op.execute("ALTER TABLE products ALTER COLUMN created_at DROP DEFAULT")
    op.execute("ALTER TABLE products ALTER COLUMN cost DROP DEFAULT")
