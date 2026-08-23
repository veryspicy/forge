"""Zendrop 一件代发厂商适配器（P2-5 首个 MCP 供应商）。

通过官方 MCP Server 接入：
- 端点: POST https://app.zendrop.com/mcp/v1
- 鉴权: Bearer Token（Access Token）
- Scopes: catalog:read, my_products:write, orders:read/write, stores:read/write, billing:read
- 限流: 读 120/min、写 30/min、履约 10/min

协议为 MCP JSON-RPC 2.0 over HTTP；真实工具参数以 Zendrop 官方 MCP 契约为准，
本实现做了通用容错解析，适配点集中在 _call_tool 与 _normalize_items。
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from forge.application.services.product_service import ProductService
from forge.infrastructure.persistence.models import ORMProduct, ORMSupplier, ORMSupplierCredential
from forge.main.config import settings
from forge.suppliers.base import ProviderAuthError, ProviderConnectionError, SupplierProvider
from forge.suppliers.schemas import SupplierProduct, SupplierSearchResult, SyncSummary

logger = logging.getLogger(__name__)


class ZendropProvider(SupplierProvider):
    provider_code = "zendrop"
    display_name = "Zendrop"
    auth_types = ("token",)

    def __init__(self, mcp_url: str | None = None) -> None:
        self._mcp_url = mcp_url or settings.zendrop_mcp_url

    # ------------------------------------------------------------------
    # MCP 通信
    # ------------------------------------------------------------------
    async def _call_tool(
        self,
        *,
        credential: ORMSupplierCredential,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> Any:
        if not credential.access_token:
            raise ProviderAuthError(f"供应商 {self.provider_code} 未配置 Access Token")

        headers = {
            "Authorization": f"Bearer {credential.access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments or {},
            },
        }
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(self._mcp_url, json=payload, headers=headers)
                resp.raise_for_status()
                body: dict[str, Any] = resp.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in (401, 403):
                raise ProviderAuthError(f"Zendrop Token 无效或已过期 ({exc.response.status_code})") from exc
            raise ProviderConnectionError(f"Zendrop MCP 调用失败: {exc.response.status_code}") from exc
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            raise ProviderConnectionError(f"Zendrop MCP 通信异常: {exc}") from exc

        if body.get("error"):
            raise ProviderConnectionError(f"Zendrop MCP 返回错误: {body['error']}")

        result = body.get("result", {})
        if result.get("isError"):
            raise ProviderConnectionError(f"Zendrop MCP 工具 {tool_name} 执行失败: {result}")
        return result

    @staticmethod
    def _extract_text(result: dict[str, Any]) -> str:
        """从 MCP tools/call 响应中提取文本内容，兼容多种 content 形态。"""
        content = result.get("content")
        if not content:
            return ""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text")
                    if text is not None:
                        parts.append(str(text))
                elif isinstance(item, str):
                    parts.append(item)
            return "\n".join(parts)
        return str(content)

    @classmethod
    def _normalize_items(cls, raw: Any) -> list[SupplierProduct]:
        """将厂商返回的商品列表归一化为 SupplierProduct。"""
        items: list[Any] = []
        if isinstance(raw, dict):
            for key in ("products", "items", "data", "catalog"):
                val = raw.get(key)
                if isinstance(val, list):
                    items = val
                    break
            else:
                items = [raw]
        elif isinstance(raw, list):
            items = raw

        normalized: list[SupplierProduct] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            pid = str(item.get("id") or item.get("product_id") or item.get("_id") or "")
            if not pid:
                continue
            images = item.get("images") or item.get("image") or []
            if isinstance(images, str):
                images = [images]
            elif isinstance(images, list):
                images = [img.get("url") if isinstance(img, dict) else str(img) for img in images]
            price = float(item.get("price") or item.get("cost") or 0)
            inventory = int(item.get("inventory") or item.get("stock") or 0)
            normalized.append(
                SupplierProduct(
                    provider_code=cls.provider_code,
                    provider_product_id=pid,
                    title=str(item.get("title") or item.get("name") or ""),
                    price=price,
                    inventory=inventory,
                    images=images,
                    description=str(item.get("description") or ""),
                    sku=str(item.get("sku") or ""),
                    currency=str(item.get("currency") or "USD"),
                    variants=item.get("variants") or [],
                    extra={"raw": item},
                )
            )
        return normalized

    # ------------------------------------------------------------------
    # 货源搜索
    # ------------------------------------------------------------------
    async def search(
        self,
        *,
        credential: ORMSupplierCredential,
        keyword: str = "",
        page: int = 1,
        page_size: int = 20,
    ) -> SupplierSearchResult:
        tool_name = "get_catalog_products" if keyword else "get_catalog_trending_products"
        arguments = (
            {"keyword": keyword, "page": page, "limit": page_size} if keyword else {"page": page, "limit": page_size}
        )
        result = await self._call_tool(
            credential=credential,
            tool_name=tool_name,
            arguments=arguments,
        )
        text = self._extract_text(result)
        raw: Any = {}
        if text.strip():
            try:
                raw = json.loads(text)
            except json.JSONDecodeError:
                raw = {"raw_text": text}
        items = self._normalize_items(raw)
        total = 0
        if isinstance(raw, dict):
            total = int(raw.get("total") or raw.get("count") or len(items))
        return SupplierSearchResult(items=items, total=total, page=page, page_size=page_size)

    async def get_product(
        self,
        *,
        credential: ORMSupplierCredential,
        provider_product_id: str,
    ) -> SupplierProduct:
        result = await self._call_tool(
            credential=credential,
            tool_name="get_catalog_product",
            arguments={"product_id": provider_product_id},
        )
        text = self._extract_text(result)
        raw: Any = {}
        if text.strip():
            try:
                raw = json.loads(text)
            except json.JSONDecodeError:
                raw = {"id": provider_product_id, "raw_text": text}
        items = self._normalize_items(raw)
        if not items:
            raise ProviderConnectionError(f"Zendrop 未找到商品 {provider_product_id}")
        return items[0]

    # ------------------------------------------------------------------
    # 导入与同步
    # ------------------------------------------------------------------
    async def import_product(
        self,
        db: AsyncSession,
        *,
        supplier: ORMSupplier,
        product: SupplierProduct,
    ) -> ORMProduct:
        """导入为商品草稿；若 supplier_product_id 已存在则更新而非新建（幂等）。"""
        existing = await db.scalar(
            select(ORMProduct).where(
                ORMProduct.supplier_id == supplier.id,
                ORMProduct.supplier_product_id == product.provider_product_id,
            )
        )
        images = [
            {
                "key": f"supplier/{product.provider_product_id}/{idx}",
                "url": url,
                "sort": idx,
                "is_main": idx == 0,
                "alt": product.title,
            }
            for idx, url in enumerate(product.images)
        ]
        payload: dict[str, Any] = {
            "sku": product.sku or f"znd-{product.provider_product_id[:40]}",
            "name": product.title,
            "description": product.description,
            "price": product.price,
            "cost": product.price,
            "category": product.category or "dropship",
            "inventory": product.inventory,
            "status": "draft",
            "images": images,
            "supplier_id": supplier.id,
            "supplier_sku": product.sku or "",
            "supplier_product_id": product.provider_product_id,
        }
        if existing is not None:
            await ProductService.update_product(db, existing, payload)
            return existing
        return await ProductService.create_product(db, payload)

    async def sync_inventory_price(
        self,
        db: AsyncSession,
        *,
        supplier: ORMSupplier,
        credential: ORMSupplierCredential,
    ) -> SyncSummary:
        summary = SyncSummary()
        config: dict[str, object] = supplier.config if isinstance(supplier.config, dict) else {}
        auto_update_price = bool(config.get("auto_update_price", True))
        rows = (
            await db.scalars(
                select(ORMProduct).where(
                    ORMProduct.supplier_id == supplier.id,
                    ORMProduct.supplier_product_id.is_not(None),
                )
            )
        ).all()
        summary.items_total = len(rows)
        try:
            for product in rows:
                latest = await self.get_product(
                    credential=credential,
                    provider_product_id=str(product.supplier_product_id),
                )
                updates: dict[str, Any] = {"inventory": latest.inventory}
                if auto_update_price and latest.price > 0:
                    updates["cost"] = latest.price
                    updates["price"] = latest.price
                await ProductService.update_product(db, product, updates)
                summary.items_updated += 1
        except Exception as exc:  # noqa: BLE001 - 首个失败即中断并交由上层记录 partial
            logger.exception("Zendrop 增量同步失败")
            summary.error = str(exc)
            raise
        return summary


# 注册到全局注册表
from forge.suppliers.registry import register  # noqa: E402

register(ZendropProvider())
