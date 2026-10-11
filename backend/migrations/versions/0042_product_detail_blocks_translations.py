"""product detail_blocks translations + ai_description_translations cleanup

Revision ID: 0042_product_detail_blocks_translations
Revises: 0041_product_audit_fields
Create Date: 2026-10-10

- ``products`` 表新增 ``detail_blocks_translations``(JSONB)：详情块多语言覆盖（Shopify 字段级模型），
  结构 ``{locale: [detail_block]}``；``detail_blocks`` 保持基准语言块，C 端按 locale 取整组块、缺失回退基准。
- ``products`` 表删除 ``ai_description_translations``(JSONB)：AI 描述翻译为无价值残留（admin 前端入口已在
  feature/admin-pdp-simplify 移除），后端契约与序列化同步清理，本迁移完成 DB 列 drop（破坏性，用户已确认）。
幂等：ADD/DROP COLUMN IF [NOT] EXISTS，可重复执行。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0042_product_detail_blocks_translations"
down_revision: str | Sequence[str] | None = "0041_product_audit_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "ALTER TABLE products ADD COLUMN IF NOT EXISTS detail_blocks_translations JSONB DEFAULT '{}'::jsonb NOT NULL"
        )
    )
    op.execute(sa.text("ALTER TABLE products DROP COLUMN IF EXISTS ai_description_translations"))


def downgrade() -> None:
    op.execute(
        sa.text(
            "ALTER TABLE products ADD COLUMN IF NOT EXISTS ai_description_translations JSONB DEFAULT '{}'::jsonb NOT NULL"
        )
    )
    op.execute(sa.text("ALTER TABLE products DROP COLUMN IF EXISTS detail_blocks_translations"))
