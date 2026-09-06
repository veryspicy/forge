"""orders_payment_reviews

Revision ID: 0032_orders_payment_reviews
Revises: 0031_users_add_phone
Create Date: 2026-09-05

订单行业功能补齐（后端基线）：
1. orders 表新增支付/状态时间线/软删字段：
   payment_method / payment_status(unpaid) / payment_intent_id 已有 /
   paid_at / confirmed_at / shipped_at / delivered_at / deleted_at
2. 新建 product_reviews 评价表（order_item_id 唯一，rating 1-5）
幂等：ADD COLUMN IF NOT EXISTS / CREATE TABLE IF NOT EXISTS / CREATE INDEX IF NOT EXISTS 可重复执行。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0032_orders_payment_reviews"
down_revision: str | Sequence[str] | None = "0031_users_add_phone"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(sa.text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS payment_method VARCHAR(50)"))
    op.execute(
        sa.text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS payment_status VARCHAR(20) NOT NULL DEFAULT 'unpaid'")
    )
    op.execute(sa.text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS paid_at TIMESTAMP WITHOUT TIME ZONE"))
    op.execute(sa.text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS confirmed_at TIMESTAMP WITHOUT TIME ZONE"))
    op.execute(sa.text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS shipped_at TIMESTAMP WITHOUT TIME ZONE"))
    op.execute(sa.text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS delivered_at TIMESTAMP WITHOUT TIME ZONE"))
    op.execute(sa.text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITHOUT TIME ZONE"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_orders_deleted_at ON orders (deleted_at)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_orders_payment_status ON orders (payment_status)"))

    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS product_reviews (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                order_id UUID NOT NULL REFERENCES orders(id),
                order_item_id UUID NOT NULL UNIQUE REFERENCES order_items(id),
                user_id UUID NOT NULL,
                product_id BIGINT NOT NULL REFERENCES products(id),
                rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
                title VARCHAR(200),
                content TEXT,
                images JSONB,
                admin_reply TEXT,
                created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
                updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now()
            )
            """
        )
    )
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_product_reviews_product_id ON product_reviews (product_id)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_product_reviews_user_id ON product_reviews (user_id)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_product_reviews_order_id ON product_reviews (order_id)"))


def downgrade() -> None:
    op.execute(sa.text("DROP TABLE IF EXISTS product_reviews"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_orders_deleted_at"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_orders_payment_status"))
    op.execute(sa.text("ALTER TABLE orders DROP COLUMN IF EXISTS deleted_at"))
    op.execute(sa.text("ALTER TABLE orders DROP COLUMN IF EXISTS delivered_at"))
    op.execute(sa.text("ALTER TABLE orders DROP COLUMN IF EXISTS shipped_at"))
    op.execute(sa.text("ALTER TABLE orders DROP COLUMN IF EXISTS confirmed_at"))
    op.execute(sa.text("ALTER TABLE orders DROP COLUMN IF EXISTS paid_at"))
    op.execute(sa.text("ALTER TABLE orders DROP COLUMN IF EXISTS payment_status"))
    op.execute(sa.text("ALTER TABLE orders DROP COLUMN IF EXISTS payment_method"))
