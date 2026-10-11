"""product variant attributes translations

Revision ID: 0044_product_variant_attributes_translations
Revises: 0043_product_seo_variant_translations
Create Date: 2026-10-11

- ``product_variants`` 表新增 ``attributes_translations``(JSONB)：变体属性值多语言（Shopify 字段级模型），
  结构 ``{locale: {key: localized_value}}``；``attributes`` 保持基准语言（key 与 value 均为基准）。
  属性键（key）以基准语言录入，各语种仅覆盖 value。
幂等：ADD COLUMN IF NOT EXISTS，可重复执行。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0044_product_variant_attributes_translations"
down_revision: str | Sequence[str] | None = "0043_product_seo_variant_translations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "ALTER TABLE product_variants ADD COLUMN IF NOT EXISTS attributes_translations JSONB DEFAULT '{}'::jsonb NOT NULL"
        )
    )


def downgrade() -> None:
    op.execute(sa.text("ALTER TABLE product_variants DROP COLUMN IF EXISTS attributes_translations"))
