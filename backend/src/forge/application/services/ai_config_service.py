"""AI（LLM）多供应商配置服务。

存储设计
--------
``system_configs`` 表的 ``ai.providers`` 键保存供应商集合（有序数组，数组顺序即页面排序）::

    {
      "items": [{"id": "p_xxx", "name": "NIM", "type": "api" | "aggregate", ...}],
      "active_id": "p_xxx" | None,
      "enabled": true
    }

密钥（供应商自身 + 聚合供应商各上游端点）以 Fernet 密文 JSON 映射整体存放在同一行的
``secret_value`` 列，映射键为 ``<provider_id>`` 与 ``<provider_id>#<upstream_id>``；
读取时解密，对外仅回显脱敏串，明文永不落库、永不回显。

历史单供应商配置 ``ai.llm`` 仅作只读迁移来源：``ai.providers`` 不存在而 ``ai.llm``
存在时，自动迁移为一条「默认供应商」，旧键保留不删。

DB 无任何记录时回退环境变量（``AI_LLM_*``），保证首装可用。
"""

from __future__ import annotations

import copy
import json
import logging
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from forge.infrastructure.persistence.models import ORMSystemConfig
from forge.infrastructure.services.crypto_service import decrypt_str, encrypt_str, mask_secret
from forge.infrastructure.services.llm_client import LLMConfig, test_endpoints
from forge.main.config import settings

logger = logging.getLogger(__name__)

AI_PROVIDERS_KEY = "ai.providers"
LEGACY_AI_CONFIG_KEY = "ai.llm"

PROVIDER_TYPE_API = "api"
PROVIDER_TYPE_AGGREGATE = "aggregate"
PROVIDER_TYPES = (PROVIDER_TYPE_API, PROVIDER_TYPE_AGGREGATE)

PROTOCOL_CHAT = "chat"
PROTOCOL_RESPONSES = "responses"
PROTOCOLS = (PROTOCOL_CHAT, PROTOCOL_RESPONSES)

MAX_PROVIDERS = 20
MAX_UPSTREAMS = 20
MAX_MODELS = 200

_IMPORT_URL_FIELDS = ("base_url", "baseUrl", "baseURL", "baseurl", "api_base", "api_url", "endpoint", "url", "host")
_IMPORT_KEY_FIELDS = ("api_key", "apiKey", "apikey", "access_token", "accessToken", "token", "key", "secret")
_IMPORT_MODEL_FIELDS = ("model", "default_model", "defaultModel", "model_id", "modelId")
_IMPORT_NAME_FIELDS = ("name", "label", "title", "provider_name", "providerName", "provider", "id")


def _now() -> str:
    """统一时间戳（naive UTC ISO 字符串，与库内其它时间字段口径一致）。"""
    return datetime.now(UTC).replace(tzinfo=None).isoformat(timespec="seconds")


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _as_float(value: Any, default: float) -> float:
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


# --------------------------------------------------------------------------- #
# 密钥（secret_value 密文 JSON 映射）
# --------------------------------------------------------------------------- #


def _read_secrets(row: ORMSystemConfig | None) -> dict[str, str]:
    """解密并解析密钥映射；密文为空、解密失败或非 JSON（历史遗留）时返回空映射。"""
    if row is None:
        return {}
    plain = decrypt_str(row.secret_value)  # type: ignore[arg-type]
    if not plain:
        return {}
    try:
        data = json.loads(plain)
    except ValueError:
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(key): str(value) for key, value in data.items() if str(value)}


def _dump_secrets(secrets: dict[str, str]) -> str | None:
    """密钥映射整体加密；全空时返回 None（is_secret=False）。"""
    cleaned = {str(key): str(value) for key, value in secrets.items() if str(value)}
    if not cleaned:
        return None
    return encrypt_str(json.dumps(cleaned, ensure_ascii=False, sort_keys=True))


def _drop_provider_secrets(secrets: dict[str, str], provider_id: str) -> None:
    secrets.pop(provider_id, None)
    for key in [k for k in secrets if k.startswith(f"{provider_id}#")]:
        secrets.pop(key, None)


# --------------------------------------------------------------------------- #
# 供应商字段归一化
# --------------------------------------------------------------------------- #


def _clean_models(raw: Any) -> list[dict[str, Any]]:
    """模型列表归一化：``[{id, context_window, capabilities}]``，去重并截断上限。"""
    if not isinstance(raw, list):
        return []
    models: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in raw:
        if isinstance(item, str):
            item = {"id": item}
        if not isinstance(item, dict):
            continue
        model_id = str(item.get("id") or "").strip()
        if not model_id or model_id in seen:
            continue
        seen.add(model_id)
        context_window = _as_int(item.get("context_window"), 0) or None
        raw_caps = item.get("capabilities")
        capabilities = [str(cap).strip() for cap in raw_caps if str(cap).strip()] if isinstance(raw_caps, list) else []
        models.append({"id": model_id, "context_window": context_window, "capabilities": capabilities})
    return models[:MAX_MODELS]


def _apply_payload(
    provider_id: str,
    payload: dict[str, Any],
    existing: dict[str, Any] | None,
    secrets: dict[str, str],
) -> dict[str, Any]:
    """把请求载荷合并到供应商字典上；``api_key`` 缺省 / 空串表示保留原密钥。

    校验失败抛 ``ValueError``（由 API 层转 400）。
    """
    base = dict(existing or {})
    now = _now()

    provider_type = str(payload.get("type") or base.get("type") or PROVIDER_TYPE_API).strip().lower()
    if provider_type not in PROVIDER_TYPES:
        raise ValueError("供应商类型仅支持 api / aggregate")

    name = str(payload.get("name") or base.get("name") or "").strip()[:100]
    if not name:
        raise ValueError("供应商名称不能为空")

    protocol = str(payload.get("protocol") or base.get("protocol") or PROTOCOL_CHAT).strip().lower()
    if protocol not in PROTOCOLS:
        raise ValueError("上游协议仅支持 chat / responses")

    base_url = str(payload.get("base_url", base.get("base_url", "")) or "").strip().rstrip("/")
    if provider_type == PROVIDER_TYPE_API:
        if not base_url:
            raise ValueError("Base URL 不能为空")
        if not base_url.startswith(("http://", "https://")):
            raise ValueError("Base URL 必须以 http:// 或 https:// 开头")

    model = str(payload.get("model", base.get("model", "")) or "").strip()
    temperature = _as_float(payload.get("temperature", base.get("temperature")), 0.7)
    max_tokens = _as_int(payload.get("max_tokens", base.get("max_tokens")), 1024)
    enabled = bool(payload.get("enabled", base.get("enabled", True)))
    raw_models = payload["models"] if "models" in payload else base.get("models")

    key = payload.get("api_key")
    if key is not None and str(key).strip():
        secrets[provider_id] = str(key).strip()

    upstreams: list[dict[str, Any]] = []
    if provider_type == PROVIDER_TYPE_AGGREGATE:
        raw_upstreams = payload["upstreams"] if "upstreams" in payload else (base.get("upstreams") or [])
        if not isinstance(raw_upstreams, list):
            raise ValueError("上游端点列表格式不正确")
        if len(raw_upstreams) > MAX_UPSTREAMS:
            raise ValueError(f"聚合供应商最多支持 {MAX_UPSTREAMS} 个上游端点")
        for raw in raw_upstreams:
            if not isinstance(raw, dict):
                continue
            upstream_url = str(raw.get("base_url") or "").strip().rstrip("/")
            if not upstream_url:
                continue
            if not upstream_url.startswith(("http://", "https://")):
                raise ValueError(f"上游端点 {upstream_url} 必须以 http:// 或 https:// 开头")
            upstream_id = str(raw.get("id") or "").strip() or _new_id("u")
            upstream_protocol = str(raw.get("protocol") or protocol).strip().lower()
            if upstream_protocol not in PROTOCOLS:
                upstream_protocol = protocol
            upstream_key = raw.get("api_key")
            if upstream_key is not None and str(upstream_key).strip():
                secrets[f"{provider_id}#{upstream_id}"] = str(upstream_key).strip()
            upstreams.append(
                {
                    "id": upstream_id,
                    "name": str(raw.get("name") or f"上游 {len(upstreams) + 1}").strip()[:60],
                    "base_url": upstream_url,
                    "protocol": upstream_protocol,
                    "model": str(raw.get("model") or model or "").strip(),
                    "enabled": bool(raw.get("enabled", True)),
                }
            )
        if not upstreams:
            raise ValueError("聚合供应商至少需要一个上游端点")
        keep = {f"{provider_id}#{item['id']}" for item in upstreams}
        for secret_key in [k for k in secrets if k.startswith(f"{provider_id}#") and k not in keep]:
            secrets.pop(secret_key, None)
    else:
        for secret_key in [k for k in secrets if k.startswith(f"{provider_id}#")]:
            secrets.pop(secret_key, None)

    return {
        "id": provider_id,
        "name": name,
        "type": provider_type,
        "enabled": enabled,
        "protocol": protocol,
        "base_url": base_url,
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "models": _clean_models(raw_models),
        "upstreams": upstreams,
        "created_at": str(base.get("created_at") or now),
        "updated_at": now,
        "last_test": base.get("last_test"),
    }


def provider_endpoint_specs(provider: dict[str, Any], secrets: dict[str, str]) -> list[tuple[str, LLMConfig]]:
    """解析供应商实际可调用的端点（label + 配置），聚合供应商按上游顺序返回。"""
    provider_id = str(provider.get("id") or "")
    protocol = str(provider.get("protocol") or PROTOCOL_CHAT)
    model = str(provider.get("model") or "")
    temperature = _as_float(provider.get("temperature"), 0.7)
    max_tokens = _as_int(provider.get("max_tokens"), 1024)

    if provider.get("type") == PROVIDER_TYPE_AGGREGATE:
        specs: list[tuple[str, LLMConfig]] = []
        for index, upstream in enumerate(provider.get("upstreams") or []):
            if not upstream.get("enabled", True):
                continue
            upstream_url = str(upstream.get("base_url") or "").strip()
            if not upstream_url:
                continue
            label = str(upstream.get("name") or f"上游 {index + 1}")
            specs.append(
                (
                    label,
                    LLMConfig(
                        base_url=upstream_url,
                        api_key=secrets.get(f"{provider_id}#{upstream.get('id')}", ""),
                        model=str(upstream.get("model") or model),
                        temperature=temperature,
                        max_tokens=max_tokens,
                        protocol=str(upstream.get("protocol") or protocol),
                    ),
                )
            )
        return specs

    return [
        (
            str(provider.get("name") or "供应商"),
            LLMConfig(
                base_url=str(provider.get("base_url") or ""),
                api_key=secrets.get(provider_id, ""),
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                protocol=protocol,
            ),
        )
    ]


def provider_endpoints(provider: dict[str, Any], secrets: dict[str, str]) -> list[LLMConfig]:
    """供应商的端点配置列表（不含 label）。"""
    return [cfg for _, cfg in provider_endpoint_specs(provider, secrets)]


# --------------------------------------------------------------------------- #
# 存储读写
# --------------------------------------------------------------------------- #


def _normalize_store(value: dict[str, Any]) -> dict[str, Any]:
    items = [item for item in (value.get("items") or []) if isinstance(item, dict) and item.get("id")]
    active_id = value.get("active_id")
    if active_id and not any(str(item.get("id")) == str(active_id) for item in items):
        active_id = None
    if not active_id and items:
        active_id = items[0]["id"]
    return {"items": items, "active_id": active_id, "enabled": bool(value.get("enabled", True))}


async def get_providers_row(db: AsyncSession) -> ORMSystemConfig | None:
    """读取多供应商配置行（不存在返回 None）。"""
    result = await db.execute(select(ORMSystemConfig).where(ORMSystemConfig.key == AI_PROVIDERS_KEY))
    return result.scalar_one_or_none()


async def _load_legacy_row(db: AsyncSession) -> ORMSystemConfig | None:
    result = await db.execute(select(ORMSystemConfig).where(ORMSystemConfig.key == LEGACY_AI_CONFIG_KEY))
    return result.scalar_one_or_none()


def _legacy_provider(legacy: ORMSystemConfig) -> tuple[dict[str, Any], dict[str, str]]:
    """历史单供应商配置 → 供应商字典 + 密钥映射。"""
    value: dict[str, Any] = dict(legacy.value or {})
    provider_id = _new_id("p")
    provider = {
        "id": provider_id,
        "name": "默认供应商",
        "type": PROVIDER_TYPE_API,
        "enabled": bool(value.get("enabled", True)),
        "protocol": PROTOCOL_CHAT,
        "base_url": str(value.get("base_url") or settings.ai_llm_base_url or "").strip().rstrip("/"),
        "model": str(value.get("model") or settings.ai_llm_model or "").strip(),
        "temperature": _as_float(value.get("temperature"), settings.ai_llm_temperature),
        "max_tokens": _as_int(value.get("max_tokens"), settings.ai_llm_max_tokens),
        "models": [],
        "upstreams": [],
        "created_at": _now(),
        "updated_at": _now(),
        "last_test": None,
    }
    secrets: dict[str, str] = {}
    legacy_key = decrypt_str(legacy.secret_value)  # type: ignore[arg-type]
    if legacy_key:
        secrets[provider_id] = legacy_key
    return provider, secrets


async def _load_store(db: AsyncSession) -> tuple[dict[str, Any], ORMSystemConfig | None]:
    """读取供应商集合；``ai.providers`` 缺失时按需从历史 ``ai.llm`` 迁移一次。"""
    row = await get_providers_row(db)
    if row is not None:
        return _normalize_store(dict(row.value or {})), row

    legacy = await _load_legacy_row(db)
    if legacy is None:
        return _normalize_store({}), None

    provider, secrets = _legacy_provider(legacy)
    if not provider["base_url"] and not secrets:
        return _normalize_store({}), None

    store: dict[str, Any] = {"items": [provider], "active_id": provider["id"], "enabled": True}
    row = await _save_store(db, store, None, secrets, updated_by=None)
    logger.info("已将历史 ai.llm 配置迁移为供应商「默认供应商」")
    return store, row


async def _save_store(
    db: AsyncSession,
    store: dict[str, Any],
    row: ORMSystemConfig | None,
    secrets: dict[str, str],
    updated_by: str | None,
) -> ORMSystemConfig:
    value = {
        "items": store.get("items") or [],
        "active_id": store.get("active_id"),
        "enabled": bool(store.get("enabled", True)),
    }
    secret_value = _dump_secrets(secrets)

    if row is None:
        row = ORMSystemConfig(
            key=AI_PROVIDERS_KEY,
            value=value,
            secret_value=secret_value,
            is_secret=bool(secret_value),
            updated_by=updated_by,
        )
        db.add(row)
    else:
        row.value = value  # type: ignore[assignment]  # 整体替换，避免 JSONB 原地变更不被追踪
        row.secret_value = secret_value  # type: ignore[assignment]
        row.is_secret = bool(secret_value)  # type: ignore[assignment]
        row.updated_by = updated_by  # type: ignore[assignment]
        row.updated_at = datetime.now(UTC).replace(tzinfo=None)  # type: ignore[assignment]

    await db.commit()
    await db.refresh(row)
    return row


def _provider_view(provider: dict[str, Any], secrets: dict[str, str]) -> dict[str, Any]:
    """对外视图：附加脱敏密钥信息，绝不回显明文。"""
    view = copy.deepcopy(provider)
    provider_id = str(provider.get("id") or "")
    view["api_key_masked"] = mask_secret(secrets.get(provider_id, ""))
    view["api_key_set"] = bool(secrets.get(provider_id))
    for upstream in view.get("upstreams") or []:
        secret_key = f"{provider_id}#{upstream.get('id')}"
        upstream["api_key_masked"] = mask_secret(secrets.get(secret_key, ""))
        upstream["api_key_set"] = bool(secrets.get(secret_key))
    return view


def _store_view(store: dict[str, Any], row: ORMSystemConfig | None, secrets: dict[str, str]) -> dict[str, Any]:
    return {
        "items": [_provider_view(item, secrets) for item in store.get("items") or []],
        "active_id": store.get("active_id"),
        "enabled": bool(store.get("enabled", True)),
        "updated_at": row.updated_at.isoformat() if row is not None and row.updated_at else None,
        "updated_by": row.updated_by if row is not None else None,
    }


def _index_of(items: list[dict[str, Any]], provider_id: str) -> int:
    for index, item in enumerate(items):
        if str(item.get("id")) == provider_id:
            return index
    raise ValueError("供应商不存在")


# --------------------------------------------------------------------------- #
# 业务操作
# --------------------------------------------------------------------------- #


async def list_providers(db: AsyncSession) -> dict[str, Any]:
    """供应商列表（含脱敏密钥信息、使用中的供应商、全局开关）。"""
    store, row = await _load_store(db)
    return _store_view(store, row, _read_secrets(row))


async def create_provider(db: AsyncSession, payload: dict[str, Any], updated_by: str | None = None) -> dict[str, Any]:
    """新增供应商；首个供应商自动置为使用中。"""
    store, row = await _load_store(db)
    secrets = _read_secrets(row)
    items = list(store["items"])
    if len(items) >= MAX_PROVIDERS:
        raise ValueError(f"供应商数量已达上限（{MAX_PROVIDERS}）")

    provider = _apply_payload(_new_id("p"), payload, None, secrets)
    items.append(provider)
    active_id = store.get("active_id") or provider["id"]
    store = {**store, "items": items, "active_id": active_id}

    row = await _save_store(db, store, row, secrets, updated_by)
    return _store_view(store, row, secrets)


async def update_provider(
    db: AsyncSession,
    provider_id: str,
    payload: dict[str, Any],
    updated_by: str | None = None,
) -> dict[str, Any]:
    """更新供应商（api_key 缺省表示保留原密钥）。"""
    store, row = await _load_store(db)
    secrets = _read_secrets(row)
    items = list(store["items"])
    index = _index_of(items, provider_id)

    items[index] = _apply_payload(provider_id, payload, items[index], secrets)
    store = {**store, "items": items}

    row = await _save_store(db, store, row, secrets, updated_by)
    return _store_view(store, row, secrets)


async def delete_provider(db: AsyncSession, provider_id: str, updated_by: str | None = None) -> dict[str, Any]:
    """删除供应商及其密钥；若删除的是使用中的供应商，自动切到剩余第一条。"""
    store, row = await _load_store(db)
    secrets = _read_secrets(row)
    items = list(store["items"])
    index = _index_of(items, provider_id)

    items.pop(index)
    _drop_provider_secrets(secrets, provider_id)
    active_id = store.get("active_id")
    if active_id == provider_id:
        active_id = items[0]["id"] if items else None
    store = {**store, "items": items, "active_id": active_id}

    row = await _save_store(db, store, row, secrets, updated_by)
    return _store_view(store, row, secrets)


async def duplicate_provider(
    db: AsyncSession,
    provider_id: str,
    name: str | None = None,
    updated_by: str | None = None,
) -> dict[str, Any]:
    """复制供应商（含密钥），副本插入到原条目之后。"""
    store, row = await _load_store(db)
    secrets = _read_secrets(row)
    items = list(store["items"])
    index = _index_of(items, provider_id)
    if len(items) >= MAX_PROVIDERS:
        raise ValueError(f"供应商数量已达上限（{MAX_PROVIDERS}）")

    source = items[index]
    clone = copy.deepcopy(source)
    new_id = _new_id("p")
    clone["id"] = new_id
    clone["name"] = (name or f"{source.get('name') or '供应商'} 副本").strip()[:100]
    clone["created_at"] = _now()
    clone["updated_at"] = _now()
    clone["last_test"] = None

    cloned_upstreams: list[dict[str, Any]] = []
    for upstream in source.get("upstreams") or []:
        cloned = copy.deepcopy(upstream)
        cloned["id"] = _new_id("u")
        cloned_upstreams.append(cloned)
        source_key = secrets.get(f"{provider_id}#{upstream.get('id')}")
        if source_key:
            secrets[f"{new_id}#{cloned['id']}"] = source_key
    clone["upstreams"] = cloned_upstreams
    source_key = secrets.get(provider_id)
    if source_key:
        secrets[new_id] = source_key

    items.insert(index + 1, clone)
    store = {**store, "items": items}

    row = await _save_store(db, store, row, secrets, updated_by)
    return _store_view(store, row, secrets)


async def activate_provider(db: AsyncSession, provider_id: str, updated_by: str | None = None) -> dict[str, Any]:
    """把指定供应商置为「使用中」。"""
    store, row = await _load_store(db)
    secrets = _read_secrets(row)
    items = list(store["items"])
    index = _index_of(items, provider_id)

    items[index] = {**items[index], "enabled": True}
    store = {**store, "items": items, "active_id": provider_id}

    row = await _save_store(db, store, row, secrets, updated_by)
    return _store_view(store, row, secrets)


async def reorder_providers(db: AsyncSession, provider_ids: list[str], updated_by: str | None = None) -> dict[str, Any]:
    """按前端拖动后的 id 顺序重排供应商。"""
    store, row = await _load_store(db)
    secrets = _read_secrets(row)
    items = list(store["items"])
    by_id = {str(item.get("id")): item for item in items}
    if sorted(by_id) != sorted({str(pid) for pid in provider_ids}):
        raise ValueError("排序列表与现有供应商不一致，请刷新后重试")

    store = {**store, "items": [by_id[str(pid)] for pid in provider_ids]}
    row = await _save_store(db, store, row, secrets, updated_by)
    return _store_view(store, row, secrets)


async def set_store_enabled(db: AsyncSession, enabled: bool, updated_by: str | None = None) -> dict[str, Any]:
    """切换「启用供应商配置」总开关。"""
    store, row = await _load_store(db)
    secrets = _read_secrets(row)
    store = {**store, "enabled": bool(enabled)}
    row = await _save_store(db, store, row, secrets, updated_by)
    return _store_view(store, row, secrets)


async def test_provider(
    db: AsyncSession,
    provider_id: str,
    payload: dict[str, Any] | None = None,
    updated_by: str | None = None,
) -> dict[str, Any]:
    """测试供应商连通性（发送 ``hi``）；支持携带未保存的草稿覆盖字段。"""
    store, row = await _load_store(db)
    secrets = _read_secrets(row)
    items = list(store["items"])
    index = _index_of(items, provider_id)
    provider = items[index]

    draft = provider
    draft_secrets = secrets
    if payload:
        draft_secrets = dict(secrets)
        draft = _apply_payload(provider_id, payload, provider, draft_secrets)

    specs = provider_endpoint_specs(draft, draft_secrets)
    if not specs:
        raise ValueError("没有可测试的上游端点")

    result = await test_endpoints([cfg for _, cfg in specs], [label for label, _ in specs])

    items[index] = {
        **provider,
        "last_test": {
            "status": result.get("status"),
            "latency_ms": result.get("latency_ms"),
            "detail": str(result.get("detail") or "")[:300],
            "at": _now(),
        },
    }
    store = {**store, "items": items}
    await _save_store(db, store, row, secrets, updated_by)
    return result


async def test_draft(payload: dict[str, Any]) -> dict[str, Any]:
    """用未保存的草稿配置做连通性测试（不落库）。"""
    secrets: dict[str, str] = {}
    data = {**payload, "name": str(payload.get("name") or "").strip() or "草稿供应商"}
    draft = _apply_payload(_new_id("p"), data, None, secrets)
    specs = provider_endpoint_specs(draft, secrets)
    if not specs:
        raise ValueError("没有可测试的上游端点")
    return await test_endpoints([cfg for _, cfg in specs], [label for label, _ in specs])


async def fetch_models(db: AsyncSession, payload: dict[str, Any]) -> dict[str, Any]:
    """拉取上游可选模型列表（草稿值优先，缺省回落到已保存的供应商配置）。"""
    provider_id = str(payload.get("provider_id") or "").strip()
    base_url = str(payload.get("base_url") or "").strip().rstrip("/")
    api_key = str(payload.get("api_key") or "").strip()

    if provider_id:
        store, row = await _load_store(db)
        secrets = _read_secrets(row)
        provider = store["items"][_index_of(store["items"], provider_id)]
        base_url = base_url or str(provider.get("base_url") or "").strip().rstrip("/")
        api_key = api_key or secrets.get(provider_id, "")

    if not base_url:
        raise ValueError("缺少 Base URL")
    if not base_url.startswith(("http://", "https://")):
        raise ValueError("Base URL 必须以 http:// 或 https:// 开头")
    if not api_key:
        raise ValueError("缺少 API Key")

    from forge.infrastructure.services.llm_client import list_models

    models = await list_models(base_url, api_key)
    return {"models": models, "count": len(models)}


# --------------------------------------------------------------------------- #
# 从第三方导入
# --------------------------------------------------------------------------- #


def _pick(entry: dict[str, Any], fields: tuple[str, ...]) -> str:
    for key in fields:
        value = entry.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _looks_like_entry(entry: dict[str, Any]) -> bool:
    return bool(_pick(entry, _IMPORT_URL_FIELDS) or _pick(entry, _IMPORT_KEY_FIELDS))


def _looks_like_key(token: str) -> bool:
    return len(token) >= 16 and re.fullmatch(r"[A-Za-z0-9._\-]+", token) is not None


def _host_label(base_url: str) -> str:
    host = base_url.split("//", 1)[-1].split("/", 1)[0].split(":")[0]
    return host or "导入的供应商"


def _entry_to_draft(entry: dict[str, Any]) -> dict[str, Any] | None:
    base_url = _pick(entry, _IMPORT_URL_FIELDS).rstrip("/")
    api_key = _pick(entry, _IMPORT_KEY_FIELDS)
    if not base_url and not api_key:
        return None
    if base_url and not base_url.startswith(("http://", "https://")):
        base_url = f"https://{base_url}"

    protocol = _pick(entry, ("protocol", "api_type", "api_mode")).lower()
    if protocol not in PROTOCOLS:
        protocol = PROTOCOL_RESPONSES if "response" in protocol else PROTOCOL_CHAT

    draft: dict[str, Any] = {
        "name": (_pick(entry, _IMPORT_NAME_FIELDS) or _host_label(base_url))[:100],
        "type": PROVIDER_TYPE_API,
        "protocol": protocol,
        "base_url": base_url,
        "model": _pick(entry, _IMPORT_MODEL_FIELDS),
        "api_key": api_key,
    }
    models = entry.get("models")
    if isinstance(models, list):
        draft["models"] = models
    if entry.get("temperature") is not None:
        draft["temperature"] = entry["temperature"]
    if entry.get("max_tokens") is not None:
        draft["max_tokens"] = entry["max_tokens"]
    return draft


def _drafts_from_json(data: Any) -> list[dict[str, Any]]:
    entries: list[Any] = []
    if isinstance(data, list):
        entries = list(data)
    elif isinstance(data, dict):
        nested = next(
            (data[key] for key in ("providers", "items", "configs") if isinstance(data.get(key), list)),
            None,
        )
        if nested is not None:
            entries = list(nested)
        elif isinstance(data.get("provider"), dict):
            entries = [data["provider"]]
        else:
            grouped = [
                (key, value) for key, value in data.items() if isinstance(value, dict) and _looks_like_entry(value)
            ]
            if grouped:
                entries = [{"name": key, **value} for key, value in grouped]
            elif _looks_like_entry(data):
                entries = [data]

    drafts: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        draft = _entry_to_draft(entry)
        if draft:
            drafts.append(draft)
    return drafts


def _split_segments(raw: str) -> list[str]:
    """多段导入内容切分：含 curl 时按 curl 起点切分，否则按行切分。"""
    text = raw.replace("\\\r\n", " ").replace("\\\n", " ")
    if re.search(r"(?:^|\s)curl\s", text, re.IGNORECASE):
        parts = re.split(r"(?=(?:^|\s)curl\s)", text, flags=re.IGNORECASE)
        return [part.strip() for part in parts if part.strip()]
    return [line.strip() for line in text.splitlines() if line.strip()]


def _draft_from_curl(segment: str) -> dict[str, Any] | None:
    if not segment.lstrip().lower().startswith("curl"):
        return None

    url_match = re.search(r"https?://[^\s'\"]+", segment)
    if not url_match:
        return None

    target = url_match.group(0).rstrip("'\"")
    protocol = PROTOCOL_RESPONSES if "/responses" in target else PROTOCOL_CHAT
    base_url = re.sub(r"/(chat/completions|completions|responses|messages|models)/?$", "", target)

    api_key = ""
    key_match = re.search(
        r"(?:authorization|x-api-key|api[-_]?key)\s*[:=]\s*(?:bearer\s+)?([A-Za-z0-9._\-]{8,})",
        segment,
        re.IGNORECASE,
    )
    if key_match:
        api_key = key_match.group(1)

    model = ""
    model_match = re.search(r"[\"']model[\"']\s*:\s*[\"']([^\"']+)[\"']", segment)
    if model_match:
        model = model_match.group(1)

    return _entry_to_draft({"base_url": base_url, "api_key": api_key, "model": model, "protocol": protocol})


def _draft_from_line(line: str) -> dict[str, Any] | None:
    if line.lower().startswith("curl"):
        return None

    tokens = [token for token in re.split(r"[,\|\s]+", line.strip()) if token]
    if not tokens:
        return None

    entry: dict[str, Any] = {}
    leftovers: list[str] = []
    for token in tokens:
        if "=" in token and not token.startswith(("http://", "https://")):
            field, _, value = token.partition("=")
            lowered = field.strip().lower()
            if lowered in {f.lower() for f in _IMPORT_URL_FIELDS}:
                entry["base_url"] = value.strip()
            elif lowered in {f.lower() for f in _IMPORT_KEY_FIELDS}:
                entry["api_key"] = value.strip()
            elif lowered in {f.lower() for f in _IMPORT_MODEL_FIELDS}:
                entry["model"] = value.strip()
            elif lowered in {f.lower() for f in _IMPORT_NAME_FIELDS}:
                entry["name"] = value.strip()
            elif lowered in ("protocol", "api_type"):
                entry["protocol"] = value.strip()
            continue
        if token.startswith(("http://", "https://")) and "base_url" not in entry:
            entry["base_url"] = token
            continue
        leftovers.append(token)

    for token in leftovers:
        if "api_key" not in entry and _looks_like_key(token):
            entry["api_key"] = token
        elif "name" not in entry:
            entry["name"] = token
        elif "model" not in entry:
            entry["model"] = token

    if not entry.get("base_url"):
        return None
    return _entry_to_draft(entry)


def parse_import_text(text: str) -> list[dict[str, Any]]:
    """解析第三方配置文本 → 供应商草稿列表。

    支持三种形态：
    1. OpenAI 兼容 JSON（单条 / 数组 / ``{"providers": [...]}`` / ``{"openai": {...}}``）
    2. cURL 命令（解析 URL、Authorization / x-api-key、body 中的 model）
    3. 纯文本行（``名称 base_url api_key model`` 或 ``base_url= k= model=``）
    """
    raw = (text or "").strip()
    if not raw:
        raise ValueError("导入内容为空")

    drafts: list[dict[str, Any]] = []
    try:
        parsed = json.loads(raw)
    except ValueError:
        parsed = None

    if parsed is not None:
        drafts = _drafts_from_json(parsed)
    else:
        for segment in _split_segments(raw):
            draft = _draft_from_curl(segment) or _draft_from_line(segment)
            if draft:
                drafts.append(draft)

    if not drafts:
        raise ValueError("未能解析出供应商配置（支持 OpenAI 兼容 JSON / cURL / 每行 base_url + api_key）")
    return drafts


async def import_providers(db: AsyncSession, text: str, updated_by: str | None = None) -> dict[str, Any]:
    """从第三方配置文本导入供应商条目（解析后可用的直接创建）。"""
    drafts = parse_import_text(text)

    store, row = await _load_store(db)
    secrets = _read_secrets(row)
    items = list(store["items"])
    created: list[str] = []
    skipped: list[str] = []

    for draft in drafts:
        if len(items) >= MAX_PROVIDERS:
            skipped.append("已达供应商数量上限")
            break
        provider_id = _new_id("p")
        try:
            provider = _apply_payload(provider_id, draft, None, secrets)
        except ValueError as exc:
            _drop_provider_secrets(secrets, provider_id)
            skipped.append(f"{draft.get('name') or '未命名'}：{exc}")
            continue
        items.append(provider)
        created.append(provider["name"])

    if not created:
        raise ValueError("；".join(skipped) or "导入失败")

    store = {**store, "items": items, "active_id": store.get("active_id") or items[0]["id"]}
    row = await _save_store(db, store, row, secrets, updated_by)
    result = _store_view(store, row, secrets)
    result["created_count"] = len(created)
    result["created_names"] = created
    result["skipped"] = skipped
    return result


# --------------------------------------------------------------------------- #
# 业务侧读取（供 AI 能力调用）
# --------------------------------------------------------------------------- #


def _env_fallback() -> LLMConfig:
    """环境变量回退配置。"""
    api_key = settings.ai_llm_api_key.strip()
    if not api_key and settings.openai_api_key and settings.openai_api_key != "sk-placeholder":
        api_key = settings.openai_api_key
    return LLMConfig(
        base_url=settings.ai_llm_base_url,
        api_key=api_key,
        model=settings.ai_llm_model,
        temperature=settings.ai_llm_temperature,
        max_tokens=settings.ai_llm_max_tokens,
        enabled=bool(api_key),
    )


async def load_llm_endpoints(db: AsyncSession) -> list[LLMConfig]:
    """读取当前生效的 LLM 端点列表（聚合供应商按上游顺序返回，供故障转移调用）。

    返回空列表表示「已配置供应商但被关闭」或无可用端点；完全未配置时回退环境变量。
    """
    store, row = await _load_store(db)
    if not bool(store.get("enabled", True)):
        return []

    active_id = store.get("active_id")
    active = next((item for item in store["items"] if str(item.get("id")) == str(active_id)), None)
    if active is not None:
        return provider_endpoints(active, _read_secrets(row))
    if store["items"]:
        return []

    fallback = _env_fallback()
    return [fallback] if fallback.base_url else []


async def load_llm_config(db: AsyncSession) -> LLMConfig:
    """读取当前生效的 LLM 配置（取使用中供应商的首个可用端点）。"""
    endpoints = await load_llm_endpoints(db)
    if not endpoints:
        return LLMConfig(enabled=False)
    return endpoints[0]
