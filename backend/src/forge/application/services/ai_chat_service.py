"""AI 客服编排服务（C 端 chat）。

职责边界
--------
- 会话与消息落库（``ai_conversations`` / ``ai_messages``）
- 组装系统提示词：站点商品清单 + 宠物档案上下文
- 调用 ``llm_router`` 完成多供应商路由（额度 / 负载 / 故障转移）
- 全部不可用时写 ``ai_handoff_requests`` 并返回可读兜底话术
- 从回复文本与商品清单中产出 ``recommendations``（前端商品卡片）
"""

from __future__ import annotations

import logging
import re
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from forge.application.services import llm_router
from forge.infrastructure.persistence.repositories.ai_chat_repo import SQLAlchemyAIChatRepository
from forge.infrastructure.persistence.repositories.pet_repo import SQLAlchemyPetProfileRepository
from forge.infrastructure.persistence.repositories.product_repo import SQLAlchemyProductRepository

logger = logging.getLogger(__name__)

MAX_HISTORY_MESSAGES = 10
MAX_CATALOG_ITEMS = 12
MAX_RECOMMENDATIONS = 4

HANDOFF_REPLY_ZH = "抱歉，智能客服当前暂时无法应答，我已为你记录并转接人工客服，请稍后留意回复。"
HANDOFF_REPLY_EN = (
    "Sorry, our AI assistant is temporarily unavailable. "
    "I've logged your question for a human agent to follow up shortly."
)

SYSTEM_PROMPT_TEMPLATE = """你是 Forge 宠物用品商城的在线客服助手。

回答要求：
1. 使用与用户提问相同的语言回答（中文问答中文，英文问答英文）。
2. 只处理宠物养护、商品选购、下单配送、售后政策相关问题；无关请求礼貌拒绝并引导回宠物话题。
3. 严禁编造订单状态、物流单号、优惠金额、退款结果、库存数字；用户询问具体订单/物流/退款进度时，
   说明需要人工客服核实，并提示已为其记录需求。
4. 推荐商品只能从下方「可售商品清单」中选择，不得虚构商品名与价格。
5. 语气亲切专业，控制在 120 字以内，必要时用 2-4 条要点。

可售商品清单：
{catalog}

用户宠物信息：
{pet_context}
"""


def _price_text(price: Any) -> str:
    try:
        return f"${float(price):.2f}"
    except (TypeError, ValueError):
        return ""


def _first_image_url(images: Any) -> str | None:
    if not isinstance(images, list) or not images:
        return None
    first = images[0]
    if isinstance(first, dict):
        url = first.get("url")
        return str(url) if url else None
    if isinstance(first, str):
        return first
    return None


async def _catalog_snapshot(db: AsyncSession) -> list[dict[str, Any]]:
    """取可售商品（最多 12 条）用于提示词上下文与关键词推荐。"""
    page = await SQLAlchemyProductRepository.list_products(db, page=1, page_size=MAX_CATALOG_ITEMS)
    items = page.get("items") or []
    snapshot: list[dict[str, Any]] = []
    for product in items:
        snapshot.append(
            {
                "id": str(product.id),
                "name": str(product.name or ""),
                "category": str(product.category or ""),
                "price": _price_text(product.price),
                "slug": str(getattr(product, "slug", "") or ""),
                "image": _first_image_url(product.images),
                "sales": int(getattr(product, "sales", 0) or 0),
            }
        )
    return snapshot


def _catalog_text(catalog: list[dict[str, Any]]) -> str:
    if not catalog:
        return "（暂无商品数据）"
    lines = [
        f"- {item['name']}｜{item['category']}｜{item['price']}｜id={item['id']}"
        for item in catalog
        if item["name"]
    ]
    return "\n".join(lines) or "（暂无商品数据）"


def _pet_context(pet: Any) -> str:
    if pet is None:
        return "（未选择宠物档案）"
    parts = [f"名字：{getattr(pet, 'name', '') or '未填'}"]
    for field, label in (
        ("breed", "品种"),
        ("breed_custom", "品种备注"),
        ("weight", "体重(kg)"),
        ("gender", "性别"),
        ("lifecycle", "生命阶段"),
        ("allergies", "过敏源"),
        ("health_notes", "健康备注"),
    ):
        value = getattr(pet, field, None)
        if value not in (None, "", [], {}):
            parts.append(f"{label}：{value}")
    return "；".join(parts)


def _tokens(text: str) -> set[str]:
    """粗分词：英文按单词、中文按 2-gram，用于商品关键词匹配。"""
    lowered = (text or "").lower()
    words = set(re.findall(r"[a-z]{3,}", lowered))
    han = re.findall(r"[\u4e00-\u9fff]+", lowered)
    for chunk in han:
        for index in range(len(chunk) - 1):
            words.add(chunk[index : index + 2])
    return words


def pick_recommendations(
    catalog: list[dict[str, Any]],
    reply: str,
    question: str,
    limit: int = MAX_RECOMMENDATIONS,
) -> list[dict[str, Any]]:
    """按关键词命中打分挑商品：回复命中 > 提问命中 > 销量兜底。"""
    reply_tokens = _tokens(reply)
    question_tokens = _tokens(question)
    scored: list[tuple[int, int, dict[str, Any]]] = []
    for item in catalog:
        name_tokens = _tokens(item["name"])
        category_tokens = _tokens(item["category"])
        score = 0
        if name_tokens & reply_tokens:
            score += 6
        if name_tokens & question_tokens:
            score += 4
        if category_tokens & (reply_tokens | question_tokens):
            score += 2
        if not score:
            continue
        scored.append((score, item["sales"], item))
    scored.sort(key=lambda row: (-row[0], -row[1]))
    picked = [row[2] for row in scored[:limit]]
    if len(picked) < limit:
        chosen = {item["id"] for item in picked}
        for item in sorted(catalog, key=lambda entry: -entry["sales"]):
            if item["id"] in chosen:
                continue
            picked.append(item)
            chosen.add(item["id"])
            if len(picked) >= limit:
                break
    return [
        {
            "id": item["id"],
            "name": item["name"],
            "price": item["price"],
            "image": item["image"],
            "slug": item["slug"],
        }
        for item in picked
    ]


async def _resolve_pet(db: AsyncSession, pet_id: str | None, user_id: UUID | None) -> Any:
    if not pet_id or user_id is None:
        return None
    try:
        pet_uuid = UUID(str(pet_id))
    except (ValueError, TypeError):
        return None
    pet = await SQLAlchemyPetProfileRepository.get_by_id(db, pet_uuid)
    if pet is None or getattr(pet, "owner_id", None) != user_id:
        return None
    return pet


async def _resolve_conversation(
    db: AsyncSession,
    *,
    conversation_id: str | None,
    user_id: UUID | None,
    guest_key: str | None,
    pet_id: UUID | None,
) -> Any:
    if conversation_id:
        try:
            conv_uuid = UUID(str(conversation_id))
        except (ValueError, TypeError):
            conv_uuid = None
        if conv_uuid is not None:
            conversation = await SQLAlchemyAIChatRepository.get_conversation(db, conv_uuid)
            if conversation is not None:
                owner_ok = (user_id is not None and conversation.user_id == user_id) or (
                    user_id is None and guest_key and conversation.guest_key == guest_key
                )
                if owner_ok:
                    return conversation
    return await SQLAlchemyAIChatRepository.create_conversation(
        db,
        user_id=user_id,
        guest_key=guest_key,
        pet_id=pet_id,
        title="",
    )


async def chat(
    db: AsyncSession,
    *,
    message: str,
    conversation_id: str | None,
    pet_id: str | None,
    user_id: UUID | None,
    guest_key: str | None,
) -> dict[str, Any]:
    """处理一次用户提问，返回前端契约结构。"""
    text = (message or "").strip()
    if not text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="message 不能为空")
    text = text[:2000]

    pet = await _resolve_pet(db, pet_id, user_id)
    conversation = await _resolve_conversation(
        db,
        conversation_id=conversation_id,
        user_id=user_id,
        guest_key=guest_key,
        pet_id=getattr(pet, "id", None),
    )

    history = await SQLAlchemyAIChatRepository.list_messages(db, conversation.id, limit=MAX_HISTORY_MESSAGES)
    await SQLAlchemyAIChatRepository.add_message(
        db,
        conversation_id=conversation.id,
        role="user",
        content=text,
    )

    catalog = await _catalog_snapshot(db)
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        catalog=_catalog_text(catalog),
        pet_context=_pet_context(pet),
    )
    messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
    for past in history[-MAX_HISTORY_MESSAGES:]:
        if past.role in ("user", "assistant") and past.content:
            messages.append({"role": past.role, "content": past.content})
    messages.append({"role": "user", "content": text})

    result = await llm_router.route_chat(db, messages)

    if result.ok and result.content.strip():
        reply = result.content.strip()
        recommendations = pick_recommendations(catalog, reply, text)
        await SQLAlchemyAIChatRepository.add_message(
            db,
            conversation_id=conversation.id,
            role="assistant",
            content=reply,
            provider_id=result.provider_id,
            provider_name=result.provider_name,
            model=result.model,
            tokens_in=result.tokens_in,
            tokens_out=result.tokens_out,
            latency_ms=result.latency_ms,
            status="ok",
            recommendations=recommendations,
        )
        await SQLAlchemyAIChatRepository.touch_conversation(
            db,
            conversation,
            last_message=reply,
            provider_id=result.provider_id,
            add_messages=2,
            title=text[:80],
        )
        await db.commit()
        return {
            "conversation_id": str(conversation.id),
            "response": reply,
            "recommendations": recommendations,
            "status": "ok",
            "provider": {
                "id": result.provider_id,
                "name": result.provider_name,
                "upstream": result.upstream_name,
                "model": result.model,
            },
        }

    # ---- 降级：全部供应商不可用 ----
    reply = HANDOFF_REPLY_ZH if _is_cjk(text) else HANDOFF_REPLY_EN
    await SQLAlchemyAIChatRepository.add_message(
        db,
        conversation_id=conversation.id,
        role="assistant",
        content=reply,
        status="degraded",
        recommendations=[],
    )
    await SQLAlchemyAIChatRepository.touch_conversation(
        db,
        conversation,
        last_message=reply,
        provider_id=None,
        add_messages=2,
        title=text[:80],
    )
    await SQLAlchemyAIChatRepository.create_handoff(
        db,
        conversation_id=conversation.id,
        user_id=user_id,
        guest_key=guest_key,
        message=text,
        reason=result.reason or "all_failed",
        detail=result.detail or None,
    )
    await db.commit()
    logger.warning("AI 客服降级转人工: reason=%s detail=%s", result.reason, result.detail)
    return {
        "conversation_id": str(conversation.id),
        "response": reply,
        "recommendations": pick_recommendations(catalog, "", text),
        "status": "handoff",
        "reason": result.reason,
    }


def _is_cjk(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text or ""))


def new_guest_key() -> str:
    return f"guest-{uuid4().hex}"


async def list_conversations_for_owner(
    db: AsyncSession,
    *,
    user_id: UUID | None,
    guest_key: str | None,
    limit: int = 50,
) -> dict[str, Any]:
    rows = await SQLAlchemyAIChatRepository.list_conversations(
        db, user_id=user_id, guest_key=guest_key, limit=min(limit, 100)
    )
    return {"items": [row.to_dict() for row in rows]}


async def delete_conversation_for_owner(
    db: AsyncSession,
    *,
    conversation_id: str,
    user_id: UUID | None,
    guest_key: str | None,
) -> None:
    try:
        conv_uuid = UUID(str(conversation_id))
    except (ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在") from None
    conversation = await SQLAlchemyAIChatRepository.get_conversation(db, conv_uuid)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    owner_ok = (user_id is not None and conversation.user_id == user_id) or (
        user_id is None and guest_key and conversation.guest_key == guest_key
    )
    if not owner_ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    await SQLAlchemyAIChatRepository.delete_conversation(db, conv_uuid)
    await db.commit()


async def conversation_messages(
    db: AsyncSession,
    *,
    conversation_id: str,
    user_id: UUID | None,
    guest_key: str | None,
) -> dict[str, Any]:
    try:
        conv_uuid = UUID(str(conversation_id))
    except (ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在") from None
    conversation = await SQLAlchemyAIChatRepository.get_conversation(db, conv_uuid)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    owner_ok = (user_id is not None and conversation.user_id == user_id) or (
        user_id is None and guest_key and conversation.guest_key == guest_key
    )
    if not owner_ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    rows = await SQLAlchemyAIChatRepository.list_messages(db, conv_uuid)
    return {"items": [row.to_dict() for row in rows]}
