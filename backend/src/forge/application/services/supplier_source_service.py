"""Supplier Source — Application Service（P2-5 多供应商货源管理）。

承载凭据管理（Access Token / OAuth2.0 PKCE）、货源搜索、导入、增量同步、同步日志。
"""

from __future__ import annotations

import secrets
from contextlib import suppress
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from forge.infrastructure.persistence.models import (
    ORMSupplier,
    ORMSupplierCredential,
    ORMSupplierSyncLog,
)
from forge.infrastructure.persistence.repositories.supplier_repo import (
    SQLAlchemySupplierRepository,
)
from forge.suppliers.base import (
    ProviderAuthError,
    ProviderConnectionError,
    ProviderNotFoundError,
)
from forge.suppliers.registry import get_provider
from forge.suppliers.schemas import SyncSummary


class SupplierSourceError(ValueError):
    pass


class SupplierSourceService:
    """多供应商货源服务。"""

    # ------------------------------------------------------------------
    # 凭据管理
    # ------------------------------------------------------------------
    @staticmethod
    async def get_credential(
        db: AsyncSession,
        supplier_id: Any,
    ) -> ORMSupplierCredential | None:
        return await db.scalar(select(ORMSupplierCredential).where(ORMSupplierCredential.supplier_id == supplier_id))

    @staticmethod
    async def save_token(
        db: AsyncSession,
        *,
        supplier: ORMSupplier,
        access_token: str,
        refresh_token: str | None = None,
        token_type: str | None = None,
        expires_at: datetime | None = None,
        auth_type: str = "token",
    ) -> ORMSupplierCredential:
        credential = await SupplierSourceService.get_credential(db, supplier.id)
        if credential is None:
            credential = ORMSupplierCredential(
                supplier_id=supplier.id,
                provider_code=supplier.provider_code or "",
                auth_type=auth_type,
            )
            db.add(credential)
        credential.access_token = access_token
        credential.refresh_token = refresh_token
        credential.token_type = token_type
        credential.expires_at = expires_at
        credential.auth_type = auth_type
        credential.updated_at = datetime.now()
        await db.flush()
        return credential

    @staticmethod
    async def start_oauth(
        db: AsyncSession,
        *,
        supplier: ORMSupplier,
    ) -> tuple[str, str]:
        """生成 OAuth2.0 PKCE 授权链接。返回 (state, auth_url)。"""
        provider = get_provider(supplier.provider_code or "")
        if "oauth_pkce" not in provider.auth_types:
            raise SupplierSourceError(f"供应商 {supplier.provider_code} 不支持 OAuth 授权")

        state = secrets.token_urlsafe(32)
        credential = await SupplierSourceService.get_credential(db, supplier.id)
        if credential is None:
            credential = ORMSupplierCredential(
                supplier_id=supplier.id,
                provider_code=supplier.provider_code or "",
                auth_type="oauth_pkce",
            )
            db.add(credential)
        credential.oauth_state = state
        credential.updated_at = datetime.now()
        await db.flush()

        auth_url = await provider.build_auth_url(state)
        return state, auth_url

    @staticmethod
    async def complete_oauth(
        db: AsyncSession,
        *,
        supplier: ORMSupplier,
        code: str,
        state: str,
        verifier: str,
    ) -> ORMSupplierCredential:
        provider = get_provider(supplier.provider_code or "")
        credential = await SupplierSourceService.get_credential(db, supplier.id)
        if credential is None or not credential.oauth_state or credential.oauth_state != state:
            raise SupplierSourceError("OAuth state 不匹配或已过期")

        tokens = await provider.exchange_token(code, verifier)
        credential.access_token = tokens.get("access_token") or ""
        credential.refresh_token = tokens.get("refresh_token")
        credential.token_type = tokens.get("token_type")
        if tokens.get("expires_in"):
            with suppress(TypeError, ValueError, OSError):
                credential.expires_at = datetime.fromtimestamp(
                    int(datetime.now().timestamp()) + int(tokens["expires_in"])
                )
        credential.oauth_state = None
        credential.auth_type = "oauth_pkce"
        credential.updated_at = datetime.now()
        await db.flush()
        return credential

    # ------------------------------------------------------------------
    # 货源搜索
    # ------------------------------------------------------------------
    @staticmethod
    async def search_products(
        db: AsyncSession,
        *,
        supplier: ORMSupplier,
        keyword: str = "",
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        provider = get_provider(supplier.provider_code or "")
        credential = await SupplierSourceService.get_credential(db, supplier.id)
        if credential is None or not credential.access_token:
            raise SupplierSourceError("供应商尚未配置 Access Token")

        result = await provider.search(
            credential=credential,
            keyword=keyword,
            page=page,
            page_size=page_size,
        )
        return {
            "items": [item.__dict__ for item in result.items],
            "total": result.total,
            "page": result.page,
            "page_size": result.page_size,
        }

    # ------------------------------------------------------------------
    # 导入与同步
    # ------------------------------------------------------------------
    @staticmethod
    async def import_products(
        db: AsyncSession,
        *,
        supplier: ORMSupplier,
        provider_product_ids: list[str],
    ) -> dict[str, Any]:
        """按厂商侧商品 ID 拉取最新详情并导入为商品草稿（幂等）。"""
        provider = get_provider(supplier.provider_code or "")
        credential = await SupplierSourceService.get_credential(db, supplier.id)
        if credential is None or not credential.access_token:
            raise SupplierSourceError("供应商尚未配置 Access Token")

        imported: list[dict[str, Any]] = []
        failed: list[dict[str, str]] = []
        for pid in provider_product_ids:
            try:
                product = await provider.get_product(credential=credential, provider_product_id=pid)
                orm = await provider.import_product(db, supplier=supplier, product=product)
                imported.append(
                    {
                        "provider_product_id": pid,
                        "product_id": str(orm.id),
                        "name": orm.name,
                        "sku": orm.sku,
                        "status": orm.status,
                    }
                )
            except Exception as exc:  # noqa: BLE001 - 单个商品失败不中断批量导入
                failed.append({"provider_product_id": pid, "error": str(exc)})

        await db.commit()
        return {"imported": imported, "failed": failed}

    @staticmethod
    async def sync_supplier(
        db: AsyncSession,
        *,
        supplier: ORMSupplier,
        trigger_type: str = "manual",
    ) -> ORMSupplierSyncLog:
        """手动/定时增量同步库存与价格，记录同步日志。"""
        provider = get_provider(supplier.provider_code or "")
        credential = await SupplierSourceService.get_credential(db, supplier.id)
        if credential is None or not credential.access_token:
            raise SupplierSourceError("供应商尚未配置 Access Token")

        log = ORMSupplierSyncLog(
            supplier_id=supplier.id,
            provider_code=supplier.provider_code or "",
            trigger_type=trigger_type,
            status="running",
        )
        db.add(log)
        await db.flush()

        summary = SyncSummary()
        try:
            summary = await provider.sync_inventory_price(
                db,
                supplier=supplier,
                credential=credential,
            )
            log.status = "success" if not summary.error else "partial"
            log.error = summary.error or None
        except ProviderAuthError as exc:
            log.status = "failed"
            log.error = f"鉴权失败: {exc}"
        except (ProviderConnectionError, Exception) as exc:  # noqa: BLE001
            log.status = "partial" if summary.items_updated else "failed"
            log.error = str(exc)

        log.items_total = summary.items_total
        log.items_imported = summary.items_imported
        log.items_updated = summary.items_updated
        log.finished_at = datetime.now()
        await db.commit()
        await db.refresh(log)
        return log

    @staticmethod
    async def list_sync_logs(
        db: AsyncSession,
        *,
        supplier_id: Any,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        rows = (
            await db.scalars(
                select(ORMSupplierSyncLog)
                .where(ORMSupplierSyncLog.supplier_id == supplier_id)
                .order_by(ORMSupplierSyncLog.started_at.desc())
                .limit(limit)
            )
        ).all()
        return [row.to_dict() for row in rows]


async def get_supplier_with_provider(db: AsyncSession, supplier_id: Any) -> ORMSupplier:
    """校验供应商存在且已配置 provider。"""
    supplier = await SQLAlchemySupplierRepository.get_by_id(db, supplier_id)
    if supplier is None:
        raise ProviderNotFoundError("供应商不存在")
    if not supplier.provider_code:
        raise SupplierSourceError("该供应商未配置厂商类型 (provider_code)")
    return supplier
