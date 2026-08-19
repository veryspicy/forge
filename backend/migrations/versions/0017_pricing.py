"""add_pricing_rules_and_promotions

Revision ID: 0017_pricing
Revises: 0016_suppliers
Create Date: 2026-08-19

P1 定价引擎：
- pricing_rules：区域倍率 + 固定运费，按优先级匹配，GLOBAL 为全局默认
- promotions：促销活动（COUPON/DISCOUNT/BUNDLE），适用区域/品类，时间窗
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0017_pricing"
down_revision: str | None = "0016_suppliers"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 遗留空表直接重建（count=0、无引用，结构与 P1 目标不一致）
    op.drop_table("pricing_rules")
    op.drop_table("promotions")

    op.create_table(
        "pricing_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("region", sa.String(16), nullable=False, server_default="GLOBAL"),
        sa.Column("markup_multiplier", sa.Numeric(10, 4), nullable=False, server_default="1.4"),
        sa.Column("fixed_shipping_fee", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("markup_multiplier > 1.0", name="ck_pricing_rules_multiplier"),
    )
    op.create_index("ix_pricing_rules_region", "pricing_rules", ["region"])

    op.create_table(
        "promotions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("type", sa.String(32), nullable=False, server_default="COUPON"),
        sa.Column("applicable_regions", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("applicable_categories", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("start_date", sa.DateTime(timezone=False), nullable=True),
        sa.Column("end_date", sa.DateTime(timezone=False), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("stackable", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("config", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "type IN ('COUPON','DISCOUNT','BUNDLE')",
            name="ck_promotions_type",
        ),
    )


def downgrade() -> None:
    op.drop_index("ix_pricing_rules_region", table_name="pricing_rules")
    op.drop_table("pricing_rules")
    op.drop_table("promotions")
