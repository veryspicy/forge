"""add resource download log table

Revision ID: 0048_resource_download_log
Revises: 0047_resource_phash
Create Date: 2026-10-27

- 新增 resource_download_log 表：记录原图下载人 / IP / UA / 隐写 payload，
  供 P4 取证对账（下载日志 ↔ 隐写提取结果）。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0048_resource_download_log"
down_revision: str | Sequence[str] | None = "0047_resource_phash"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "resource_download_log",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("resource_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("user_email", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("ip", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("user_agent", sa.String(length=512), nullable=False, server_default=""),
        sa.Column("payload", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_resource_download_log_resource_id", "resource_download_log", ["resource_id"])
    op.create_index("ix_resource_download_log_user_id", "resource_download_log", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_resource_download_log_user_id", table_name="resource_download_log")
    op.drop_index("ix_resource_download_log_resource_id", table_name="resource_download_log")
    op.drop_table("resource_download_log")
