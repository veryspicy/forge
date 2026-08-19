"""add_product_translations

Revision ID: 0018_product_translations
Revises: 0017_pricing
Create Date: 2026-08-19

P1 多语言字段重构：
- products 新增 name_translations / description_translations / ai_description_translations JSONB 列
- 现有 name/description/ai_description 保留为默认语言（en），并回填至 translations
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0018_product_translations"
down_revision: str | None = "0017_pricing"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column(
            "name_translations",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "products",
        sa.Column(
            "description_translations",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "products",
        sa.Column(
            "ai_description_translations",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )

    # 回填现有数据为默认语言 en
    op.execute(
        sa.text(
            """
            UPDATE products
            SET name_translations = jsonb_build_object('en', name)
            WHERE name IS NOT NULL AND name != ''
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE products
            SET description_translations = jsonb_build_object('en', description)
            WHERE description IS NOT NULL AND description != ''
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE products
            SET ai_description_translations = jsonb_build_object('en', ai_description)
            WHERE ai_description IS NOT NULL AND ai_description != ''
            """
        )
    )


def downgrade() -> None:
    op.drop_column("products", "ai_description_translations")
    op.drop_column("products", "description_translations")
    op.drop_column("products", "name_translations")
