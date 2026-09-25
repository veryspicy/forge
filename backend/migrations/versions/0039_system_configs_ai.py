"""ai config (后台 AI/LLM 配置持久化)

Revision ID: 0039_system_configs_ai
Revises: 0038_admin_archive
Create Date: 2026-09-25

- 新增 ``system_configs`` 表（KV）：存放可在 Admin 后台修改的系统级配置，
  AI/LLM 配置（key = ``ai.llm``）为首个用例。
  ``value``(JSONB) 存非敏感项（base_url / model / temperature / max_tokens / enabled），
  ``secret_value`` 存敏感项的 Fernet 密文（API Key），落库即加密、接口永不回显明文。
- 新增权限码 ``ai_config:view`` / ``ai_config:manage``，仅授予 admin 角色；
  super_admin 走权限通配 '*'，不建关联。
  权限定义与 ``forge.main.rbac.ROLE_PERMISSIONS`` 保持一致，改动时需同步。
幂等：CREATE TABLE IF NOT EXISTS + ON CONFLICT，可重复执行。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0039_system_configs_ai"
down_revision: str | Sequence[str] | None = "0038_admin_archive"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (module, code, display_name) —— 与 rbac.seed_permissions() 输出一致
AI_CONFIG_PERMISSIONS: list[tuple[str, str, str]] = [
    ("ai_config", "ai_config:view", "AI 配置-查看"),
    ("ai_config", "ai_config:manage", "AI 配置-管理"),
]


def upgrade() -> None:
    op.execute(
        sa.text(
            "CREATE TABLE IF NOT EXISTS system_configs ("
            "key VARCHAR(100) PRIMARY KEY, "
            "value JSONB NOT NULL DEFAULT '{}'::jsonb, "
            "secret_value TEXT, "
            "is_secret BOOLEAN NOT NULL DEFAULT false, "
            "updated_by VARCHAR(100), "
            "created_at TIMESTAMP NOT NULL DEFAULT now(), "
            "updated_at TIMESTAMP NOT NULL DEFAULT now())"
        )
    )

    for module, code, display in AI_CONFIG_PERMISSIONS:
        op.execute(
            sa.text(
                "INSERT INTO permissions (id, code, display_name, module, created_at) "
                "VALUES (gen_random_uuid(), :code, :display, :module, now()) "
                "ON CONFLICT (code) DO UPDATE SET display_name = EXCLUDED.display_name, module = EXCLUDED.module"
            ).bindparams(code=code, display=display, module=module)
        )
        # 增量授权：只补 admin 角色的 AI 配置权限，不重建整张 role_permissions
        op.execute(
            sa.text(
                "INSERT INTO role_permissions (role_id, permission_id) "
                "SELECT r.id, p.id FROM roles r, permissions p "
                "WHERE r.name = 'admin' AND p.code = :code "
                "ON CONFLICT DO NOTHING"
            ).bindparams(code=code)
        )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE permission_id IN "
            "(SELECT id FROM permissions WHERE code IN ('ai_config:view', 'ai_config:manage'))"
        )
    )
    op.execute(sa.text("DELETE FROM permissions WHERE code IN ('ai_config:view', 'ai_config:manage')"))
    op.execute(sa.text("DROP TABLE IF EXISTS system_configs"))
