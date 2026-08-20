"""add_supplier_mcp

Revision ID: 0020_supplier_mcp
Revises: 0019_product_variants
Create Date: 2026-08-21

P2-5 多供应商 MCP 集成（首个厂商 Zendrop）：
- suppliers 扩展 provider_code / config（多供应商类型标识与厂商配置）
- products 扩展 supplier_product_id（厂商侧商品 ID，用于增量同步价格/库存）
- 新增 supplier_credentials 表（Access Token / OAuth2.0 PKCE 凭据 + 状态）
- 新增 supplier_sync_logs 表（手动/定时同步记录）
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0020_supplier_mcp"
down_revision: str | None = "0019_product_variants"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. suppliers 扩展：provider_code + config
    op.add_column("suppliers", sa.Column("provider_code", sa.String(64), nullable=True))
    op.add_column(
        "suppliers",
        sa.Column("config", postgresql.JSONB(), nullable=True, server_default=sa.text("'{}'::jsonb")),
    )
    op.create_index("ix_suppliers_provider_code", "suppliers", ["provider_code"])

    # 2. products 扩展：supplier_product_id
    op.add_column("products", sa.Column("supplier_product_id", sa.String(128), nullable=True))
    op.create_index("ix_products_supplier_product_id", "products", ["supplier_product_id"])

    # 3. supplier_credentials 表
    op.create_table(
        "supplier_credentials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "supplier_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("suppliers.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("provider_code", sa.String(64), nullable=False),
        sa.Column("auth_type", sa.String(16), nullable=False, server_default="token"),
        sa.Column("access_token", sa.Text(), nullable=True),
        sa.Column("refresh_token", sa.Text(), nullable=True),
        sa.Column("token_type", sa.String(32), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("oauth_state", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("supplier_id", name="uq_supplier_credentials_supplier"),
    )

    # 4. supplier_sync_logs 表
    op.create_table(
        "supplier_sync_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "supplier_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("suppliers.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("provider_code", sa.String(64), nullable=False),
        sa.Column("trigger_type", sa.String(16), nullable=False, server_default="manual"),
        sa.Column("status", sa.String(16), nullable=False, server_default="running"),
        sa.Column("items_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_imported", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.text("now()")),
        sa.Column("finished_at", sa.DateTime(timezone=False), nullable=True),
        sa.CheckConstraint(
            "trigger_type IN ('manual','scheduled')",
            name="ck_supplier_sync_logs_trigger",
        ),
        sa.CheckConstraint(
            "status IN ('running','success','partial','failed')",
            name="ck_supplier_sync_logs_status",
        ),
    )


def downgrade() -> None:
    op.drop_table("supplier_sync_logs")
    op.drop_table("supplier_credentials")
    op.drop_index("ix_products_supplier_product_id", table_name="products")
    op.drop_column("products", "supplier_product_id")
    op.drop_index("ix_suppliers_provider_code", table_name="suppliers")
    op.drop_column("suppliers", "config")
    op.drop_column("suppliers", "provider_code")
