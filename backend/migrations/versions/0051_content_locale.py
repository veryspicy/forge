"""cms content add locale for i18n (language-separated entries)

Revision ID: 0051_content_locale
Revises: 0050_content
Create Date: 2026-11-04

- ``content`` 表新增 ``locale`` 列（en/zh），默认 ``en``
- slug 唯一索引替换为 ``(slug, locale)`` 复合唯一：同一 slug 可存在各语言独立内容
- 已有行自动归入 ``en``，行为与改造前一致（C 端 fallback 默认 en）
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0051_content_locale"
down_revision: str | Sequence[str] | None = "0050_content"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("ix_content_slug", table_name="content")
    op.add_column(
        "content",
        sa.Column("locale", sa.String(length=16), nullable=False, server_default="en"),
    )
    op.create_unique_constraint("uq_content_slug_locale", "content", ["slug", "locale"])
    op.create_index("ix_content_locale", "content", ["locale"])


def downgrade() -> None:
    op.drop_index("ix_content_locale", table_name="content")
    op.drop_constraint("uq_content_slug_locale", "content", type_="unique")
    op.drop_column("content", "locale")
    op.create_index("ix_content_slug", "content", ["slug"], unique=True)
