"""product detail blocks (商品结构化详情块)

Revision ID: 0040_product_detail_blocks
Revises: 0039_system_configs_ai
Create Date: 2026-09-25

- ``products`` 表新增 ``detail_blocks``(JSONB)，存放商品详情页的结构化内容块。
  约定为有序数组，元素形如 ``{"type": "...", ...}``，type 取值：
  ``rich_text`` / ``image`` / ``image_text`` / ``spec_table`` / ``features`` / ``faq`` / ``video``。
  与 ``description``（纯文本简介）互补：列表/简介用 description，详情正文用 detail_blocks，
  避免 mall-admin-web 式整段 HTML 富文本（XSS、多语言、结构化数据不可复用）。
- C 端 ``_PUBLIC_FIELDS`` 需同步暴露该字段（仅已上架商品）。
幂等：ADD COLUMN IF NOT EXISTS，可重复执行。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0040_product_detail_blocks"
down_revision: str | Sequence[str] | None = "0039_system_configs_ai"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text("ALTER TABLE products ADD COLUMN IF NOT EXISTS detail_blocks JSONB NOT NULL DEFAULT '[]'::jsonb")
    )


def downgrade() -> None:
    op.execute(sa.text("ALTER TABLE products DROP COLUMN IF EXISTS detail_blocks"))
