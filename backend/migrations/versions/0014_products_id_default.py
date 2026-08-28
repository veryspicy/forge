"""add_products_id_default

Revision ID: 0014_products_id_default
Revises: 0013_product_status_images
Create Date: 2026-08-18

修复：products.id 缺少数据库默认值。
- 初始 migration（84e64df81995）建表时 id 列为 UUID NOT NULL 但未设 DEFAULT，
  ORM 的 server_default="gen_random_uuid()" 只影响建表 DDL，未落到现有库；
  INSERT 不带 id 时数据库直接报 NOT NULL 违反，导致商品创建 500。
- 本迁移为存量列补上 DEFAULT gen_random_uuid()，仅加默认值，不破坏存量数据。
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0014_products_id_default"
down_revision: str | None = "0013_product_status_images"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE products ALTER COLUMN id SET DEFAULT gen_random_uuid()")


def downgrade() -> None:
    op.execute("ALTER TABLE products ALTER COLUMN id DROP DEFAULT")
