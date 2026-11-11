"""order tax snapshot (订单税费快照字段)

Revision ID: 0053_order_tax_snapshot
Revises: 0052_payment_config
Create Date: 2026-11-08

税率表（A 方案）落地后，订单需要固化「下单当时」的计税依据，避免后续调税率
导致历史订单金额/退款金额不可追溯：

- ``tax_rate``         实际适用税率（小数，如 0.19）
- ``tax_name``         税种名（VAT / GST / Sales Tax）
- ``tax_jurisdiction`` 辖区（如 DE、US-CA）
- ``tax_inclusive``    价内含税标记（EU/UK 常见）

已有订单保持 ``NULL`` / ``false``（此前 tax 恒为 0，行为不变）。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0053_order_tax_snapshot"
down_revision: str | Sequence[str] | None = "0052_payment_config"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("tax_rate", sa.Numeric(6, 4), nullable=True))
    op.add_column("orders", sa.Column("tax_name", sa.String(length=100), nullable=True))
    op.add_column("orders", sa.Column("tax_jurisdiction", sa.String(length=20), nullable=True))
    op.add_column(
        "orders",
        sa.Column("tax_inclusive", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("orders", "tax_inclusive")
    op.drop_column("orders", "tax_jurisdiction")
    op.drop_column("orders", "tax_name")
    op.drop_column("orders", "tax_rate")
