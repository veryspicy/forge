"""order refund (line-level) and line-level procurement

Revision ID: 0035_order_refund_line_procure
Revises: 0034_products_fulfillment_mode
Create Date: 2026-09-11

取消/退款语义收敛 + 粒度对齐（行业：Shopify orderCancel(refund, restock) / refundCreate）：
1. orders.refunded_amount：累计已退金额（含商品/税/运费），支撑上限校验与列表展示
2. orders.refunds：退款流水 JSONB（每笔含 items/运费/税/原因/经手人）
   - payment_status 复用既有列取值：unpaid / paid / partially_refunded / refunded（不新增终态）
3. order_items.refunded_quantity：行级已退数量（部分退款不影响剩余行发货）
4. order_items 行级采购：procurement_status ∈ {requested, received} + 时间戳 + 成本
   - 采购是行级旁支动作，不改订单主状态（对齐 Shopify PO / 聚水潭采购单）
幂等：ADD COLUMN IF NOT EXISTS 可重复执行。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0035_order_refund_line_procure"
down_revision: str | Sequence[str] | None = "0034_products_fulfillment_mode"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. 订单级退款累计与流水
    op.execute(sa.text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS refunded_amount NUMERIC(12, 2) NOT NULL DEFAULT 0"))
    op.execute(sa.text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS refunds JSONB"))

    # 2. 行级退款数量
    op.execute(sa.text("ALTER TABLE order_items ADD COLUMN IF NOT EXISTS refunded_quantity INTEGER NOT NULL DEFAULT 0"))

    # 3. 行级采购
    op.execute(sa.text("ALTER TABLE order_items ADD COLUMN IF NOT EXISTS procurement_status VARCHAR(20)"))
    op.execute(sa.text("ALTER TABLE order_items ADD COLUMN IF NOT EXISTS procurement_requested_at TIMESTAMP"))
    op.execute(sa.text("ALTER TABLE order_items ADD COLUMN IF NOT EXISTS procurement_received_at TIMESTAMP"))
    op.execute(sa.text("ALTER TABLE order_items ADD COLUMN IF NOT EXISTS procurement_cost NUMERIC(12, 2)"))
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                ALTER TABLE order_items
                    ADD CONSTRAINT ck_order_items_procurement_status
                    CHECK (procurement_status IN ('requested', 'received'));
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END $$;
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("ALTER TABLE order_items DROP CONSTRAINT IF EXISTS ck_order_items_procurement_status"))
    op.execute(sa.text("ALTER TABLE order_items DROP COLUMN IF EXISTS procurement_cost"))
    op.execute(sa.text("ALTER TABLE order_items DROP COLUMN IF EXISTS procurement_received_at"))
    op.execute(sa.text("ALTER TABLE order_items DROP COLUMN IF EXISTS procurement_requested_at"))
    op.execute(sa.text("ALTER TABLE order_items DROP COLUMN IF EXISTS procurement_status"))
    op.execute(sa.text("ALTER TABLE order_items DROP COLUMN IF EXISTS refunded_quantity"))
    op.execute(sa.text("ALTER TABLE orders DROP COLUMN IF EXISTS refunds"))
    op.execute(sa.text("ALTER TABLE orders DROP COLUMN IF EXISTS refunded_amount"))
