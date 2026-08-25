"""products_bigint_id

Revision ID: 0027_products_bigint_id
Revises: 0026_product_status_deleted
Create Date: 2026-08-24

商品主键迁移：products.id 由 UUID 改为 BIGINT 自增（方案A）。
- 子表 product_variants / order_items / cart_items 的 product_id 同步转为 BIGINT 并重建外键。
- 新增业务字段：brand / is_new / is_recommend / sort_order / sales / audit_status。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0027_products_bigint_id"
down_revision: str | None = "0026_product_status_deleted"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. 删除子表外键（先解除对 products.id 的引用）
    op.drop_constraint("product_variants_product_id_fkey", "product_variants", type_="foreignkey")
    op.drop_constraint("order_items_product_id_fkey", "order_items", type_="foreignkey")
    op.drop_constraint("cart_items_product_id_fkey", "cart_items", type_="foreignkey")

    # 2. products 新增 bigint 自增列并回填现有行
    op.execute("ALTER TABLE products ADD COLUMN id_new BIGINT")
    op.execute("CREATE SEQUENCE IF NOT EXISTS products_id_new_seq")
    op.execute("UPDATE products SET id_new = nextval('products_id_new_seq')")
    op.execute("ALTER TABLE products ALTER COLUMN id_new SET DEFAULT nextval('products_id_new_seq')")
    op.execute("ALTER SEQUENCE products_id_new_seq OWNED BY products.id_new")
    op.execute("ALTER TABLE products ALTER COLUMN id_new SET NOT NULL")

    # 3. 子表新增映射列并回填
    for table in ("product_variants", "order_items", "cart_items"):
        op.execute(f"ALTER TABLE {table} ADD COLUMN product_id_new BIGINT")
        op.execute(f"UPDATE {table} t SET product_id_new = p.id_new FROM products p WHERE p.id = t.product_id")
        op.execute(f"ALTER TABLE {table} ALTER COLUMN product_id_new SET NOT NULL")
        op.execute(f"ALTER TABLE {table} DROP COLUMN product_id")
        op.execute(f"ALTER TABLE {table} RENAME COLUMN product_id_new TO product_id")

    # 4. products 更换主键
    op.execute("ALTER TABLE products DROP CONSTRAINT products_pkey")
    op.execute("ALTER TABLE products DROP COLUMN id")
    op.execute("ALTER TABLE products RENAME COLUMN id_new TO id")
    op.execute("ALTER TABLE products ADD PRIMARY KEY (id)")

    # 5. 重建子表外键
    op.create_foreign_key(
        "product_variants_product_id_fkey",
        "product_variants",
        "products",
        ["product_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "order_items_product_id_fkey",
        "order_items",
        "products",
        ["product_id"],
        ["id"],
    )
    op.create_foreign_key(
        "cart_items_product_id_fkey",
        "cart_items",
        "products",
        ["product_id"],
        ["id"],
    )

    # 6. 新增业务字段
    op.add_column("products", sa.Column("brand", sa.String(length=255), nullable=True))
    op.add_column("products", sa.Column("is_new", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("products", sa.Column("is_recommend", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("products", sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("products", sa.Column("sales", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("products", sa.Column("audit_status", sa.String(length=20), nullable=False, server_default="pending"))

    # 7. 序列已 OWNED BY products.id_new，重命名列后自动跟随，无需额外处理。


def downgrade() -> None:
    # 1. 删除新增业务字段
    op.drop_column("products", "audit_status")
    op.drop_column("products", "sales")
    op.drop_column("products", "sort_order")
    op.drop_column("products", "is_recommend")
    op.drop_column("products", "is_new")
    op.drop_column("products", "brand")

    # 2. 删除子表外键
    op.drop_constraint("product_variants_product_id_fkey", "product_variants", type_="foreignkey")
    op.drop_constraint("order_items_product_id_fkey", "order_items", type_="foreignkey")
    op.drop_constraint("cart_items_product_id_fkey", "cart_items", type_="foreignkey")

    # 3. products 换回 uuid 主键（新行生成 gen_random_uuid）
    op.execute("ALTER TABLE products ADD COLUMN id_new UUID DEFAULT gen_random_uuid()")
    op.execute("UPDATE products SET id_new = gen_random_uuid()")
    op.execute("ALTER TABLE products ALTER COLUMN id_new SET NOT NULL")

    # 4. 子表回填映射列
    for table in ("product_variants", "order_items", "cart_items"):
        op.execute(f"ALTER TABLE {table} ADD COLUMN product_id_new UUID")
        op.execute(f"UPDATE {table} t SET product_id_new = p.id_new FROM products p WHERE p.id = t.product_id")
        op.execute(f"ALTER TABLE {table} ALTER COLUMN product_id_new SET NOT NULL")
        op.execute(f"ALTER TABLE {table} DROP COLUMN product_id")
        op.execute(f"ALTER TABLE {table} RENAME COLUMN product_id_new TO product_id")

    # 5. products 换主键
    op.execute("ALTER TABLE products DROP CONSTRAINT products_pkey")
    op.execute("ALTER TABLE products DROP COLUMN id")
    op.execute("ALTER TABLE products RENAME COLUMN id_new TO id")
    op.execute("ALTER TABLE products ADD PRIMARY KEY (id)")

    # 6. 重建子表外键
    op.create_foreign_key(
        "product_variants_product_id_fkey",
        "product_variants",
        "products",
        ["product_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "order_items_product_id_fkey",
        "order_items",
        "products",
        ["product_id"],
        ["id"],
    )
    op.create_foreign_key(
        "cart_items_product_id_fkey",
        "cart_items",
        "products",
        ["product_id"],
        ["id"],
    )
