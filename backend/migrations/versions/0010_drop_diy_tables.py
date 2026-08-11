"""drop_diy_tables

Revision ID: 0010_drop_diy_tables
Revises: 0009_seed_system_diy_pages
Create Date: 2026-08-12

删除 DIY 页面装修相关表（diy_page_components / diy_components / diy_pages）。
原因：admin 端"页面装修"功能重构为"站点配置"，不再需要页面/组件/结构编辑。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0010_drop_diy_tables'
down_revision: Union[str, None] = '0009_seed_system_diy_pages'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table('diy_page_components')
    op.drop_table('diy_components')
    op.drop_table('diy_pages')


def downgrade() -> None:
    # 重建 diy_pages
    op.create_table(
        'diy_pages',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('slug', sa.String(128), nullable=False, unique=True),
        sa.Column('title', sa.String(256), nullable=False, server_default=''),
        sa.Column('description', sa.Text(), nullable=False, server_default=''),
        sa.Column('page_type', sa.String(32), nullable=False, server_default='custom'),
        sa.Column('status', sa.String(16), nullable=False, server_default='draft'),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('is_template', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('industry_tag', sa.String(64), nullable=True),
        sa.Column('template_thumbnail', sa.String(512), nullable=True),
        sa.Column('template_description', sa.Text(), nullable=True),
        sa.Column('snapshot_config', postgresql.JSONB(), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_table(
        'diy_components',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('code', sa.String(64), nullable=False, unique=True),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('category', sa.String(32), nullable=False, server_default='basic'),
        sa.Column('icon', sa.String(64), nullable=False, server_default='mdi:widget'),
        sa.Column('default_config', postgresql.JSONB(), nullable=False, server_default=sa.text('\'{}\'')),
        sa.Column('config_schema', postgresql.JSONB(), nullable=False, server_default=sa.text('\'{}\'')),
        sa.Column('is_system', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_table(
        'diy_page_components',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('page_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('diy_pages.id', ondelete='CASCADE'), nullable=False),
        sa.Column('component_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('diy_components.id'), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('config', postgresql.JSONB(), nullable=False, server_default=sa.text('\'{}\'')),
        sa.Column('is_visible', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
