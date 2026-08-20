"""Supplier — Application Service.

承载供应商业务规则：名称唯一校验、integration_type 取值校验。
API 层负责 HTTP 语义与错误映射，本层只抛领域异常。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from forge.infrastructure.persistence.models import ORMSupplier
from forge.infrastructure.persistence.repositories.supplier_repo import (
    SQLAlchemySupplierRepository,
)
from forge.suppliers.registry import list_providers

VALID_INTEGRATION_TYPES = {"manual", "api", "dropship"}


def _provider_codes() -> set[str]:
    return {item["provider_code"] for item in list_providers()}


class SupplierValidationError(ValueError):
    """业务校验失败，携带字段级错误明细。"""

    def __init__(self, message: str, errors: dict[str, str] | None = None):
        super().__init__(message)
        self.errors = errors or {}


class SupplierNameConflictError(ValueError):
    pass


class SupplierService:
    """供应商业务规则层。"""

    @staticmethod
    async def create_supplier(db: AsyncSession, data: dict[str, Any]) -> ORMSupplier:
        errors = SupplierService._validate_base(data)
        if errors:
            raise SupplierValidationError("供应商参数校验失败", errors)

        name = str(data["name"]).strip()
        existing = await SQLAlchemySupplierRepository.get_by_name(db, name)
        if existing:
            raise SupplierNameConflictError(f"供应商名称已存在: {name}")

        payload = dict(data)
        payload["name"] = name
        payload.setdefault("integration_type", "manual")
        payload.setdefault("default_currency", "USD")
        payload.setdefault("is_active", True)
        return await SQLAlchemySupplierRepository.create(db, payload)

    @staticmethod
    async def update_supplier(
        db: AsyncSession,
        supplier: ORMSupplier,
        data: dict[str, Any],
    ) -> ORMSupplier:
        errors = SupplierService._validate_base(data, partial=True)
        if errors:
            raise SupplierValidationError("供应商参数校验失败", errors)

        if "name" in data and data["name"] != supplier.name:
            new_name = str(data["name"]).strip()
            existing = await SQLAlchemySupplierRepository.get_by_name(db, new_name)
            if existing and existing.id != supplier.id:
                raise SupplierNameConflictError(f"供应商名称已存在: {new_name}")
            data["name"] = new_name

        return await SQLAlchemySupplierRepository.update(db, supplier, data)

    @staticmethod
    async def set_active(db: AsyncSession, supplier: ORMSupplier, is_active: bool) -> ORMSupplier:
        return await SQLAlchemySupplierRepository.update(db, supplier, {"is_active": is_active})

    @staticmethod
    def _validate_base(data: dict[str, Any], partial: bool = False) -> dict[str, str]:
        errors: dict[str, str] = {}

        if "name" in data or not partial:
            name = data.get("name")
            if not name or not str(name).strip():
                errors["name"] = "名称不能为空"
            elif len(str(name)) > 255:
                errors["name"] = "名称长度不能超过 255"

        if "contact_email" in data and data["contact_email"] and len(str(data["contact_email"])) > 320:
            errors["contact_email"] = "邮箱长度不能超过 320"

        if "contact_phone" in data and data["contact_phone"] and len(str(data["contact_phone"])) > 50:
            errors["contact_phone"] = "电话长度不能超过 50"

        if "integration_type" in data and data["integration_type"] not in VALID_INTEGRATION_TYPES:
            errors["integration_type"] = f"integration_type 必须为 {sorted(VALID_INTEGRATION_TYPES)} 之一"

        if "provider_code" in data and data["provider_code"]:
            if data["provider_code"] not in _provider_codes():
                errors["provider_code"] = f"未注册的供应商类型: {data['provider_code']}"
            elif data.get("integration_type", "manual") == "manual":
                errors["provider_code"] = "integration_type=manual 时不可设置 provider_code"

        if "config" in data and data["config"] is not None and not isinstance(data["config"], dict):
            errors["config"] = "config 必须是 JSON 对象"

        return errors
