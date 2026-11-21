"""AI 客服 - SQLAlchemy Repository（会话 / 消息 / 每日额度用量 / 转人工工单）。

额度用量的累加走 Postgres ``ON CONFLICT DO UPDATE`` 原子自增，避免并发下的
读-改-写丢失更新；其余表均为常规 ORM 操作。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from forge.infrastructure.persistence.models import (
    ORMAIConversation,
    ORMAIHandoffRequest,
    ORMAIMessage,
    ORMAIUsageDaily,
)


def _now() -> datetime:
    # 表列 TIMESTAMP WITHOUT TIME ZONE，须用 naive UTC 赋值，避免 asyncpg aware/naive 混用报错
    return datetime.now(UTC).replace(tzinfo=None)


def business_day() -> str:
    """业务自然日（UTC+8）——额度归集口径与运营看到的「今天」一致。"""
    return datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")


class SQLAlchemyAIChatRepository:
    """AI 客服数据库访问封装。"""

    # ------------------------------------------------------------------ #
    # 会话
    # ------------------------------------------------------------------ #
    @staticmethod
    async def get_conversation(db: AsyncSession, conversation_id: UUID) -> ORMAIConversation | None:
        return (
            await db.execute(select(ORMAIConversation).where(ORMAIConversation.id == conversation_id))
        ).scalar_one_or_none()

    @staticmethod
    async def create_conversation(
        db: AsyncSession,
        *,
        user_id: UUID | None,
        guest_key: str | None,
        pet_id: UUID | None = None,
        title: str = "",
    ) -> ORMAIConversation:
        conversation = ORMAIConversation(
            user_id=user_id,
            guest_key=guest_key,
            pet_id=pet_id,
            title=(title or "")[:200],
            last_message="",
            message_count=0,
            created_at=_now(),
            updated_at=_now(),
        )
        db.add(conversation)
        await db.flush()
        return conversation

    @staticmethod
    async def touch_conversation(
        db: AsyncSession,
        conversation: ORMAIConversation,
        *,
        last_message: str,
        provider_id: str | None,
        add_messages: int = 2,
        title: str | None = None,
    ) -> None:
        conversation.last_message = (last_message or "")[:1000]  # type: ignore[assignment]
        conversation.message_count = int(conversation.message_count or 0) + add_messages  # type: ignore[assignment]
        conversation.provider_id = provider_id  # type: ignore[assignment]
        if title and not (conversation.title or ""):
            conversation.title = title[:200]  # type: ignore[assignment]
        conversation.updated_at = _now()  # type: ignore[assignment]
        await db.flush()

    @staticmethod
    async def list_conversations(
        db: AsyncSession,
        *,
        user_id: UUID | None,
        guest_key: str | None,
        limit: int = 50,
    ) -> list[ORMAIConversation]:
        stmt = select(ORMAIConversation)
        if user_id is not None:
            stmt = stmt.where(ORMAIConversation.user_id == user_id)
        elif guest_key:
            stmt = stmt.where(ORMAIConversation.guest_key == guest_key)
        else:
            return []
        stmt = stmt.order_by(ORMAIConversation.updated_at.desc()).limit(limit)
        return list((await db.execute(stmt)).scalars().all())

    @staticmethod
    async def claim_guest_conversations(db: AsyncSession, *, user_id: UUID, guest_key: str) -> int:
        """把该访客标识名下尚未归属用户的会话认领给当前登录用户。

        用户在游客态聊过的会话，登录后应延续到账号下，否则历史记录会"消失"。
        """
        result = await db.execute(
            update(ORMAIConversation)
            .where(
                ORMAIConversation.guest_key == guest_key,
                ORMAIConversation.user_id.is_(None),
            )
            .values(user_id=user_id)
        )
        return int(getattr(result, "rowcount", 0) or 0)

    @staticmethod
    async def delete_conversation(db: AsyncSession, conversation_id: UUID) -> int:
        result = await db.execute(delete(ORMAIConversation).where(ORMAIConversation.id == conversation_id))
        return int(getattr(result, "rowcount", 0) or 0)

    # ------------------------------------------------------------------ #
    # 消息
    # ------------------------------------------------------------------ #
    @staticmethod
    async def add_message(
        db: AsyncSession,
        *,
        conversation_id: UUID,
        role: str,
        content: str,
        provider_id: str | None = None,
        provider_name: str | None = None,
        model: str | None = None,
        tokens_in: int = 0,
        tokens_out: int = 0,
        latency_ms: int = 0,
        status: str = "ok",
        recommendations: list[Any] | None = None,
    ) -> ORMAIMessage:
        message = ORMAIMessage(
            conversation_id=conversation_id,
            role=role,
            content=content or "",
            provider_id=provider_id,
            provider_name=provider_name,
            model=model,
            tokens_in=int(tokens_in or 0),
            tokens_out=int(tokens_out or 0),
            latency_ms=int(latency_ms or 0),
            status=status,
            recommendations=recommendations or [],
            created_at=_now(),
        )
        db.add(message)
        await db.flush()
        return message

    @staticmethod
    async def list_messages(db: AsyncSession, conversation_id: UUID, limit: int = 100) -> list[ORMAIMessage]:
        stmt = (
            select(ORMAIMessage)
            .where(ORMAIMessage.conversation_id == conversation_id)
            .order_by(ORMAIMessage.created_at.asc())
            .limit(limit)
        )
        return list((await db.execute(stmt)).scalars().all())

    # ------------------------------------------------------------------ #
    # 额度用量
    # ------------------------------------------------------------------ #
    @staticmethod
    async def bump_usage(
        db: AsyncSession,
        *,
        provider_id: str,
        requests: int = 0,
        tokens: int = 0,
        failures: int = 0,
        quota_hits: int = 0,
        last_error: str | None = None,
    ) -> None:
        """原子累加当日用量。"""
        stmt = pg_insert(ORMAIUsageDaily).values(
            provider_id=provider_id,
            usage_date=business_day(),
            requests=requests,
            tokens=tokens,
            failures=failures,
            quota_hits=quota_hits,
            last_error=(last_error or None),
            updated_at=_now(),
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[ORMAIUsageDaily.provider_id, ORMAIUsageDaily.usage_date],
            set_={
                "requests": ORMAIUsageDaily.requests + stmt.excluded.requests,
                "tokens": ORMAIUsageDaily.tokens + stmt.excluded.tokens,
                "failures": ORMAIUsageDaily.failures + stmt.excluded.failures,
                "quota_hits": ORMAIUsageDaily.quota_hits + stmt.excluded.quota_hits,
                "last_error": stmt.excluded.last_error,
                "updated_at": _now(),
            },
        )
        await db.execute(stmt)
        await db.flush()

    @staticmethod
    async def usage_today(db: AsyncSession, provider_ids: list[str] | None = None) -> dict[str, ORMAIUsageDaily]:
        stmt = select(ORMAIUsageDaily).where(ORMAIUsageDaily.usage_date == business_day())
        if provider_ids:
            stmt = stmt.where(ORMAIUsageDaily.provider_id.in_(provider_ids))
        rows = (await db.execute(stmt)).scalars().all()
        return {str(row.provider_id): row for row in rows}

    # ------------------------------------------------------------------ #
    # 转人工工单
    # ------------------------------------------------------------------ #
    @staticmethod
    async def create_handoff(
        db: AsyncSession,
        *,
        conversation_id: UUID | None,
        user_id: UUID | None,
        guest_key: str | None,
        message: str,
        reason: str,
        detail: str | None = None,
    ) -> ORMAIHandoffRequest:
        handoff = ORMAIHandoffRequest(
            conversation_id=conversation_id,
            user_id=user_id,
            guest_key=guest_key,
            message=(message or "")[:4000],
            reason=reason,
            detail=(detail or None),
            status="pending",
            created_at=_now(),
            updated_at=_now(),
        )
        db.add(handoff)
        await db.flush()
        return handoff

    # ------------------------------------------------------------------
    # 转人工工单（Admin 运维）
    # ------------------------------------------------------------------

    @staticmethod
    async def list_handoffs(
        db: AsyncSession,
        *,
        status_filter: str | None = "pending",
        limit: int = 50,
        offset: int = 0,
    ) -> list[ORMAIHandoffRequest]:
        stmt = select(ORMAIHandoffRequest)
        if status_filter:
            stmt = stmt.where(ORMAIHandoffRequest.status == status_filter)
        stmt = stmt.order_by(ORMAIHandoffRequest.created_at.desc()).limit(min(limit, 200)).offset(offset)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_handoff(db: AsyncSession, handoff_id: UUID) -> ORMAIHandoffRequest | None:
        result = await db.execute(select(ORMAIHandoffRequest).where(ORMAIHandoffRequest.id == handoff_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def resolve_handoff(
        db: AsyncSession,
        handoff: ORMAIHandoffRequest,
        *,
        handler: str,
        note: str | None = None,
        new_status: str = "resolved",
    ) -> ORMAIHandoffRequest:
        # 模型列注解为旧式 Column[...]，直接赋值会被 mypy 判为类型不符，经 Any 视图写入
        target: Any = handoff
        target.status = new_status
        target.handled_by = handler
        target.handled_at = _now()
        if note:
            target.note = note
        await db.flush()
        return handoff

    @staticmethod
    async def list_usage_since(db: AsyncSession, since_day: str) -> list[ORMAIUsageDaily]:
        stmt = (
            select(ORMAIUsageDaily)
            .where(ORMAIUsageDaily.usage_date >= since_day)
            .order_by(ORMAIUsageDaily.usage_date.asc(), ORMAIUsageDaily.provider_id.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def recent_conversations(db: AsyncSession, limit: int = 20) -> list[ORMAIConversation]:
        stmt = select(ORMAIConversation).order_by(ORMAIConversation.updated_at.desc()).limit(min(limit, 100))
        result = await db.execute(stmt)
        return list(result.scalars().all())
