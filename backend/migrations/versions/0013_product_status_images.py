"""add_product_status_images_supplier

Revision ID: 0013_product_status_images
Revises: 0012_resource_dir_tag
Create Date: 2026-08-18

P0 数据模型变更（对齐数据库实际 schema）：
- products.images：ARRAY(String) → JSONB（存量全为空数组，无损；JSONB 支持 is_main/sort/alt 结构）
- products 新增 status（draft/active/inactive 状态机，存量回填 active）
- products 新增 supplier_id / supplier_sku（本阶段不加外键，供应商表落地后补）
- rating / review_count / is_ai_generated 补 server_default（ORM 创建商品缺默认值会失败）
- price 加 CHECK(>0)；inventory 加 CHECK(>=0)（sku 唯一索引已存在于初始 migration，不重复创建）
- 新增 status / category / supplier_id 查询索引
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0013_product_status_images"
down_revision: str | None = "0012_resource_dir_tag"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # images：ARRAY(String) → JSONB（存量全为空，无损）
    op.drop_column("products", "images")
    op.add_column(
        "products",
        sa.Column(
            "images",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )

    # status 状态机（存量商品视为在售）
    op.add_column(
        "products",
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
    )
    op.create_check_constraint(
        "ck_products_status",
        "products",
        "status IN ('draft','active','inactive')",
    )

    # supplier 关联字段（本阶段无外键）
    op.add_column(
        "products",
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "products",
        sa.Column("supplier_sku", sa.String(100), nullable=True),
    )

    # 存量 NOT NULL 列补默认值（ORM 创建商品时依赖）
    op.alter_column("products", "rating", server_default=sa.text("0"), nullable=False)
    op.alter_column("products", "review_count", server_default=sa.text("0"), nullable=False)
    op.alter_column("products", "is_ai_generated", server_default=sa.text("false"), nullable=False)

    # 约束：售价为正 / 库存非负（sku 唯一索引已存在）
    op.create_check_constraint("ck_products_price_positive", "products", "price > 0")
    op.create_check_constraint("ck_products_inventory_nonneg", "products", "inventory >= 0")

    # 列表筛选常用索引
    op.create_index("ix_products_status", "products", ["status"])
    op.create_index("ix_products_category", "products", ["category"])
    op.create_index("ix_products_supplier_id", "products", ["supplier_id"])


def downgrade() -> None:
    op.drop_index("ix_products_supplier_id", table_name="products")
    op.drop_index("ix_products_category", table_name="products")
    op.drop_index("ix_products_status", table_name="products")
    op.drop_constraint("ck_products_inventory_nonneg", "products", type_="check")
    op.drop_constraint("ck_products_price_positive", "products", type_="check")
    op.drop_column("products", "supplier_sku")
    op.drop_column("products", "supplier_id")
    op.drop_constraint("ck_products_status", "products", type_="check")
    op.drop_column("products", "status")
    op.alter_column("products", "is_ai_generated", server_default=None, nullable=False)
    op.alter_column("products", "review_count", server_default=None, nullable=False)
    op.alter_column("products", "rating", server_default=None, nullable=False)
    op.drop_column("products", "images")
    op.add_column(
        "products",
        sa.Column("images", postgresql.ARRAY(sa.String()), nullable=True),
    )
