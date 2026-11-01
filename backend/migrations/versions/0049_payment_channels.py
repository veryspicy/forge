"""payment multi-channel: transaction id + channel meta on orders

Revision ID: 0049_payment_channels
Revises: 0048_resource_download_log
Create Date: 2026-11-01

- orders 新增 ``payment_transaction_id``（渠道侧捕获流水号，PayPal capture id / Stripe charge id ...）
- orders 新增 ``payment_channel_meta``（JSONB，渠道扩展元数据，如 PayPal order status / capture amount）
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0049_payment_channels"
down_revision: str | Sequence[str] | None = "0048_resource_download_log"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("payment_transaction_id", sa.String(length=500), nullable=True))
    op.add_column("orders", sa.Column("payment_channel_meta", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "payment_channel_meta")
    op.drop_column("orders", "payment_transaction_id")
