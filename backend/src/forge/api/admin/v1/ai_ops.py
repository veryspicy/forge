"""Admin — AI 客服运维（额度用量 / 会话巡检 / 转人工工单）。

路由前缀由 admin 聚合器挂载为 ``/api/admin/v1/ai-ops``。

- ``GET  /usage``                 各供应商当日额度与健康度（含可用性判定）
- ``GET  /usage/trend``           近 N 天用量曲线（额度治理复盘）
- ``GET  /conversations``         最近会话巡检（定位答非所问 / 降级会话）
- ``GET  /handoffs``              转人工工单列表（默认 pending）
- ``POST /handoffs/{id}/resolve`` 标记工单已处理
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from forge.application.services import llm_router
from forge.infrastructure.persistence.repositories.ai_chat_repo import (
    SQLAlchemyAIChatRepository,
    business_day,
)
from forge.main.dependencies import get_db
from forge.main.rbac import require_permission

router = APIRouter()


class ResolveHandoffPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    status: str = Field(default="resolved", pattern="^(resolved|ignored)$")
    note: str | None = Field(default=None, max_length=1000)


def _operator(admin: dict[str, Any]) -> str:
    for key in ("email", "username", "sub"):
        value = admin.get(key)
        if value:
            return str(value)
    return "admin"


@router.get("/usage")
async def ai_usage_overview(
    db: AsyncSession = Depends(get_db),
    admin: dict[str, Any] = Depends(require_permission("ai_config", "view")),  # noqa: B008
) -> dict[str, Any]:
    """供应商额度总览：谁还有余额、谁被冷却、谁当日超额。"""
    overview = await llm_router.providers_usage_overview(db)
    items = overview["items"]
    totals = {
        "requests_today": sum(int(item["requests_today"]) for item in items),
        "tokens_today": sum(int(item["tokens_today"]) for item in items),
        "failures_today": sum(int(item["failures_today"]) for item in items),
        "quota_hits_today": sum(int(item["quota_hits_today"]) for item in items),
    }
    available = [item for item in items if not item["quota_exhausted"] and not item["cooling_down"]]
    return {
        "usage_date": overview["usage_date"],
        "provider_count": len(items),
        "available_count": len(available),
        "totals": totals,
        "items": items,
    }


@router.get("/usage/trend")
async def ai_usage_trend(
    days: int = Query(default=14, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    admin: dict[str, Any] = Depends(require_permission("ai_config", "view")),  # noqa: B008
) -> dict[str, Any]:
    """近 N 天用量：喂给运营看额度是否被某个供应商吃满。"""
    since = (datetime.strptime(business_day(), "%Y-%m-%d") - timedelta(days=days - 1)).strftime("%Y-%m-%d")
    rows = await SQLAlchemyAIChatRepository.list_usage_since(db, since)
    by_day: dict[str, dict[str, int]] = {}
    for row in rows:
        bucket = by_day.setdefault(
            str(row.usage_date),
            {"requests": 0, "tokens": 0, "failures": 0, "quota_hits": 0},
        )
        bucket["requests"] += int(row.requests or 0)
        bucket["tokens"] += int(row.tokens or 0)
        bucket["failures"] += int(row.failures or 0)
        bucket["quota_hits"] += int(row.quota_hits or 0)
    series = [{"date": day, **by_day[day]} for day in sorted(by_day)]
    return {"since": since, "until": business_day(), "days": days, "series": series}


@router.get("/conversations")
async def ai_recent_conversations(
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin: dict[str, Any] = Depends(require_permission("ai_config", "view")),  # noqa: B008
) -> dict[str, Any]:
    rows = await SQLAlchemyAIChatRepository.recent_conversations(db, limit=limit)
    return {"items": [row.to_dict() for row in rows]}


@router.get("/conversations/{conversation_id}/messages")
async def ai_conversation_messages(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: dict[str, Any] = Depends(require_permission("ai_config", "view")),  # noqa: B008
) -> dict[str, Any]:
    conversation = await SQLAlchemyAIChatRepository.get_conversation(db, conversation_id)
    if conversation is None:
        return {"items": []}
    rows = await SQLAlchemyAIChatRepository.list_messages(db, conversation_id)
    return {"items": [row.to_dict() for row in rows]}


@router.get("/handoffs")
async def ai_handoffs(
    status_filter: str | None = Query(default="pending", alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    admin: dict[str, Any] = Depends(require_permission("ai_config", "view")),  # noqa: B008
) -> dict[str, Any]:
    """AI 全部供应商不可用时的转人工工单，按创建时间倒序。"""
    rows = await SQLAlchemyAIChatRepository.list_handoffs(
        db, status_filter=status_filter or None, limit=limit, offset=offset
    )
    return {"items": [row.to_dict() for row in rows], "limit": limit, "offset": offset}


@router.post("/handoffs/{handoff_id}/resolve")
async def ai_resolve_handoff(
    handoff_id: UUID,
    body: ResolveHandoffPayload,
    db: AsyncSession = Depends(get_db),
    admin: dict[str, Any] = Depends(require_permission("ai_config", "manage")),  # noqa: B008
) -> dict[str, Any]:
    handoff = await SQLAlchemyAIChatRepository.get_handoff(db, handoff_id)
    if handoff is None:
        return {"ok": False, "message": "工单不存在"}
    await SQLAlchemyAIChatRepository.resolve_handoff(
        db,
        handoff,
        handler=_operator(admin),
        note=body.note,
        new_status=body.status,
    )
    await db.commit()
    return {"ok": True, "item": handoff.to_dict()}


@router.get("/health")
async def ai_health(
    db: AsyncSession = Depends(get_db),
    admin: dict[str, Any] = Depends(require_permission("ai_config", "view")),  # noqa: B008
) -> dict[str, Any]:
    """客服可用性快检：是否至少有一个供应商能直接接流量。"""
    overview = await llm_router.providers_usage_overview(db)
    items = overview["items"]
    available = [item for item in items if not item["quota_exhausted"] and not item["cooling_down"]]
    return {
        "date": date.fromisoformat(overview["usage_date"]).isoformat(),
        "configured": len(items),
        "available": len(available),
        "degraded": not available,
        "providers": [
            {
                "provider_id": item["provider_id"],
                "provider_name": item["provider_name"],
                "quota_exhausted": item["quota_exhausted"],
                "cooling_down": item["cooling_down"],
                "last_error": item["last_error"],
            }
            for item in items
        ],
    }
