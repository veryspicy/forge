"""cms content table (lightweight CMS pages)

Revision ID: 0050_content
Revises: 0049_payment_channels
Create Date: 2026-11-01

- 新增 ``content`` 表：slug 驱动的轻量 CMS 内容页（faqs/shipping/returns/contact/...）
- 独立于 site_profile，按 slug 提供给 C 端渲染与 Admin 内容管理
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0050_content"
down_revision: str | Sequence[str] | None = "0049_payment_channels"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "content",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("slug", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column("seo_title", sa.String(length=255), nullable=True),
        sa.Column("seo_description", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="draft"),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_content_slug", "content", ["slug"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_content_slug", table_name="content")
    op.drop_table("content")
