"""products_attributes_snapshot

Revision ID: 0029_products_attributes_snapshot
Revises: 0028_products_catalog_refactor
Create Date: 2026-08-28

商品体系改造：products 补充 attributes JSONB 读快照列。
- 规格关系表（product_spec_keys/values/variant_specs）为权威；
  products.attributes 仅作读快照，由 SpecRepository.sync_product_attributes 维护。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0029_products_attributes"
down_revision: str | None = "0028_products_catalog_refactor"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column(
            "attributes",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("products", "attributes")
