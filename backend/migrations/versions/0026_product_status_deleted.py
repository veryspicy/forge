"""product_status_deleted

Revision ID: 0026_product_status_deleted
Revises: 0025_admin_rbac_matrix_extend
Create Date: 2026-08-23

商品软删除：status 枚举增加 deleted 值，同步放宽 ck_products_status 约束。
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0026_product_status_deleted"
down_revision: str | None = "0025_admin_rbac_matrix_extend"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_products_status", "products", type_="check")
    op.create_check_constraint(
        "ck_products_status",
        "products",
        "status IN ('draft','active','inactive','deleted')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_products_status", "products", type_="check")
    op.create_check_constraint(
        "ck_products_status",
        "products",
        "status IN ('draft','active','inactive')",
    )
