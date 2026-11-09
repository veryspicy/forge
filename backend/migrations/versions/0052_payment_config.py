"""payment config (支付渠道启停 + 凭证后台可配置)

Revision ID: 0052_payment_config
Revises: 0051_content_locale
Create Date: 2026-11-08

- 新增权限码 ``payment_config:view`` / ``payment_config:manage``，仅授予 admin 角色；
  super_admin 走通配 '*'，不建关联。定义与 ``forge.main.rbac.ROLE_PERMISSIONS`` 同步。
- 支付渠道配置本身复用既有存储，无需建表：
  - 启停：``app_settings`` key = ``payment`` → ``{"enabled_channels": [...]}``
  - 凭证：``system_configs`` key = ``payment.channels``（敏感字段 Fernet 密文）
- 不预置默认启用集合：保持「DB 优先 > env FORGE_PAYMENT_ENABLED_CHANNELS > mock」兜底，
  部署行为与改造前一致，后台首次保存后即由配置接管。

幂等：ON CONFLICT DO NOTHING / UPDATE，可重复执行。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0052_payment_config"
down_revision: str | Sequence[str] | None = "0051_content_locale"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PAYMENT_CONFIG_PERMISSIONS: list[tuple[str, str, str]] = [
    ("payment_config", "payment_config:view", "支付配置-查看"),
    ("payment_config", "payment_config:manage", "支付配置-管理"),
]


def upgrade() -> None:
    for module, code, display in PAYMENT_CONFIG_PERMISSIONS:
        op.execute(
            sa.text(
                "INSERT INTO permissions (id, code, display_name, module, created_at) "
                "VALUES (gen_random_uuid(), :code, :display, :module, now()) "
                "ON CONFLICT (code) DO UPDATE SET display_name = EXCLUDED.display_name, module = EXCLUDED.module"
            ).bindparams(code=code, display=display, module=module)
        )
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
            "(SELECT id FROM permissions WHERE code IN ('payment_config:view', 'payment_config:manage'))"
        )
    )
    op.execute(
        sa.text("DELETE FROM permissions WHERE code IN ('payment_config:view', 'payment_config:manage')")
    )
