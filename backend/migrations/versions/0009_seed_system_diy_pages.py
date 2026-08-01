"""seed_system_diy_pages

Revision ID: 0009_seed_system_diy_pages
Revises: 0008_add_diy_tables
Create Date: 2026-07-30

种子数据：为 diy_pages 表插入 3 个 C 端系统页面（home / category / product_detail），
配合 list_site_pages 返回 system 卡片列表。
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0009_seed_system_diy_pages'
down_revision: Union[str, None] = '0008_add_diy_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO diy_pages (name, slug, title, page_type, status)
        VALUES
            ('Home',             'home',             'Home Page',             'home',             'draft'),
            ('Category',         'category',         'Category Page',         'category',         'draft'),
            ('Product Detail',   'product_detail',   'Product Detail Page',   'product_detail',   'draft')
        ON CONFLICT (slug) DO NOTHING
    """)


def downgrade() -> None:
    op.execute(
        "DELETE FROM diy_pages WHERE page_type IN ('home', 'category', 'product_detail')"
    )
