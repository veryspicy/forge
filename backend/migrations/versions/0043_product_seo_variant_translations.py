"""product seo & variant name translations

Revision ID: 0043_product_seo_variant_translations
Revises: 0042_product_detail_blocks_translations
Create Date: 2026-10-10

- ``products`` 表新增 ``seo_translations``(JSONB)：SEO 多语言覆盖（Shopify 字段级模型），
  结构 ``{locale: {title, description, keywords[]}}``；``seo_title/seo_description/seo_keywords`` 保持基准语言。
- ``product_variants`` 表新增 ``name_translations``(JSONB)：变体展示名多语言，结构 ``{locale: name}``；
  ``name`` 保持基准语言。
幂等：ADD COLUMN IF NOT EXISTS，可重复执行。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0043_product_seo_variant_translations"
down_revision: str | Sequence[str] | None = "0042_product_detail_blocks_translations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "ALTER TABLE products ADD COLUMN IF NOT EXISTS seo_translations JSONB DEFAULT '{}'::jsonb NOT NULL"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE product_variants ADD COLUMN IF NOT EXISTS name_translations JSONB DEFAULT '{}'::jsonb NOT NULL"
        )
    )


def downgrade() -> None:
    op.execute(sa.text("ALTER TABLE products DROP COLUMN IF EXISTS seo_translations"))
    op.execute(sa.text("ALTER TABLE product_variants DROP COLUMN IF EXISTS name_translations"))
