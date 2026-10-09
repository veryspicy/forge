"""Admin 模型管理（多供应商）API。

- ``GET    /api/admin/v1/ai-config/providers``                   供应商列表
- ``POST   /api/admin/v1/ai-config/providers``                   新增供应商
- ``PUT    /api/admin/v1/ai-config/providers/{provider_id}``     更新供应商
- ``DELETE /api/admin/v1/ai-config/providers/{provider_id}``     删除供应商
- ``POST   /api/admin/v1/ai-config/providers/{provider_id}/duplicate``  复制供应商
- ``POST   /api/admin/v1/ai-config/providers/{provider_id}/activate``   设为使用中
- ``POST   /api/admin/v1/ai-config/providers/reorder``           保存排序
- ``POST   /api/admin/v1/ai-config/providers/test``              连通性测试（发送 hi）
- ``POST   /api/admin/v1/ai-config/providers/models``            拉取上游模型列表
- ``POST   /api/admin/v1/ai-config/providers/import``            从第三方配置文本导入
- ``PUT    /api/admin/v1/ai-config/enabled``                     启用/关闭供应商配置

配置持久化在 ``system_configs`` 表的 ``ai.providers`` 键；API Key 以密文落库，
接口只返回脱敏串（``api_key_masked`` / ``api_key_set``）。``api_key`` 不传或留空
表示保留原密钥。
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from fastapi import APIRouter, Body, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from forge.api.errors import APIError, ErrorCode
from forge.application.services import ai_config_service
from forge.main.dependencies import get_db
from forge.main.rbac import require_permission

logger = logging.getLogger(__name__)

router = APIRouter()


class ProviderUpstreamPayload(BaseModel):
    """聚合供应商的上游端点。"""

    id: str | None = None
    name: str | None = None
    base_url: str
    protocol: str | None = None
    model: str | None = None
    api_key: str | None = None
    enabled: bool | None = True


class ProviderModelPayload(BaseModel):
    """供应商下的模型条目。"""

    id: str
    context_window: int | None = None
    capabilities: list[str] | None = None


class ProviderPayload(BaseModel):
    """供应商新增 / 更新 / 测试载荷；None 字段表示「不覆盖已保存值」。"""

    name: str | None = None
    type: str | None = None
    protocol: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    model: str | None = None
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1, le=65536)
    enabled: bool | None = None
    models: list[ProviderModelPayload] | None = None
    upstreams: list[ProviderUpstreamPayload] | None = None


class ProviderTestPayload(ProviderPayload):
    """连通性测试载荷：``provider_id`` 为空表示用草稿配置测试。"""

    provider_id: str | None = None


class DuplicatePayload(BaseModel):
    name: str | None = None


class ReorderPayload(BaseModel):
    provider_ids: list[str] = Field(min_length=1)


class EnabledPayload(BaseModel):
    enabled: bool


class ImportPayload(BaseModel):
    text: str


def _dump(payload: BaseModel | None) -> dict[str, Any] | None:
    """只透传请求体显式给出的字段，避免 None 覆盖已保存值。"""
    if payload is None:
        return None
    return payload.model_dump(exclude_unset=True, exclude_none=True)


def _updated_by(admin: dict[str, Any]) -> str | None:
    return str(admin.get("email") or admin.get("sub") or "") or None


def _error(exc: ValueError) -> APIError:
    """服务层校验异常 -> 已注册错误码（文案由前端 ``errors.<code>`` 映射）。"""
    detail = str(exc)
    if "不存在" in detail:
        return APIError(code=ErrorCode.AI_PROVIDER_NOT_FOUND)
    if "上限" in detail:
        return APIError(code=ErrorCode.AI_PROVIDER_LIMIT_REACHED)
    return APIError(code=ErrorCode.AI_PROVIDER_INVALID)


@router.get("/providers")
async def list_providers(
    admin: dict[str, Any] = Depends(require_permission("ai_config", "view")),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict[str, Any]:
    """供应商列表（密钥脱敏，含使用中供应商与全局开关）。"""
    return {"data": await ai_config_service.list_providers(db)}


@router.post("/providers")
async def create_provider(
    payload: ProviderPayload,
    admin: dict[str, Any] = Depends(require_permission("ai_config", "manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict[str, Any]:
    """新增供应商；首个供应商自动置为使用中。"""
    try:
        data = await ai_config_service.create_provider(db, _dump(payload) or {}, _updated_by(admin))
    except ValueError as exc:
        raise _error(exc) from None
    return {"data": data}


@router.post("/providers/reorder")
async def reorder_providers(
    payload: ReorderPayload,
    admin: dict[str, Any] = Depends(require_permission("ai_config", "manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict[str, Any]:
    """按拖动后的顺序保存供应商排序。"""
    try:
        data = await ai_config_service.reorder_providers(db, payload.provider_ids, _updated_by(admin))
    except ValueError as exc:
        raise _error(exc) from None
    return {"data": data}


@router.post("/providers/test")
async def test_provider(
    payload: ProviderTestPayload | None = Body(default=None),
    admin: dict[str, Any] = Depends(require_permission("ai_config", "view")),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict[str, Any]:
    """连通性测试：拉模型列表并发起一次最小对话（发送 ``hi``）。

    携带 ``provider_id`` 表示测试已保存的供应商（可附带草稿覆盖字段，结果会记录到
    该供应商的 ``last_test``）；不带 ``provider_id`` 表示用未保存的草稿临时测试。
    """
    data = _dump(payload) or {}
    provider_id = str(data.pop("provider_id", "") or "")
    try:
        if provider_id:
            result = await ai_config_service.test_provider(db, provider_id, data, _updated_by(admin))
        else:
            result = await ai_config_service.test_draft(data)
    except ValueError as exc:
        raise _error(exc) from None
    return {"data": result}


@router.post("/providers/models")
async def fetch_provider_models(
    payload: ProviderTestPayload | None = Body(default=None),
    admin: dict[str, Any] = Depends(require_permission("ai_config", "view")),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict[str, Any]:
    """拉取上游可选模型列表（``GET {base_url}/models``）。

    携带 ``provider_id`` 且未传密钥时，复用该供应商已保存的密钥。
    """
    try:
        data = await ai_config_service.fetch_models(db, _dump(payload) or {})
    except ValueError as exc:
        raise _error(exc) from None
    except httpx.HTTPStatusError as exc:
        raise APIError(
            code=ErrorCode.AI_UPSTREAM_UNREACHABLE,
            message=f"Upstream returned HTTP {exc.response.status_code}.",
        ) from None
    except httpx.HTTPError as exc:
        raise APIError(
            code=ErrorCode.AI_UPSTREAM_UNREACHABLE, message=f"Upstream error: {type(exc).__name__}."
        ) from None
    return {"data": data}


@router.post("/providers/import")
async def import_providers(
    payload: ImportPayload,
    admin: dict[str, Any] = Depends(require_permission("ai_config", "manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict[str, Any]:
    """从第三方配置文本（JSON / cURL / 文本行）导入供应商。"""
    try:
        data = await ai_config_service.import_providers(db, payload.text, _updated_by(admin))
    except ValueError as exc:
        raise _error(exc) from None
    return {"data": data}


@router.put("/enabled")
async def set_enabled(
    payload: EnabledPayload,
    admin: dict[str, Any] = Depends(require_permission("ai_config", "manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict[str, Any]:
    """启用 / 关闭供应商配置。"""
    return {"data": await ai_config_service.set_store_enabled(db, payload.enabled, _updated_by(admin))}


@router.put("/providers/{provider_id}")
async def update_provider(
    provider_id: str,
    payload: ProviderPayload,
    admin: dict[str, Any] = Depends(require_permission("ai_config", "manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict[str, Any]:
    """更新供应商（``api_key`` 不传或留空表示保留原密钥）。"""
    try:
        data = await ai_config_service.update_provider(db, provider_id, _dump(payload) or {}, _updated_by(admin))
    except ValueError as exc:
        raise _error(exc) from None
    return {"data": data}


@router.delete("/providers/{provider_id}")
async def delete_provider(
    provider_id: str,
    admin: dict[str, Any] = Depends(require_permission("ai_config", "manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict[str, Any]:
    """删除供应商及其密钥。"""
    try:
        data = await ai_config_service.delete_provider(db, provider_id, _updated_by(admin))
    except ValueError as exc:
        raise _error(exc) from None
    return {"data": data}


@router.post("/providers/{provider_id}/duplicate")
async def duplicate_provider(
    provider_id: str,
    payload: DuplicatePayload | None = Body(default=None),
    admin: dict[str, Any] = Depends(require_permission("ai_config", "manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict[str, Any]:
    """复制供应商（含密钥），副本插入到原条目之后。"""
    name = (payload.name if payload is not None else None) or None
    try:
        data = await ai_config_service.duplicate_provider(db, provider_id, name, _updated_by(admin))
    except ValueError as exc:
        raise _error(exc) from None
    return {"data": data}


@router.post("/providers/{provider_id}/activate")
async def activate_provider(
    provider_id: str,
    admin: dict[str, Any] = Depends(require_permission("ai_config", "manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict[str, Any]:
    """把指定供应商置为「使用中」。"""
    try:
        data = await ai_config_service.activate_provider(db, provider_id, _updated_by(admin))
    except ValueError as exc:
        raise _error(exc) from None
    return {"data": data}


@router.get("/providers/{provider_id}")
async def get_provider(
    provider_id: str,
    admin: dict[str, Any] = Depends(require_permission("ai_config", "view")),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict[str, Any]:
    """读取单个供应商详情（密钥脱敏）。"""
    store = await ai_config_service.list_providers(db)
    for item in store["items"]:
        if str(item.get("id")) == provider_id:
            return {"data": item}
    raise APIError(code=ErrorCode.AI_PROVIDER_NOT_FOUND)
