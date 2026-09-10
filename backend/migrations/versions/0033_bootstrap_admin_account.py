"""0033_bootstrap_admin_account

Revision ID: 0033_bootstrap_admin_account
Revises: 0032_orders_payment_reviews
Create Date: 2026-09-08

幂等创建默认 super_admin 账号（生产初始化开箱可用）。

依赖前置：0023_admin_rbac_db 已创建 roles 表并种子 super_admin 角色。
本迁移在链尾执行，仅在 admin@forge.dev 不存在时插入账号并关联 super_admin；
已存在（老库/手工补过）则跳过，保留现有密码不动。

安全红线：默认口令 admin123 仅用于初始化首登，生产部署后必须立即修改
（见 docs/DEPLOYMENT-MOP.md 生产初始化 SOP 第 4 步）。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0033_bootstrap_admin_account"
down_revision: str | Sequence[str] | None = "0032_orders_payment_reviews"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# 默认管理员账号（首登后应立即改密）
ADMIN_EMAIL = "admin@forge.dev"
ADMIN_PASSWORD_HASH = "$2b$12$R5xOR0YolL..Nv.gBz/P7esmWgM82YdJM2OM9RDMi9e2MLupPuh6e"  # bcrypt("admin123")
ADMIN_DISPLAY_NAME = "Super Admin"


def upgrade() -> None:
    bind = op.get_bind()

    # 前置检查：roles 表与 super_admin 角色须已存在（由 0023 提供）；缺失则跳过，
    # 保持幂等，避免因上游迁移被改动导致本迁移越权建角色。
    role_row = bind.execute(sa.text("SELECT id FROM roles WHERE name = 'super_admin' LIMIT 1")).fetchone()
    if role_row is None:
        return

    # 插入默认账号（email 唯一，冲突即跳过，保留已有密码）
    bind.execute(
        sa.text(
            "INSERT INTO admin_users "
            "(id, email, password_hash, display_name, role, is_active, created_at, updated_at) "
            "VALUES (gen_random_uuid(), :email, :pwd_hash, :display, 'super_admin', true, now(), now()) "
            "ON CONFLICT (email) DO NOTHING"
        ).bindparams(
            email=ADMIN_EMAIL,
            pwd_hash=ADMIN_PASSWORD_HASH,
            display=ADMIN_DISPLAY_NAME,
        )
    )

    # 关联 super_admin 角色（幂等）
    bind.execute(
        sa.text(
            "INSERT INTO admin_user_roles (admin_user_id, role_id) "
            "SELECT u.id, r.id FROM admin_users u "
            "JOIN roles r ON r.name = 'super_admin' "
            "WHERE u.email = :email "
            "ON CONFLICT DO NOTHING"
        ).bindparams(email=ADMIN_EMAIL)
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "DELETE FROM admin_user_roles WHERE admin_user_id IN (SELECT id FROM admin_users WHERE email = :email)"
        ).bindparams(email=ADMIN_EMAIL)
    )
    bind.execute(sa.text("DELETE FROM admin_users WHERE email = :email").bindparams(email=ADMIN_EMAIL))
