"""add_mcp_server

Revision ID: 0021_mcp_server
Revises: 0020_supplier_mcp
Create Date: 2026-08-21

P3 对外 MCP Server（大模型 Agent 对接）：
- 新增 mcp_api_keys 表（Agent API Key，SHA-256 哈希存储，可吊销）
- 新增 mcp_audit_logs 表（每次 MCP Tool 调用审计）
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0021_mcp_server"
down_revision: str | None = "0020_supplier_mcp"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. mcp_api_keys 表
    op.create_table(
        "mcp_api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("key_prefix", sa.String(16), nullable=False),
        sa.Column("key_hash", sa.String(128), nullable=False, unique=True),
        sa.Column("scopes", postgresql.JSONB(), nullable=False, server_default=sa.text("'[\"read\"]'::jsonb")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.text("now()")),
        sa.Column("last_used_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=False), nullable=True),
    )
    op.create_index("ix_mcp_api_keys_name", "mcp_api_keys", ["name"])

    # 2. mcp_audit_logs 表
    op.create_table(
        "mcp_audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "api_key_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("mcp_api_keys.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("agent_name", sa.String(128), nullable=True),
        sa.Column("tool_name", sa.String(64), nullable=False),
        sa.Column("arguments", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("result_status", sa.String(16), nullable=False, server_default="ok"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_mcp_audit_logs_created_at", "mcp_audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("mcp_audit_logs")
    op.drop_table("mcp_api_keys")
