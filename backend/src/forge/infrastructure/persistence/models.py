"""SQLAlchemy ORM models — auto-mapped tables.

实际表结构由 Alembic 迁移管理，此文件仅声明 SQLAlchemy 映射类。
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    Numeric,
    String,
    Text,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, relationship

__all__ = [
    "Base",
    "ORMDiyPage",
    "ORMDiyComponent",
    "ORMDiyPageComponent",
    "ORMProduct",
    "ORMUser",
    "ORMAdminUser",
    "ORMRole",
    "ORMOrderItem",
    "ORMOrder",
    "ORMSiteProfile",
]


class Base(DeclarativeBase):
    pass


class ORMDiyPage(Base):
    __tablename__ = "diy_pages"

    id = Column(UUID(as_uuid=True), primary_key=True,
                server_default="gen_random_uuid()")
    name = Column(String(128), nullable=False)
    slug = Column(String(128), nullable=False, unique=True)
    title = Column(String(256), nullable=False, default="")
    description = Column(Text, nullable=False, default="")
    page_type = Column(String(32), nullable=False, default="custom")
    status = Column(String(16), nullable=False, default="draft")
    is_default = Column(Boolean, nullable=False, default=False)
    is_template = Column(Boolean, nullable=False, default=False)
    industry_tag = Column(String(64), nullable=True)
    template_thumbnail = Column(String(512), nullable=True)
    template_description = Column(Text, nullable=True)
    snapshot_config = Column(JSONB, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(UUID(as_uuid=True),
                        ForeignKey("admin_users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False,
                        server_default="now()")
    updated_at = Column(DateTime(timezone=True), nullable=False,
                        server_default="now()")

    components = relationship(
        "ORMDiyPageComponent",
        back_populates="page",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.name,
            "slug": self.slug,
            "title": self.title,
            "description": self.description,
            "page_type": self.page_type,
            "status": self.status,
            "is_default": self.is_default,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "components": [
                {
                    "id": str(c.id),
                    "component_id": str(c.component_id),
                    "component": c.component.to_dict() if c.component else None,
                    "sort_order": c.sort_order,
                    "config": c.config or {},
                    "is_visible": c.is_visible,
                }
                for c in (self.components or [])
            ],
        }


class ORMDiyComponent(Base):
    __tablename__ = "diy_components"

    id = Column(UUID(as_uuid=True), primary_key=True,
                server_default="gen_random_uuid()")
    code = Column(String(64), nullable=False, unique=True)
    name = Column(String(128), nullable=False)
    category = Column(String(32), nullable=False, default="basic")
    icon = Column(String(64), nullable=False, default="mdi:widget")
    default_config = Column(JSONB, nullable=False, default=dict)
    config_schema = Column(JSONB, nullable=False, default=dict)
    is_system = Column(Boolean, nullable=False, default=True)
    sort_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False,
                        server_default="now()")
    updated_at = Column(DateTime(timezone=True), nullable=False,
                        server_default="now()")

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "code": self.code,
            "name": self.name,
            "category": self.category,
            "icon": self.icon,
            "default_config": self.default_config or {},
            "config_schema": self.config_schema or {},
            "is_system": self.is_system,
            "sort_order": self.sort_order,
            "is_active": self.is_active,
        }


class ORMDiyPageComponent(Base):
    __tablename__ = "diy_page_components"

    id = Column(UUID(as_uuid=True), primary_key=True,
                server_default="gen_random_uuid()")
    page_id = Column(UUID(as_uuid=True),
                     ForeignKey("diy_pages.id", ondelete="CASCADE"), nullable=False)
    component_id = Column(UUID(as_uuid=True),
                          ForeignKey("diy_components.id"), nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)
    config = Column(JSONB, nullable=False, default=dict)
    is_visible = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False,
                        server_default="now()")
    updated_at = Column(DateTime(timezone=True), nullable=False,
                        server_default="now()")

    page: Mapped[ORMDiyPage] = relationship(
        "ORMDiyPage", back_populates="components"
    )
    component: Mapped[ORMDiyComponent] = relationship("ORMDiyComponent")


class ORMProduct(Base):
    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True,
                server_default="gen_random_uuid()")
    sku = Column(String(100), nullable=False)
    slug = Column(String(500), nullable=False)
    name = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    ai_description = Column(Text, nullable=True)
    price = Column(Numeric(12, 2), nullable=False)
    cost = Column(Numeric(12, 2), nullable=False)
    category = Column(String(50), nullable=False)
    breed_groups = Column(ARRAY(String), nullable=True)
    suitable_for = Column(JSONB, nullable=False, default=dict)
    tags = Column(ARRAY(String), nullable=True)
    inventory = Column(Integer, nullable=False, default=0)
    region_availability = Column(ARRAY(String), nullable=True)
    seo_keywords = Column(ARRAY(String), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False,
                        server_default="now()")
    updated_at = Column(DateTime(timezone=True), nullable=False,
                        server_default="now()")

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "sku": self.sku,
            "slug": self.slug,
            "name": self.name,
            "description": self.description,
            "ai_description": self.ai_description,
            "price": float(self.price) if self.price else 0,
            "cost": float(self.cost) if self.cost else 0,
            "category": self.category,
            "breed_groups": self.breed_groups or [],
            "suitable_for": self.suitable_for or {},
            "tags": self.tags or [],
            "inventory": self.inventory,
            "region_availability": self.region_availability or [],
            "seo_keywords": self.seo_keywords or [],
        }


class ORMUser(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True,
                server_default="gen_random_uuid()")
    email = Column(String(320), nullable=False, unique=True)
    password_hash = Column(String(128), nullable=False)
    name = Column(String(200), nullable=False)
    role = Column(String(20), nullable=False, default="customer")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=False), nullable=False,
                        server_default="now()")
    updated_at = Column(DateTime(timezone=False), nullable=False,
                        server_default="now()")


class ORMAdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(UUID(as_uuid=True), primary_key=True,
                server_default="gen_random_uuid()")
    email = Column(String(320), nullable=False, unique=True)
    password_hash = Column(String(128), nullable=False)
    display_name = Column(String(200), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    last_login_at = Column(DateTime(timezone=False), nullable=True)
    created_at = Column(DateTime(timezone=False), nullable=False,
                        server_default="now()")
    updated_at = Column(DateTime(timezone=False), nullable=False,
                        server_default="now()")


class ORMRole(Base):
    __tablename__ = "roles"

    id = Column(UUID(as_uuid=True), primary_key=True,
                server_default="gen_random_uuid()")
    name = Column(String(50), nullable=False, unique=True)
    display_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_system = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=False), nullable=False,
                        server_default="now()")
    updated_at = Column(DateTime(timezone=False), nullable=False,
                        server_default="now()")


class ORMOrderItem(Base):
    __tablename__ = "order_items"

    id = Column(UUID(as_uuid=True), primary_key=True,
                server_default="gen_random_uuid()")
    order_id = Column(UUID(as_uuid=True),
                      ForeignKey("orders.id"), nullable=False)
    product_id = Column(UUID(as_uuid=True),
                        ForeignKey("products.id"), nullable=False)
    name = Column(String(500), nullable=False)
    sku = Column(String(100), nullable=False)
    price = Column(Numeric(12, 2), nullable=False)
    quantity = Column(Integer, nullable=False)
    image = Column(String(1000), nullable=True)

    order: Mapped["ORMOrder"] = relationship("ORMOrder", back_populates="items")


class ORMOrder(Base):
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True,
                server_default="gen_random_uuid()")
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
    created_at = Column(DateTime(timezone=False), nullable=False,
                        server_default="now()")
    updated_at = Column(DateTime(timezone=False), nullable=False,
                        server_default="now()")

    items: Mapped[list["ORMOrderItem"]] = relationship(
        "ORMOrderItem", back_populates="order", lazy="selectin")


class ORMSiteProfile(Base):
    __tablename__ = "site_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True,
                server_default="gen_random_uuid()")
    name = Column(String(64), nullable=False, unique=True)
    label = Column(String(128), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    config = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=False), nullable=False,
                        server_default="now()")
    updated_at = Column(DateTime(timezone=False), nullable=False,
                        server_default="now()")
