"""供应商注册表（P2-5）。

模块导入末尾触发 providers 子包注册，保证 get_provider/list_providers 立即可用；
新增厂商只需在 providers/ 下实现并调用 register()。
"""

from __future__ import annotations

from typing import Any

from forge.suppliers.base import ProviderNotFoundError, SupplierProvider

_PROVIDERS: dict[str, SupplierProvider] = {}


def register(provider: SupplierProvider) -> None:
    if not provider.provider_code:
        raise ValueError("provider_code 不能为空")
    _PROVIDERS[provider.provider_code] = provider


def get_provider(code: str) -> SupplierProvider:
    provider = _PROVIDERS.get(code)
    if provider is None:
        raise ProviderNotFoundError(f"未注册的供应商类型: {code}")
    return provider


def list_providers() -> list[dict[str, Any]]:
    return [
        {
            "provider_code": p.provider_code,
            "display_name": p.display_name,
            "auth_types": list(p.auth_types),
            "supports_scheduled_sync": p.supports_scheduled_sync,
        }
        for p in _PROVIDERS.values()
    ]
