"""after-sales return requests (RMA)

Revision ID: 0036_return_requests
Revises: 0035_order_refund_line_procure
Create Date: 2026-09-12

Batch2 退货退款通道（行业对齐 Shopify Returns / 有赞退货单）：
1. return_requests：退货申请单主表
   - 状态机 requested -> approved -> received -> refunded，旁支 rejected / cancelled / closed
   - 资金动作不在本表：退款统一走 order_repo.admin_refund_order，本表仅记录 refund_id 关联
   - deadline_at：审核通过后寄回截止时间（默认 14 天），超时由调度任务自动 closed(expired)
   - refund_amount：审核时锁定的应退金额（商品+税+可选运费），执行退款时按此校验
2. return_items：退货申请行（快照 order_items 的 name/sku/unit_price，避免订单行变更影响售后凭证）
幂等：CREATE TABLE IF NOT EXISTS / 索引与约束均做存在性判断，可重复执行。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0036_return_requests"
down_revision: str | Sequence[str] | None = "0035_order_refund_line_procure"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS return_requests (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                return_number VARCHAR(50) NOT NULL UNIQUE,
                order_id UUID NOT NULL REFERENCES orders(id),
                user_id UUID NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'requested',
                reason VARCHAR(100) NOT NULL,
                note TEXT,
                refund_method VARCHAR(20) NOT NULL DEFAULT 'original',
                refund_amount NUMERIC(12, 2) NOT NULL DEFAULT 0,
                refund_shipping BOOLEAN NOT NULL DEFAULT false,
                restock BOOLEAN NOT NULL DEFAULT true,
                requested_at TIMESTAMP NOT NULL DEFAULT now(),
                deadline_at TIMESTAMP,
                reviewed_at TIMESTAMP,
                reviewed_by VARCHAR(100),
                review_note TEXT,
                received_at TIMESTAMP,
                refunded_at TIMESTAMP,
                refund_id VARCHAR(64),
                cancelled_at TIMESTAMP,
                closed_reason VARCHAR(200),
                created_at TIMESTAMP NOT NULL DEFAULT now(),
                updated_at TIMESTAMP NOT NULL DEFAULT now()
            )
            """
        )
    )
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_return_requests_order_id ON return_requests (order_id)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_return_requests_user_id ON return_requests (user_id)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_return_requests_status ON return_requests (status)"))

    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS return_items (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                return_id UUID NOT NULL REFERENCES return_requests(id) ON DELETE CASCADE,
                order_item_id UUID NOT NULL REFERENCES order_items(id),
                name VARCHAR(500) NOT NULL,
                sku VARCHAR(100) NOT NULL,
                unit_price NUMERIC(12, 2) NOT NULL,
                quantity INTEGER NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT now()
            )
            """
        )
    )
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_return_items_return_id ON return_items (return_id)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_return_items_order_item_id ON return_items (order_item_id)"))

    # 状态与数量约束（幂等：重复创建忽略）
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                ALTER TABLE return_requests
                    ADD CONSTRAINT ck_return_requests_status
                    CHECK (
                        status IN (
                            'requested', 'approved', 'received', 'refunded', 'rejected', 'cancelled', 'closed'
                        )
                    );
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END $$;
            """
        )
    )
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                ALTER TABLE return_items
                    ADD CONSTRAINT ck_return_items_quantity
                    CHECK (quantity > 0);
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END $$;
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP TABLE IF EXISTS return_items"))
    op.execute(sa.text("DROP TABLE IF EXISTS return_requests"))
