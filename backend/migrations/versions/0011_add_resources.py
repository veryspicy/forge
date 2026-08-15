"""add_resources

Revision ID: 0011_add_resources
Revises: 0010_drop_diy_tables
Create Date: 2026-08-16

新增资源管理模块两张表：
- resource      资源登记表（全站唯一上传入口，软删）
- resource_ref  资源引用关系表（引用位置追踪）
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0011_add_resources'
down_revision: Union[str, None] = '0010_drop_diy_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "resource",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bucket", sa.String(128), nullable=False, server_default=""),
        sa.Column("object_key", sa.String(512), nullable=False, server_default=""),
        sa.Column("url", sa.String(1024), nullable=False, server_default=""),
        sa.Column("file_type", sa.String(32), nullable=False, server_default="document"),
        sa.Column("mime", sa.String(128), nullable=False, server_default=""),
        sa.Column("file_size", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("sha256", sa.String(64), nullable=True),
        sa.Column("name", sa.String(255), nullable=False, server_default=""),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=False), nullable=True),
    )
    op.create_index("ix_resource_site_id", "resource", ["site_id"])
    op.create_index("ix_resource_deleted_at", "resource", ["deleted_at"])

    op.create_table(
        "resource_ref",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ref_type", sa.String(64), nullable=False, server_default=""),
        sa.Column("ref_id", sa.String(128), nullable=False, server_default=""),
        sa.Column("ref_label", sa.String(255), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_resource_ref_resource_id", "resource_ref", ["resource_id"])
    op.create_index("ix_resource_ref_ref_type_ref_id", "resource_ref", ["ref_type", "ref_id"])


def downgrade() -> None:
    op.drop_table("resource_ref")
    op.drop_table("resource")
