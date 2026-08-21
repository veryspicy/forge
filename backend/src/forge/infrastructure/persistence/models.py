"""SQLAlchemy ORM models — auto-mapped tables.

实际表结构由 Alembic 迁移管理，此文件仅声明 SQLAlchemy 映射类。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

__all__ = [
    "Base",
    "ORMProduct",
    "ORMProductVariant",
    "ORMSupplier",
    "ORMSupplierCredential",
    "ORMSupplierSyncLog",
    "ORMUser",
    "ORMAdminUser",
    "ORMRole",
    "ORMOrderItem",
    "ORMOrder",
    "ORMSiteProfile",
    "ORMResource",
    "ORMResourceRef",
]


class Base(DeclarativeBase):
    pass


class ORMProduct(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("price > 0", name="ck_products_price_positive"),
        CheckConstraint("inventory >= 0", name="ck_products_inventory_nonneg"),
        CheckConstraint(
            "status IN ('draft','active','inactive')",
            name="ck_products_status",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    sku = Column(String(100), nullable=False, unique=True)
    slug = Column(String(500), nullable=False, unique=True)
    name = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    ai_description = Column(Text, nullable=True)
    name_translations = Column(JSONB, nullable=False, default=dict)
    description_translations = Column(JSONB, nullable=False, default=dict)
    ai_description_translations = Column(JSONB, nullable=False, default=dict)
    price = Column(Numeric(12, 2), nullable=False)
    cost = Column(Numeric(12, 2), nullable=False)
    category = Column(String(50), nullable=False, index=True)
    breed_groups: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    suitable_for = Column(JSONB, nullable=False, default=dict)
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    inventory = Column(Integer, nullable=False, default=0)
    status = Column(String(20), nullable=False, default="draft", index=True)
    images = Column(JSONB, nullable=False, default=list)
    supplier_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    supplier_sku = Column(String(100), nullable=True)
    supplier_product_id = Column(String(128), nullable=True, index=True)
    rating = Column(Float, nullable=False, default=0.0)
    review_count = Column(Integer, nullable=False, default=0)
    is_ai_generated = Column(Boolean, nullable=False, default=False)
    region_availability: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    seo_title = Column(String(500), nullable=True)
    seo_description = Column(Text, nullable=True)
    seo_keywords: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default="now()")
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default="now()")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "sku": self.sku,
            "slug": self.slug,
            "name": self.name,
            "description": self.description,
            "ai_description": self.ai_description,
            "name_translations": self.name_translations or {},
            "description_translations": self.description_translations or {},
            "ai_description_translations": self.ai_description_translations or {},
            "price": float(self.price) if self.price else 0,
            "cost": float(self.cost) if self.cost else 0,
            "category": self.category,
            "breed_groups": self.breed_groups or [],
            "suitable_for": self.suitable_for or {},
            "tags": self.tags or [],
            "inventory": self.inventory,
            "status": self.status or "draft",
            "images": self.images or [],
            "supplier_id": str(self.supplier_id) if self.supplier_id else None,
            "supplier_sku": self.supplier_sku,
            "supplier_product_id": self.supplier_product_id,
            "rating": self.rating or 0.0,
            "review_count": self.review_count or 0,
            "is_ai_generated": bool(self.is_ai_generated),
            "region_availability": self.region_availability or [],
            "seo_title": self.seo_title,
            "seo_description": self.seo_description,
            "seo_keywords": self.seo_keywords or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ORMProductVariant(Base):
    """商品变体表（P2-1 变体管理）。"""

    __tablename__ = "product_variants"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    product_id = Column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sku = Column(String(100), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    attributes = Column(JSONB, nullable=False, default=dict)
    price = Column(Numeric(12, 2), nullable=True)
    cost = Column(Numeric(12, 2), nullable=True)
    inventory = Column(Integer, nullable=False, default=0)
    status = Column(String(20), nullable=False, default="active", index=True)
    is_default = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default="now()")
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default="now()")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "product_id": str(self.product_id) if self.product_id else None,
            "sku": self.sku,
            "name": self.name,
            "attributes": self.attributes or {},
            "price": float(self.price) if self.price else None,
            "cost": float(self.cost) if self.cost else None,
            "inventory": self.inventory or 0,
            "status": self.status or "active",
            "is_default": bool(self.is_default),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ORMSupplier(Base):
    """供应商表（P1 落地，products.supplier_id 届时补外键）。"""

    __tablename__ = "suppliers"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    name = Column(String(255), nullable=False, unique=True)
    contact_email = Column(String(320), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    integration_type = Column(String(32), nullable=False, default="manual")
    provider_code = Column(String(64), nullable=True, index=True)
    config = Column(JSONB, nullable=False, default=dict)
    shipping_regions: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    default_currency = Column(String(10), nullable=False, default="USD")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=False), nullable=False, server_default="now()")
    updated_at = Column(DateTime(timezone=False), nullable=False, server_default="now()")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "name": self.name,
            "contact_email": self.contact_email,
            "contact_phone": self.contact_phone,
            "integration_type": self.integration_type or "manual",
            "provider_code": self.provider_code,
            "config": self.config or {},
            "shipping_regions": self.shipping_regions or [],
            "default_currency": self.default_currency or "USD",
            "is_active": bool(self.is_active),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ORMSupplierCredential(Base):
    """供应商凭据表（P2-5：Access Token / OAuth2.0 PKCE）。"""

    __tablename__ = "supplier_credentials"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    supplier_id = Column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider_code = Column(String(64), nullable=False)
    auth_type = Column(String(16), nullable=False, default="token")
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    token_type = Column(String(32), nullable=True)
    expires_at = Column(DateTime(timezone=False), nullable=True)
    oauth_state = Column(String(128), nullable=True)
    created_at = Column(DateTime(timezone=False), nullable=False, server_default="now()")
    updated_at = Column(DateTime(timezone=False), nullable=False, server_default="now()")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "supplier_id": str(self.supplier_id) if self.supplier_id else None,
            "provider_code": self.provider_code,
            "auth_type": self.auth_type or "token",
            "has_access_token": bool(self.access_token),
            "has_refresh_token": bool(self.refresh_token),
            "token_type": self.token_type,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "oauth_state": self.oauth_state,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ORMSupplierSyncLog(Base):
    """供应商同步日志表（P2-5：手动/定时同步记录）。"""

    __tablename__ = "supplier_sync_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    supplier_id = Column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider_code = Column(String(64), nullable=False)
    trigger_type = Column(String(16), nullable=False, default="manual")
    status = Column(String(16), nullable=False, default="running")
    items_total = Column(Integer, nullable=False, default=0)
    items_imported = Column(Integer, nullable=False, default=0)
    items_updated = Column(Integer, nullable=False, default=0)
    error = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=False), nullable=False, server_default="now()")
    finished_at = Column(DateTime(timezone=False), nullable=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "supplier_id": str(self.supplier_id) if self.supplier_id else None,
            "provider_code": self.provider_code,
            "trigger_type": self.trigger_type or "manual",
            "status": self.status or "running",
            "items_total": self.items_total or 0,
            "items_imported": self.items_imported or 0,
            "items_updated": self.items_updated or 0,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
        }


class ORMUser(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    email = Column(String(320), nullable=False, unique=True)
    password_hash = Column(String(128), nullable=False)
    name = Column(String(200), nullable=False)
    role = Column(String(20), nullable=False, default="customer")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=False), nullable=False, server_default="now()")
    updated_at = Column(DateTime(timezone=False), nullable=False, server_default="now()")


class ORMAdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    email = Column(String(320), nullable=False, unique=True)
    password_hash = Column(String(128), nullable=False)
    display_name = Column(String(200), nullable=False)
    role = Column(String(20), nullable=False, default="super_admin", server_default="super_admin")
    is_active = Column(Boolean, nullable=False, default=True)
    last_login_at = Column(DateTime(timezone=False), nullable=True)
    created_at = Column(DateTime(timezone=False), nullable=False, server_default="now()")
    updated_at = Column(DateTime(timezone=False), nullable=False, server_default="now()")


class ORMRole(Base):
    __tablename__ = "roles"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    name = Column(String(50), nullable=False, unique=True)
    display_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_system = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=False), nullable=False, server_default="now()")
    updated_at = Column(DateTime(timezone=False), nullable=False, server_default="now()")


class ORMOrderItem(Base):
    __tablename__ = "order_items"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    name = Column(String(500), nullable=False)
    sku = Column(String(100), nullable=False)
    price = Column(Numeric(12, 2), nullable=False)
    quantity = Column(Integer, nullable=False)
    image = Column(String(1000), nullable=True)

    order: Mapped[ORMOrder] = relationship("ORMOrder", back_populates="items")


class ORMOrder(Base):
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    order_number = Column(String(50), nullable=False, unique=True)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    subtotal = Column(Numeric(12, 2), nullable=False)
    tax = Column(Numeric(12, 2), nullable=False)
    shipping_cost = Column(Numeric(12, 2), nullable=False)
    discount = Column(Numeric(12, 2), nullable=False)
    total = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(10), nullable=False, default="CNY")
    status = Column(String(50), nullable=False)
    payment_intent_id = Column(String(500), nullable=True)
    tracking_number = Column(String(500), nullable=True)
    shipping_address = Column(JSONB, nullable=True)
    review_status = Column(JSONB, nullable=True)
    procurement_info = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=False), nullable=False, server_default="now()")
    updated_at = Column(DateTime(timezone=False), nullable=False, server_default="now()")

    items: Mapped[list[ORMOrderItem]] = relationship("ORMOrderItem", back_populates="order", lazy="selectin")


class ORMSiteProfile(Base):
    __tablename__ = "site_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    name = Column(String(64), nullable=False, unique=True)
    label = Column(String(128), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    config = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=False), nullable=False, server_default="now()")
    updated_at = Column(DateTime(timezone=False), nullable=False, server_default="now()")


class ORMResource(Base):
    """资源表 - 全站统一上传入口登记（软删，回收站式）。"""

    __tablename__ = "resource"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    site_id = Column(UUID(as_uuid=True), nullable=False)
    bucket = Column(String(128), nullable=False, default="")
    object_key = Column(String(512), nullable=False, default="")
    url = Column(String(1024), nullable=False, default="")
    file_type = Column(String(32), nullable=False, default="document")
    mime = Column(String(128), nullable=False, default="")
    file_size = Column(Integer, nullable=False, default=0)
    sha256 = Column(String(64), nullable=True)
    name = Column(String(255), nullable=False, default="")
    directory = Column(String(255), nullable=False, default="")
    created_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=False), nullable=False, server_default="now()")
    deleted_at = Column(DateTime(timezone=False), nullable=True)


class ORMResourceTag(Base):
    """资源标签表（全局标签，name 唯一）。"""

    __tablename__ = "resource_tag"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    name = Column(String(64), nullable=False, unique=True, index=True)
    created_at = Column(DateTime(timezone=False), nullable=False, server_default="now()")


class ORMResourceTagMap(Base):
    """资源-标签关联表（多对多）。"""

    __tablename__ = "resource_tag_map"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    resource_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    tag_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=False), nullable=False, server_default="now()")


class ORMResourceRef(Base):
    """资源引用关系表 - 用于"引用位置"追踪。"""

    __tablename__ = "resource_ref"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    resource_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    ref_type = Column(String(64), nullable=False, default="")
    ref_id = Column(String(128), nullable=False, default="")
    ref_label = Column(String(255), nullable=False, default="")
    created_at = Column(DateTime(timezone=False), nullable=False, server_default="now()")


class ORMPricingRule(Base):
    """定价规则表（P1：区域倍率 + 固定运费，按优先级匹配）。"""

    __tablename__ = "pricing_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    name = Column(String(255), nullable=False)
    region = Column(String(16), nullable=False, default="GLOBAL", index=True)
    markup_multiplier = Column(Numeric(10, 4), nullable=False, default=1.4)
    fixed_shipping_fee = Column(Numeric(12, 2), nullable=False, default=0.0)
    priority = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    is_default = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=False), nullable=False, server_default="now()")
    updated_at = Column(DateTime(timezone=False), nullable=False, server_default="now()")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "name": self.name,
            "region": self.region or "GLOBAL",
            "markup_multiplier": float(self.markup_multiplier or 1.4),
            "fixed_shipping_fee": float(self.fixed_shipping_fee or 0.0),
            "priority": self.priority or 0,
            "is_active": bool(self.is_active),
            "is_default": bool(self.is_default),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ORMPromotion(Base):
    """促销活动表（P1：优惠券/折扣/捆绑）。"""

    __tablename__ = "promotions"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    name = Column(String(255), nullable=False)
    type = Column(String(32), nullable=False, default="COUPON")
    applicable_regions: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    applicable_categories: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    start_date = Column(DateTime(timezone=False), nullable=True)
    end_date = Column(DateTime(timezone=False), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    stackable = Column(Boolean, nullable=False, default=False)
    priority = Column(Integer, nullable=False, default=0)
    config = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=False), nullable=False, server_default="now()")
    updated_at = Column(DateTime(timezone=False), nullable=False, server_default="now()")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "name": self.name,
            "type": self.type or "COUPON",
            "applicable_regions": self.applicable_regions or [],
            "applicable_categories": self.applicable_categories or [],
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "is_active": bool(self.is_active),
            "stackable": bool(self.stackable),
            "priority": self.priority or 0,
            "config": self.config or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ORMMcpApiKey(Base):
    """对外 MCP Server 的 Agent API Key（P3）。"""

    __tablename__ = "mcp_api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    name = Column(String(128), nullable=False)
    key_prefix = Column(String(16), nullable=False)
    key_hash = Column(String(128), nullable=False, unique=True)
    scopes = Column(JSONB, nullable=False, default=list)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=False), nullable=False, server_default="now()")
    last_used_at = Column(DateTime(timezone=False), nullable=True)
    revoked_at = Column(DateTime(timezone=False), nullable=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "name": self.name,
            "key_prefix": self.key_prefix,
            "scopes": self.scopes or [],
            "is_active": bool(self.is_active),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
        }


class ORMMcpAuditLog(Base):
    """MCP Tool 调用审计日志（P3）。"""

    __tablename__ = "mcp_audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    api_key_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    agent_name = Column(String(128), nullable=True)
    tool_name = Column(String(64), nullable=False)
    arguments = Column(JSONB, nullable=False, default=dict)
    result_status = Column(String(16), nullable=False, default="ok")
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=False), nullable=False, server_default="now()")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "api_key_id": str(self.api_key_id) if self.api_key_id else None,
            "agent_name": self.agent_name,
            "tool_name": self.tool_name,
            "arguments": self.arguments or {},
            "result_status": self.result_status,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
