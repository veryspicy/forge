"""products_catalog_refactor

Revision ID: 0028_products_catalog_refactor
Revises: 0027_products_bigint_id
Create Date: 2026-08-28

商品体系改造：分类树 / 轻量品牌 / 商品类型规格模板 / 规格关系表。
- 新增 7 张表：product_categories / brands / product_types / product_type_specs /
  product_spec_keys / product_spec_values / variant_specs
- products 新增 category_id / brand_id / product_type_id（过渡期与字符串双写，NULL 起步）
- product_variants 新增 low_stock_threshold（库存预警值，D5 默认落地）
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0028_products_catalog_refactor"
down_revision: str | None = "0027_products_bigint_id"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. 商品分类树（一级/二级，预留三级）
    op.create_table(
        "product_categories",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("parent_id", sa.BigInteger(), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=150), nullable=False),
        sa.Column("icon", sa.String(length=500), nullable=True),
        sa.Column("sort", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["parent_id"], ["product_categories.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_product_categories_parent_id", "product_categories", ["parent_id"])
    op.create_index("ix_product_categories_slug", "product_categories", ["slug"], unique=True)

    # 2. 轻量品牌
    op.create_table(
        "brands",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("logo", sa.String(length=500), nullable=True),
        sa.Column("show_status", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("sort", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_brands_name", "brands", ["name"], unique=True)

    # 3. 商品类型（规格模板）
    op.create_table(
        "product_types",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("sort", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_product_types_name", "product_types", ["name"], unique=True)

    # 4. 类型 → 规格键模板
    op.create_table(
        "product_type_specs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("product_type_id", sa.BigInteger(), nullable=False),
        sa.Column("spec_key", sa.String(length=50), nullable=False),
        sa.Column("sort", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["product_type_id"], ["product_types.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("product_type_id", "spec_key", name="uq_product_type_specs_type_key"),
    )
    op.create_index("ix_product_type_specs_type_id", "product_type_specs", ["product_type_id"])

    # 5. SPU 实际使用的规格键
    op.create_table(
        "product_spec_keys",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("product_id", sa.BigInteger(), nullable=False),
        sa.Column("spec_key", sa.String(length=50), nullable=False),
        sa.Column("sort", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("product_id", "spec_key", name="uq_product_spec_keys_product_key"),
    )
    op.create_index("ix_product_spec_keys_product_id", "product_spec_keys", ["product_id"])

    # 6. 规格键下的可选值
    op.create_table(
        "product_spec_values",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("spec_key_id", sa.BigInteger(), nullable=False),
        sa.Column("value", sa.String(length=100), nullable=False),
        sa.Column("sort", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["spec_key_id"], ["product_spec_keys.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("spec_key_id", "value", name="uq_product_spec_values_key_value"),
    )
    op.create_index("ix_product_spec_values_spec_key_id", "product_spec_values", ["spec_key_id"])

    # 7. 变体 ↔ 规格值关联（决定 SKU 组合）
    op.create_table(
        "variant_specs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("variant_id", sa.UUID(), nullable=False),
        sa.Column("spec_key_id", sa.BigInteger(), nullable=False),
        sa.Column("spec_value_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["variant_id"], ["product_variants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["spec_key_id"], ["product_spec_keys.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["spec_value_id"], ["product_spec_values.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("variant_id", "spec_key_id", name="uq_variant_specs_variant_key"),
    )
    op.create_index("ix_variant_specs_variant_id", "variant_specs", ["variant_id"])
    op.create_index("ix_variant_specs_spec_value_id", "variant_specs", ["spec_value_id"])

    # 8. products 新增外键列（过渡期与 category/brand 字符串双写）
    op.add_column("products", sa.Column("category_id", sa.BigInteger(), nullable=True))
    op.add_column("products", sa.Column("brand_id", sa.BigInteger(), nullable=True))
    op.add_column("products", sa.Column("product_type_id", sa.BigInteger(), nullable=True))
    op.create_index("ix_products_category_id", "products", ["category_id"])
    op.create_index("ix_products_brand_id", "products", ["brand_id"])
    op.create_index("ix_products_product_type_id", "products", ["product_type_id"])
    op.create_foreign_key(
        "products_category_id_fkey", "products", "product_categories", ["category_id"], ["id"]
    )
    op.create_foreign_key("products_brand_id_fkey", "products", "brands", ["brand_id"], ["id"])
    op.create_foreign_key(
        "products_product_type_id_fkey", "products", "product_types", ["product_type_id"], ["id"]
    )

    # 9. product_variants 新增库存预警值（D5）
    op.add_column(
        "product_variants",
        sa.Column("low_stock_threshold", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    # 1. 删除 products 外键与列
    op.drop_constraint("products_product_type_id_fkey", "products", type_="foreignkey")
    op.drop_constraint("products_brand_id_fkey", "products", type_="foreignkey")
    op.drop_constraint("products_category_id_fkey", "products", type_="foreignkey")
    op.drop_index("ix_products_product_type_id", table_name="products")
    op.drop_index("ix_products_brand_id", table_name="products")
    op.drop_index("ix_products_category_id", table_name="products")
    op.drop_column("products", "product_type_id")
    op.drop_column("products", "brand_id")
    op.drop_column("products", "category_id")

    # 2. 删除变体预警值
    op.drop_column("product_variants", "low_stock_threshold")

    # 3. 删除规格关联表（按依赖顺序）
    op.drop_index("ix_variant_specs_spec_value_id", table_name="variant_specs")
    op.drop_index("ix_variant_specs_variant_id", table_name="variant_specs")
    op.drop_table("variant_specs")
    op.drop_index("ix_product_spec_values_spec_key_id", table_name="product_spec_values")
    op.drop_table("product_spec_values")
    op.drop_index("ix_product_spec_keys_product_id", table_name="product_spec_keys")
    op.drop_table("product_spec_keys")
    op.drop_index("ix_product_type_specs_type_id", table_name="product_type_specs")
    op.drop_table("product_type_specs")
    op.drop_index("ix_product_types_name", table_name="product_types")
    op.drop_table("product_types")
    op.drop_index("ix_brands_name", table_name="brands")
    op.drop_table("brands")
    op.drop_index("ix_product_categories_slug", table_name="product_categories")
    op.drop_index("ix_product_categories_parent_id", table_name="product_categories")
    op.drop_table("product_categories")
