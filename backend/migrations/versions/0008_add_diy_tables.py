"""add_diy_tables

Revision ID: 0008_add_diy_tables
Revises: 0007_add_site_profiles
Create Date: 2026-07-29

新增 DIY 页面装修功能的三张表：
- diy_pages            页面定义
- diy_components       组件库（含 15 个系统内置组件种子数据）
- diy_page_components  页面组件实例
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0008_add_diy_tables'
down_revision: Union[str, None] = '0007_add_site_profiles'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SYSTEM_COMPONENTS = [
    # --- 基础组件 ---
    ('banner', '轮播横幅', 'basic', 'mdi:view-carousel',
     '{"slides":[],"autoplay":true,"interval":3000,"height":375}',
     '{"type":"object","properties":{"slides":{"type":"array","items":{"type":"object","properties":{"image":{"type":"string","title":"图片"},"link":{"type":"string","title":"链接"}}}},"autoplay":{"type":"boolean","title":"自动播放"},"interval":{"type":"integer","title":"间隔(ms)","default":3000},"height":{"type":"integer","title":"高度(px)","default":375}}}',
     1),
    ('search_box', '搜索框', 'basic', 'mdi:magnify',
     '{"placeholder":"Search products...","style":"simple","backgroundColor":"#ffffff"}',
     '{"type":"object","properties":{"placeholder":{"type":"string","title":"占位文字"},"style":{"type":"string","enum":["simple","rounded","with-categories"],"title":"样式"},"backgroundColor":{"type":"string","title":"背景色"}}}',
     2),
    ('image_ad', '图片广告', 'basic', 'mdi:image',
     '{"image":"","link":"","mode":"full_width","height":200}',
     '{"type":"object","properties":{"image":{"type":"string","title":"图片"},"link":{"type":"string","title":"链接"},"mode":{"type":"string","enum":["full_width","card"],"title":"展示模式"},"height":{"type":"integer","title":"高度(px)"}}}',
     3),
    ('text_block', '文本模块', 'basic', 'mdi:text',
     '{"content":"","textAlign":"left","fontSize":14,"color":"#333333","backgroundColor":"transparent","padding":16}',
     '{"type":"object","properties":{"content":{"type":"string","title":"内容","ui:widget":"textarea"},"textAlign":{"type":"string","enum":["left","center","right"],"title":"对齐"},"fontSize":{"type":"integer","title":"字号"},"color":{"type":"string","title":"文字颜色"}}}',
     4),
    ('rich_text', '富文本', 'basic', 'mdi:format-text',
     '{"content":"","padding":16}',
     '{"type":"object","properties":{"content":{"type":"string","title":"内容","ui:widget":"rich-editor"},"padding":{"type":"integer","title":"内边距"}}}',
     5),
    ('video', '视频模块', 'basic', 'mdi:video',
     '{"url":"","poster":"","autoplay":false,"loop":false}',
     '{"type":"object","properties":{"url":{"type":"string","title":"视频地址"},"poster":{"type":"string","title":"封面图"},"autoplay":{"type":"boolean","title":"自动播放"}}}',
     6),
    ('divider', '分割线', 'basic', 'mdi:minus',
     '{"style":"solid","color":"#e5e5e5","height":1,"margin":0}',
     '{"type":"object","properties":{"style":{"type":"string","enum":["solid","dashed","dotted"],"title":"线型"},"color":{"type":"string","title":"颜色"}}}',
     7),
    # --- 商品组件 ---
    ('goods_list', '商品列表', 'goods', 'mdi:package-variant',
     '{"title":"Hot Products","source":"manual","category":"","productIds":[],"displayCount":6,"layout":"grid","columns":2,"showPrice":true,"showCartButton":true}',
     '{"type":"object","properties":{"title":{"type":"string","title":"标题"},"source":{"type":"string","enum":["manual","category","ai_recommend"],"title":"数据源"},"category":{"type":"string","title":"分类"},"productIds":{"type":"array","items":{"type":"string"},"title":"手动选品"},"displayCount":{"type":"integer","title":"展示数量"},"layout":{"type":"string","enum":["grid","list","scroll"],"title":"布局"},"columns":{"type":"integer","title":"列数"}}}',
     10),
    ('goods_single', '单商品卡片', 'goods', 'mdi:card',
     '{"productId":"","layout":"vertical"}',
     '{"type":"object","properties":{"productId":{"type":"string","title":"商品ID","ui:widget":"product-picker"},"layout":{"type":"string","enum":["vertical","horizontal"],"title":"布局"}}}',
     11),
    ('goods_group', '商品分组', 'goods', 'mdi:view-grid',
     '{"tabs":[{"name":"Tab 1","category":""}],"displayCount":4,"columns":2}',
     '{"type":"object","properties":{"tabs":{"type":"array","items":{"type":"object","properties":{"name":{"type":"string","title":"Tab名"},"category":{"type":"string","title":"分类"}}},"title":"Tab配置"}}}',
     12),
    # --- 营销组件 ---
    ('coupon', '优惠券', 'marketing', 'mdi:ticket-percent',
     '{"couponId":"","style":"card"}',
     '{"type":"object","properties":{"couponId":{"type":"string","title":"优惠券ID","ui:widget":"coupon-picker"},"style":{"type":"string","enum":["card","banner"],"title":"样式"}}}',
     20),
    ('countdown', '倒计时', 'marketing', 'mdi:timer',
     '{"endTime":"","title":"Limited Time Offer","backgroundColor":"#ff4757","textColor":"#ffffff"}',
     '{"type":"object","properties":{"endTime":{"type":"string","title":"结束时间","ui:widget":"datetime"},"title":{"type":"string","title":"标题"}}}',
     21),
    ('notice_bar', '公告栏', 'marketing', 'mdi:bullhorn',
     '{"text":"","speed":50,"backgroundColor":"#fff7e6","textColor":"#fa8c16","closable":true}',
     '{"type":"object","properties":{"text":{"type":"string","title":"公告文字"},"speed":{"type":"integer","title":"滚动速度"}}}',
     22),
    # --- 布局组件 ---
    ('blank', '空白占位', 'layout', 'mdi:dock-window',
     '{"height":20,"backgroundColor":"transparent"}',
     '{"type":"object","properties":{"height":{"type":"integer","title":"高度(px)"},"backgroundColor":{"type":"string","title":"背景色"}}}',
     30),
    ('nav_group', '导航组', 'layout', 'mdi:apps',
     '{"title":"","items":[],"columns":4}',
     '{"type":"object","properties":{"title":{"type":"string","title":"标题"},"items":{"type":"array","items":{"type":"object","properties":{"icon":{"type":"string","title":"图标"},"text":{"type":"string","title":"文字"},"link":{"type":"string","title":"链接"}}},"title":"导航项"},"columns":{"type":"integer","title":"列数"}}}',
     31),
]


def upgrade() -> None:
    op.create_table(
        'diy_pages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('slug', sa.String(128), nullable=False, unique=True),
        sa.Column('title', sa.String(256), nullable=False, server_default=''),
        sa.Column('description', sa.Text(), nullable=False, server_default=''),
        sa.Column('page_type', sa.String(32), nullable=False, server_default='custom'),
        sa.Column('status', sa.String(16), nullable=False, server_default='draft'),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('admin_users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
    )
    op.create_index('idx_diy_pages_slug', 'diy_pages', ['slug'])
    op.create_index('idx_diy_pages_status', 'diy_pages', ['status'])
    op.create_index('idx_diy_pages_type', 'diy_pages', ['page_type'])

    op.create_table(
        'diy_components',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('code', sa.String(64), nullable=False, unique=True),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('category', sa.String(32), nullable=False, server_default='basic'),
        sa.Column('icon', sa.String(64), nullable=False, server_default='mdi:widget'),
        sa.Column('default_config', postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('config_schema', postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('is_system', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
    )
    op.create_index('idx_diy_components_category', 'diy_components', ['category'])

    op.create_table(
        'diy_page_components',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('page_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('diy_pages.id', ondelete='CASCADE'), nullable=False),
        sa.Column('component_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('diy_components.id'), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('config', postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('is_visible', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
    )
    op.create_index('idx_dpc_page_id', 'diy_page_components', ['page_id'])
    op.create_index('idx_dpc_page_sort', 'diy_page_components', ['page_id', 'sort_order'])

    # --- 系统内置组件种子数据 ---
    import json

    components_table = sa.table(
        'diy_components',
        sa.column('code', sa.String),
        sa.column('name', sa.String),
        sa.column('category', sa.String),
        sa.column('icon', sa.String),
        sa.column('default_config', postgresql.JSONB),
        sa.column('config_schema', postgresql.JSONB),
        sa.column('sort_order', sa.Integer),
    )
    op.bulk_insert(
        components_table,
        [
            {
                'code': code,
                'name': name,
                'category': category,
                'icon': icon,
                'default_config': json.loads(default_config),
                'config_schema': json.loads(config_schema),
                'sort_order': sort_order,
            }
            for code, name, category, icon, default_config, config_schema, sort_order
            in SYSTEM_COMPONENTS
        ],
    )


def downgrade() -> None:
    op.drop_table('diy_page_components')
    op.drop_table('diy_components')
    op.drop_table('diy_pages')
