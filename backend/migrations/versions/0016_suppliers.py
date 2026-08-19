"""add_suppliers

Revision ID: 0016_suppliers
Revises: 0015_products_defaults
Create Date: 2026-08-19

P1 供应商模块：
- 初始 schema（84e64df81995）遗留的 suppliers 空表结构陈旧（shipping_regions jsonb、
  integration_type varchar(20)、无 name 唯一约束、列无 server_default、id 无默认值），
  且无任何数据（count=0）、无外键引用，直接重建为 P1 目标结构
- products.supplier_id 补外键（P0 预留字段，现落地约束 ON DELETE SET NULL）
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0016_suppliers"
down_revision: str | None = "0015_products_defaults"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 遗留空表直接重建（无数据、无引用，安全）
    op.drop_table("suppliers")
    op.create_table(
        "suppliers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("contact_email", sa.String(320), nullable=True),
        sa.Column("contact_phone", sa.String(50), nullable=True),
        sa.Column("integration_type", sa.String(32), nullable=False, server_default="manual"),
        sa.Column("shipping_regions", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("default_currency", sa.String(10), nullable=False, server_default="USD"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("name", name="uq_suppliers_name"),
        sa.CheckConstraint(
            "integration_type IN ('manual','api','dropship')",
            name="ck_suppliers_integration_type",
        ),
    )

    # P0 预留的 supplier_id 字段补外键
    op.create_foreign_key(
        "fk_products_supplier_id",
        "products",
        "suppliers",
        ["supplier_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_products_supplier_id", "products", type_="foreignkey")
    op.drop_table("suppliers")
