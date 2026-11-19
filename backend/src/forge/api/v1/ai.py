"""C 端 AI 客服 API。

前端契约（portal-web ``app/composables/useApi.ts`` / ``app/stores/chat.ts``）：

- ``POST   /api/v1/ai/chat``                body ``{message, conversation_id?, pet_id?}``
  → ``{conversation_id, response, recommendations[], status}``
- ``GET    /api/v1/ai/conversations``       → ``{items: [...]}``
- ``GET    /api/v1/ai/conversations/{id}``  → ``{items: [message, ...]}``
- ``DELETE /api/v1/ai/conversations/{id}``  → 204
- ``GET    /api/v1/ai/status``              → 供应商可用性概览（不含密钥）

认证：可选。带 ``Authorization: Bearer <token>`` 时按登录用户归并会话；
未登录时用 ``X-Guest-Key`` 头（前端首次生成后本地持久化）归并游客会话。
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Response, status
from fastapi.security import HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from forge.api.v1.auth import security_scheme
from forge.application.services import ai_chat_service, llm_router
from forge.infrastructure.persistence.models import ORMUser
from forge.infrastructure.persistence.repositories.user_repo import SQLAlchemyUserRepository
from forge.main.config import settings
from forge.main.dependencies import get_db

router = APIRouter(tags=["C-end AI Chat"])


class AIChatRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    message: str = Field(min_length=1, max_length=2000)
    conversation_id: str | None = None
    pet_id: str | None = None


async def get_optional_user(
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
) -> ORMUser | None:
    """可选登录：无 token / token 失效一律按游客处理，不阻断对话。"""
    if credentials is None:
        return None
    try:
        payload = jwt.decode(credentials.credentials, settings.secret_key, algorithms=["HS256"])
    except JWTError:
        return None
    email = str(payload.get("sub") or "").strip()
    if not email:
        return None
    return await SQLAlchemyUserRepository().get_by_email(db, email)


def _user_id(user: ORMUser | None) -> UUID | None:
    if user is None:
        return None
    raw = getattr(user, "id", None)
    if isinstance(raw, UUID):
        return raw
    try:
        return UUID(str(raw))
    except (TypeError, ValueError):
        return None


@router.post("/ai/chat")
async def ai_chat(
    body: AIChatRequest,
    db: AsyncSession = Depends(get_db),
    user: ORMUser | None = Depends(get_optional_user),
    guest_key: str | None = Header(default=None, alias="X-Guest-Key"),
) -> dict[str, Any]:
    """一次问答：额度内自动择优供应商，全部不可用时落转人工工单。"""
    return await ai_chat_service.chat(
        db,
        message=body.message,
        conversation_id=body.conversation_id,
        pet_id=body.pet_id,
        user_id=_user_id(user),
        guest_key=(guest_key or None),
    )


@router.get("/ai/conversations")
async def list_ai_conversations(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    user: ORMUser | None = Depends(get_optional_user),
    guest_key: str | None = Header(default=None, alias="X-Guest-Key"),
) -> dict[str, Any]:
    return await ai_chat_service.list_conversations_for_owner(
        db,
        user_id=_user_id(user),
        guest_key=(guest_key or None),
        limit=limit,
    )


@router.get("/ai/conversations/{conversation_id}")
async def get_ai_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    user: ORMUser | None = Depends(get_optional_user),
    guest_key: str | None = Header(default=None, alias="X-Guest-Key"),
) -> dict[str, Any]:
    return await ai_chat_service.conversation_messages(
        db,
        conversation_id=conversation_id,
        user_id=_user_id(user),
        guest_key=(guest_key or None),
    )


@router.delete("/ai/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ai_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    user: ORMUser | None = Depends(get_optional_user),
    guest_key: str | None = Header(default=None, alias="X-Guest-Key"),
) -> Response:
    await ai_chat_service.delete_conversation_for_owner(
        db,
        conversation_id=conversation_id,
        user_id=_user_id(user),
        guest_key=(guest_key or None),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/ai/status")
async def ai_status(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """客服助手可用性概览：不暴露密钥与上游地址，只给运营/前端探活。"""
    overview = await llm_router.providers_usage_overview(db)
    available = [item for item in overview["items"] if not item["quota_exhausted"] and not item["cooling_down"]]
    return {
        "available": bool(available),
        "usage_date": overview["usage_date"],
        "providers": [
            {
                "name": item["provider_name"],
                "quota_exhausted": item["quota_exhausted"],
                "cooling_down": item["cooling_down"],
            }
            for item in overview["items"]
        ],
    }
