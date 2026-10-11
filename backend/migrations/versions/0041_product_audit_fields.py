"""product audit fields (商品审核留痕)

Revision ID: 0041_product_audit_fields
Revises: 0040_product_detail_blocks
Create Date: 2026-10-10

- ``products`` 表新增审核留痕字段（PRODUCT-AUDIT-FLOW）：
  - ``audit_reason``(VARCHAR(500))：审核备注 / 拒绝原因
  - ``audit_by``(VARCHAR(128))：审核人（当前登录管理员 email）
  - ``audited_at``(TIMESTAMPTZ)：审核时间
  与既有 ``audit_status``（pending / approved / rejected）配合，实现商品审核闭环。
幂等：ADD COLUMN IF NOT EXISTS，可重复执行。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0041_product_audit_fields"
down_revision: str | Sequence[str] | None = "0040_product_detail_blocks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "ALTER TABLE products ADD COLUMN IF NOT EXISTS audit_reason VARCHAR(500)"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE products ADD COLUMN IF NOT EXISTS audit_by VARCHAR(128)"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE products ADD COLUMN IF NOT EXISTS audited_at TIMESTAMP WITH TIME ZONE"
        )
    )


def downgrade() -> None:
    op.execute(sa.text("ALTER TABLE products DROP COLUMN IF EXISTS audit_reason"))
    op.execute(sa.text("ALTER TABLE products DROP COLUMN IF EXISTS audit_by"))
    op.execute(sa.text("ALTER TABLE products DROP COLUMN IF EXISTS audited_at"))
