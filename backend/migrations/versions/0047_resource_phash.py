"""add phash fingerprint column to resource

Revision ID: 0047_resource_phash
Revises: 0046_product_images_resource_ref
Create Date: 2026-10-26

- resource 表新增 phash 列（64bit 感知哈希 hex，可空），供图片溯源取证（P4）使用
- 同时创建索引便于相似检索（phash 前缀粗筛）
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0047_resource_phash"
down_revision: str | Sequence[str] | None = "0046_product_images_resource_ref"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("resource", sa.Column("phash", sa.String(length=64), nullable=True))
    op.create_index("ix_resource_phash", "resource", ["phash"])


def downgrade() -> None:
    op.drop_index("ix_resource_phash", table_name="resource")
    op.drop_column("resource", "phash")
