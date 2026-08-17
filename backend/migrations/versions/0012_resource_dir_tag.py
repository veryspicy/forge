"""add_resource_directory_and_tags

Revision ID: 0012_resource_dir_tag
Revises: 0011_add_resources
Create Date: 2026-08-17

目录 + 标签体系：
- resource 表新增 directory 字段（目录路径，如 产品图/春季）
- 新增 resource_tag 标签表（全局标签，name 唯一）
- 新增 resource_tag_map 资源-标签多对多关联表
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0012_resource_dir_tag'
down_revision: Union[str, None] = '0011_add_resources'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # resource.directory：目录路径（正斜杠分隔），空串表示未归档
    op.add_column(
        "resource",
        sa.Column("directory", sa.String(255), nullable=False, server_default=""),
    )
    op.create_index("ix_resource_directory", "resource", ["directory"])

    # 标签表（全局标签，name 唯一）
    op.create_table(
        "resource_tag",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("uq_resource_tag_name", "resource_tag", ["name"], unique=True)

    # 资源-标签关联表
    op.create_table(
        "resource_tag_map",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tag_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_resource_tag_map_resource_id", "resource_tag_map", ["resource_id"])
    op.create_index("ix_resource_tag_map_tag_id", "resource_tag_map", ["tag_id"])
    op.create_index("uq_resource_tag_map_pair", "resource_tag_map", ["resource_id", "tag_id"], unique=True)


def downgrade() -> None:
    op.drop_table("resource_tag_map")
    op.drop_table("resource_tag")
    op.drop_index("ix_resource_directory", table_name="resource")
    op.drop_column("resource", "directory")
