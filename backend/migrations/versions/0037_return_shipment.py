"""return shipment tracking (RMA 客户寄回物流)

Revision ID: 0037_return_shipment
Revises: 0036_return_requests
Create Date: 2026-09-14

RMA 五段式第 3 段（寄回）落地：审核通过后由 C 端回填承运商与快递单号，
Admin 售后单详情据此查看客户寄回物流，收货确认后进入退款环节。
- carrier / tracking_number：客户寄回物流标识（供售后单内追踪）
- shipped_at：客户首次回填时间（用于判断是否超期未寄回）
幂等：ADD COLUMN IF NOT EXISTS，可重复执行。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0037_return_shipment"
down_revision: str | Sequence[str] | None = "0036_return_requests"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(sa.text("ALTER TABLE return_requests ADD COLUMN IF NOT EXISTS carrier VARCHAR(100)"))
    op.execute(sa.text("ALTER TABLE return_requests ADD COLUMN IF NOT EXISTS tracking_number VARCHAR(500)"))
    op.execute(sa.text("ALTER TABLE return_requests ADD COLUMN IF NOT EXISTS shipped_at TIMESTAMP"))


def downgrade() -> None:
    op.execute(sa.text("ALTER TABLE return_requests DROP COLUMN IF EXISTS shipped_at"))
    op.execute(sa.text("ALTER TABLE return_requests DROP COLUMN IF EXISTS tracking_number"))
    op.execute(sa.text("ALTER TABLE return_requests DROP COLUMN IF EXISTS carrier"))
