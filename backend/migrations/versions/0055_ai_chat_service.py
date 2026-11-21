"""AI 客服服务（多供应商路由 / 额度治理 / 转人工）

Revision ID: 0055_ai_chat_service
Revises: 0054_tax_config_perms
Create Date: 2026-11-19

新增四张表：

- ``ai_conversations``：C 端 AI 客服会话（登录用户按 users.id，游客按 guest_key）
- ``ai_messages``：消息明细，记录命中供应商 / token / 延迟 / 状态
- ``ai_usage_daily``：供应商每日额度用量（额度治理与负载均衡的事实来源）
- ``ai_handoff_requests``：AI 全部不可用时的转人工工单

幂等：CREATE TABLE IF NOT EXISTS / CREATE INDEX IF NOT EXISTS，可重复执行。
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0055_ai_chat_service"
down_revision: str | Sequence[str] | None = "0054_tax_config_perms"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ai_conversations (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NULL,
            guest_key varchar(128) NULL,
            title varchar(200) NOT NULL DEFAULT '',
            pet_id uuid NULL,
            last_message text NOT NULL DEFAULT '',
            message_count integer NOT NULL DEFAULT 0,
            provider_id varchar(64) NULL,
            created_at timestamp without time zone NOT NULL DEFAULT now(),
            updated_at timestamp without time zone NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_conversations_user_id ON ai_conversations (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_conversations_guest_key ON ai_conversations (guest_key)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_conversations_updated_at ON ai_conversations (updated_at DESC)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ai_messages (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            conversation_id uuid NOT NULL
                REFERENCES ai_conversations (id) ON DELETE CASCADE,
            role varchar(16) NOT NULL,
            content text NOT NULL DEFAULT '',
            provider_id varchar(64) NULL,
            provider_name varchar(100) NULL,
            model varchar(120) NULL,
            tokens_in integer NOT NULL DEFAULT 0,
            tokens_out integer NOT NULL DEFAULT 0,
            latency_ms integer NOT NULL DEFAULT 0,
            status varchar(16) NOT NULL DEFAULT 'ok',
            recommendations jsonb NOT NULL DEFAULT '[]'::jsonb,
            created_at timestamp without time zone NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_messages_conversation_id ON ai_messages (conversation_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_messages_created_at ON ai_messages (created_at DESC)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ai_usage_daily (
            id bigserial PRIMARY KEY,
            provider_id varchar(64) NOT NULL,
            usage_date varchar(10) NOT NULL,
            requests integer NOT NULL DEFAULT 0,
            tokens integer NOT NULL DEFAULT 0,
            failures integer NOT NULL DEFAULT 0,
            quota_hits integer NOT NULL DEFAULT 0,
            last_error text NULL,
            updated_at timestamp without time zone NOT NULL DEFAULT now(),
            CONSTRAINT uq_ai_usage_daily_provider_date UNIQUE (provider_id, usage_date)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_usage_daily_provider_id ON ai_usage_daily (provider_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_usage_daily_date ON ai_usage_daily (usage_date)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ai_handoff_requests (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            conversation_id uuid NULL,
            user_id uuid NULL,
            guest_key varchar(128) NULL,
            message text NOT NULL DEFAULT '',
            reason varchar(32) NOT NULL DEFAULT 'quota_exhausted',
            detail text NULL,
            status varchar(16) NOT NULL DEFAULT 'pending',
            handled_by varchar(128) NULL,
            handled_at timestamp without time zone NULL,
            note text NULL,
            created_at timestamp without time zone NOT NULL DEFAULT now(),
            updated_at timestamp without time zone NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ai_handoff_requests_status ON ai_handoff_requests (status, created_at DESC)"
    )
    # 兼容"表已存在"的历史环境：CREATE TABLE IF NOT EXISTS 不会补列
    op.execute("ALTER TABLE ai_handoff_requests ADD COLUMN IF NOT EXISTS handled_at timestamp without time zone NULL")
    op.execute("ALTER TABLE ai_handoff_requests ADD COLUMN IF NOT EXISTS note text NULL")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ai_handoff_requests")
    op.execute("DROP TABLE IF EXISTS ai_usage_daily")
    op.execute("DROP TABLE IF EXISTS ai_messages")
    op.execute("DROP TABLE IF EXISTS ai_conversations")
