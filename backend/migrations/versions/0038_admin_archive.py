"""admin archive (后台归档/软删除) for orders / shipments / returns

Revision ID: 0038_admin_archive
Revises: 0037_return_shipment
Create Date: 2026-09-15

后台「删除」统一为归档语义（软删除），不物理删除、可逆：
- orders / shipments / return_requests 各加 admin_archived_at（NULL = 未归档）；
  该字段与 C 端 orders.deleted_at 口径相互独立，仅影响 Admin 列表 / 看板 / 导出。
- 新增权限码 orders:archive / shipments:archive（售后归档复用 orders:archive），
  仅授予 admin 角色；super_admin 走权限通配 '*' 不建关联。
  权限定义与 forge.main.rbac.ROLE_PERMISSIONS 保持一致，改动时需同步。
幂等：ADD COLUMN IF NOT EXISTS + ON CONFLICT，可重复执行。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0038_admin_archive"
down_revision: str | Sequence[str] | None = "0037_return_shipment"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (module, code, display_name) —— 与 rbac.seed_permissions() 输出一致
ARCHIVE_PERMISSIONS: list[tuple[str, str, str]] = [
    ("orders", "orders:archive", "订单管理-归档"),
    ("shipments", "shipments:archive", "发货管理-归档"),
]


def upgrade() -> None:
    op.execute(sa.text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS admin_archived_at TIMESTAMP"))
    op.execute(sa.text("ALTER TABLE shipments ADD COLUMN IF NOT EXISTS admin_archived_at TIMESTAMP"))
    op.execute(sa.text("ALTER TABLE return_requests ADD COLUMN IF NOT EXISTS admin_archived_at TIMESTAMP"))

    for module, code, display in ARCHIVE_PERMISSIONS:
        op.execute(
            sa.text(
                "INSERT INTO permissions (id, code, display_name, module, created_at) "
                "VALUES (gen_random_uuid(), :code, :display, :module, now()) "
                "ON CONFLICT (code) DO UPDATE SET display_name = EXCLUDED.display_name, module = EXCLUDED.module"
            ).bindparams(code=code, display=display, module=module)
        )
        # 增量授权：只补 admin 角色的归档权限，不重建整张 role_permissions（不覆盖既有手工调整）
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
            "(SELECT id FROM permissions WHERE code IN ('orders:archive', 'shipments:archive'))"
        )
    )
    op.execute(sa.text("DELETE FROM permissions WHERE code IN ('orders:archive', 'shipments:archive')"))
    op.execute(sa.text("ALTER TABLE return_requests DROP COLUMN IF EXISTS admin_archived_at"))
    op.execute(sa.text("ALTER TABLE shipments DROP COLUMN IF EXISTS admin_archived_at"))
    op.execute(sa.text("ALTER TABLE orders DROP COLUMN IF EXISTS admin_archived_at"))
