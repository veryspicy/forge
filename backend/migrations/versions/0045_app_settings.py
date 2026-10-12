"""app settings kv table + product audit switch seed

Revision ID: 0045_app_settings
Revises: 0044_product_variant_attributes_translations
Create Date: 2026-10-12

- 新增 ``app_settings`` KV 表：持久化业务开关/配置（如商品审核开关）
- 种子写入 ``product_audit_enabled=false``：审核默认关闭，对齐单商家自营主流平台
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0045_app_settings"
down_revision: str | Sequence[str] | None = "0044_product_variant_attributes_translations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(length=100), primary_key=True),
        sa.Column("value", postgresql.JSONB(), nullable=False),
        sa.Column("updated_by", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )
    op.execute(
        sa.text(
            "INSERT INTO app_settings (key, value) VALUES ('product_audit_enabled', 'false'::jsonb) "
            "ON CONFLICT (key) DO NOTHING"
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM app_settings WHERE key = 'product_audit_enabled'"))
    op.drop_table("app_settings")
