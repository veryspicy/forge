"""prod_admin_users_bootstrap

Revision ID: prod_admin_users_bootstrap
Revises: 84e64df81995
Create Date: 2026-09-08

幂等创建 admin_users 表（生产/空库初始化基线修复）。

背景：admin_users 是 RBAC 核心表，但历史上由外部手工建表、从未进入迁移链。
自 0008_add_diy_tables 起迁移即引用 admin_users.id 外键，0022/0024 亦在其上
执行 ALTER，导致全新空库直接 upgrade head 时断链。本迁移将建表插入链早期
（initial_schema 之后），保证空库可完整跑通迁移链；老库已存在该表时自动跳过。

建表列以 ORMAdminUser 为准，但刻意不含 role 列——role 列由 0022_admin_rbac_role
按历史顺序添加（老库该列已存在，bootstrap 不会在老库执行建表分支，无冲突）。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "prod_admin_users_bootstrap"
down_revision: str | Sequence[str] | None = "84e64df81995"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("admin_users"):
        # 老库已存在（历史手工建表或先前迁移已建），跳过建表，保持幂等。
        return

    op.create_table(
        "admin_users",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=128), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_admin_users_email", "admin_users", ["email"], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("admin_users"):
        op.drop_index("ix_admin_users_email", table_name="admin_users")
        op.drop_table("admin_users")
