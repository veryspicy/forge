"""统一货源 DTO（P2-5）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SupplierProduct:
    """归一化货源商品：各厂商搜索结果统一转换为该结构。"""

    provider_code: str
    provider_product_id: str
    title: str
    price: float
    inventory: int
    images: list[str] = field(default_factory=list)
    description: str = ""
    sku: str = ""
    currency: str = "USD"
    category: str = "dropship"
    variants: list[dict[str, Any]] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class SupplierSearchResult:
    items: list[SupplierProduct]
    total: int
    page: int
    page_size: int


@dataclass
class SyncSummary:
    items_total: int = 0
    items_imported: int = 0
    items_updated: int = 0
    error: str = ""
