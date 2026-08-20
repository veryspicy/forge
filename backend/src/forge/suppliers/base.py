"""供应商抽象基类与领域异常（P2-5）。

新增厂商实现 SupplierProvider 子类即可接入统一货源搜索/导入/同步流程。
"""

from __future__ import annotations

import abc
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from forge.infrastructure.persistence.models import ORMProduct, ORMSupplier, ORMSupplierCredential
from forge.suppliers.schemas import SupplierProduct, SupplierSearchResult, SyncSummary


class ProviderNotFoundError(LookupError):
    """供应商类型未注册。"""


class ProviderConnectionError(ConnectionError):
    """与厂商 API/MCP 通信失败。"""


class ProviderAuthError(PermissionError):
    """厂商凭据无效或过期。"""


class SupplierProvider(abc.ABC):
    """厂商适配器基类。子类实现统一契约，供服务层与 API 层无差别调用。"""

    #: 供应商类型标识（存储于 suppliers.provider_code）
    provider_code: str = ""
    #: 展示名
    display_name: str = ""
    #: 支持的鉴权方式："token" / "oauth_pkce"
    auth_types: tuple[str, ...] = ("token",)
    #: 是否支持自动定时增量同步
    supports_scheduled_sync: bool = True

    # ------------------------------------------------------------------
    # 货源搜索
    # ------------------------------------------------------------------
    @abc.abstractmethod
    async def search(
        self,
        *,
        credential: ORMSupplierCredential,
        keyword: str = "",
        page: int = 1,
        page_size: int = 20,
    ) -> SupplierSearchResult:
        """按关键词/热门搜索厂商货源，返回归一化商品列表。"""

    @abc.abstractmethod
    async def get_product(
        self,
        *,
        credential: ORMSupplierCredential,
        provider_product_id: str,
    ) -> SupplierProduct:
        """按厂商侧商品 ID 获取单个商品最新信息。"""

    # ------------------------------------------------------------------
    # 导入与同步
    # ------------------------------------------------------------------
    @abc.abstractmethod
    async def import_product(
        self,
        db: AsyncSession,
        *,
        supplier: ORMSupplier,
        product: SupplierProduct,
    ) -> ORMProduct:
        """将货源商品导入为本站商品草稿（products.status=draft）。

        实现方负责 SKU 生成、supplier_id / supplier_sku / supplier_product_id 回填。
        """

    @abc.abstractmethod
    async def sync_inventory_price(
        self,
        db: AsyncSession,
        *,
        supplier: ORMSupplier,
        credential: ORMSupplierCredential,
    ) -> SyncSummary:
        """增量同步本站已导入商品的价格/库存（按 supplier_product_id 匹配）。"""

    # ------------------------------------------------------------------
    # 鉴权（token 直存 / OAuth2.0 PKCE）
    # ------------------------------------------------------------------
    async def build_auth_url(self, state: str) -> str:
        """生成 OAuth2.0 PKCE 授权链接；不支持的厂商抛 NotImplementedError。"""
        raise NotImplementedError(f"供应商 {self.provider_code} 不支持 OAuth 授权")

    async def exchange_token(self, code: str, verifier: str) -> dict[str, Any]:
        """用授权码换取 token；不支持的厂商抛 NotImplementedError。"""
        raise NotImplementedError(f"供应商 {self.provider_code} 不支持 OAuth 授权")
