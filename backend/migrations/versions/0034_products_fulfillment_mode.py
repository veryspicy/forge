"""products_fulfillment_mode

Revision ID: 0034_products_fulfillment_mode
Revises: 0033_bootstrap_admin_account
Create Date: 2026-09-10

双模式履约改造（PLAN-DUAL-FULFILLMENT）：
1. products 新增 fulfillment_mode ∈ {self, dropship}，默认 self（老商品一律自采购）
2. order_items 新增履约快照列：fulfillment_mode / supplier_id / supplier_sku
   - 快照语义：supplier_id 故意不建外键，供应商停用/删除不影响历史订单可读性
幂等：ADD COLUMN IF NOT EXISTS / CREATE INDEX IF NOT EXISTS / DO 块兜底重复约束，可重复执行。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0034_products_fulfillment_mode"
down_revision: str | Sequence[str] | None = "0033_bootstrap_admin_account"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. 商品履约模式
    op.execute(
        sa.text("ALTER TABLE products ADD COLUMN IF NOT EXISTS fulfillment_mode VARCHAR(20) NOT NULL DEFAULT 'self'")
    )
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                ALTER TABLE products
                    ADD CONSTRAINT ck_products_fulfillment_mode
                    CHECK (fulfillment_mode IN ('self', 'dropship'));
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END $$;
            """
        )
    )
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_products_fulfillment_mode ON products (fulfillment_mode)"))

    # 2. 订单行履约快照（不拆单，按行承载来源）
    op.execute(sa.text("ALTER TABLE order_items ADD COLUMN IF NOT EXISTS fulfillment_mode VARCHAR(20)"))
    op.execute(sa.text("ALTER TABLE order_items ADD COLUMN IF NOT EXISTS supplier_id UUID"))
    op.execute(sa.text("ALTER TABLE order_items ADD COLUMN IF NOT EXISTS supplier_sku VARCHAR(255)"))


def downgrade() -> None:
    op.execute(sa.text("ALTER TABLE order_items DROP COLUMN IF EXISTS supplier_sku"))
    op.execute(sa.text("ALTER TABLE order_items DROP COLUMN IF EXISTS supplier_id"))
    op.execute(sa.text("ALTER TABLE order_items DROP COLUMN IF EXISTS fulfillment_mode"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_products_fulfillment_mode"))
    op.execute(sa.text("ALTER TABLE products DROP CONSTRAINT IF EXISTS ck_products_fulfillment_mode"))
    op.execute(sa.text("ALTER TABLE products DROP COLUMN IF EXISTS fulfillment_mode"))
