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
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from forge.application.services import llm_router
from forge.infrastructure.persistence.models import ORMResource
from forge.infrastructure.persistence.repositories.ai_chat_repo import SQLAlchemyAIChatRepository
from forge.infrastructure.persistence.repositories.pet_repo import SQLAlchemyPetProfileRepository
from forge.infrastructure.persistence.repositories.product_repo import SQLAlchemyProductRepository

logger = logging.getLogger(__name__)

MAX_HISTORY_MESSAGES = 10
MAX_CATALOG_SCAN = 120
MAX_CATALOG_ITEMS = 12
MAX_RECOMMENDATIONS = 4
MIN_RECOMMEND_SCORE = 5

HANDOFF_REPLY_ZH = "抱歉，智能客服当前暂时无法应答，我已为你记录并转接人工客服，请稍后留意回复。"
HANDOFF_REPLY_EN = (
    "Sorry, our AI assistant is temporarily unavailable. "
    "I've logged your question for a human agent to follow up shortly."
)

SYSTEM_PROMPT_TEMPLATE = """你是 Forge 宠物用品商城的在线客服助手。

回答要求：
1. 使用与用户提问相同的语言回答（中文问答中文，英文问答英文）。
2. 只处理宠物养护、商品选购、下单配送、售后政策相关问题；无关请求礼貌拒绝并引导回宠物话题。
3. 严禁编造订单状态、物流单号、物流轨迹、优惠金额、退款结果、库存数字；也不得承诺具体时效与赔付
   （如"1-3 天送达""今日一定发货""破损双倍赔偿"）。用户询问具体订单/物流/退款进度、催发货、
   要时效承诺或索赔时，只能说明需要人工客服核实，并提示已为其记录需求，不得给出任何数字或时间点。
4. 只可陈述下方「可售商品清单」中明确写出的信息（商品名、价格、卖点）；清单里没有的规格、材质、
   库存、发货地、保质期一律回答需人工客服确认，不得推测或补全。
5. 推荐商品只能从下方「可售商品清单」中选择，不得虚构商品名与价格。
6. 必须尊重物种与品种：用户提到狗/犬/泰迪/金毛等犬类，只推荐犬用商品；提到猫/英短/布偶等猫类，只推荐猫用商品。
   清单中没有物种相符的商品时，明确告知"暂无完全匹配的商品"，不得用相反物种（如猫抓板给狗）或无关品类凑数，
   也不得凭空列举清单外的具体款式/品牌（如"棉绳玩具""橡胶球"），只能说明暂未匹配到并引导用户补充品种与年龄。
7. 语气亲切专业，控制在 120 字以内，必要时用 2-4 条要点。

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


def _first_image_ref(images: Any) -> tuple[str | None, str | None]:
    """取主图：返回 (直链, 资源ID)。

    商品 ``images`` 里常见两种形态：上传直链 ``url``，或仅存 ``resource_id``
    （资源中心引用），后者需回表 ``resource`` 才能拿到可下发前端的 URL。
    """
    if not isinstance(images, list) or not images:
        return None, None
    first = images[0]
    if isinstance(first, str):
        return first, None
    if isinstance(first, dict):
        url = first.get("url")
        resource_id = first.get("resource_id")
        return (str(url) if url else None), (str(resource_id) if resource_id else None)
    return None, None


async def _resource_url_map(db: AsyncSession, resource_ids: set[str]) -> dict[str, str]:
    """批量解析 resource_id → 图片 URL，避免 N+1 查询。"""
    uuids: list[UUID] = []
    for raw in resource_ids:
        try:
            uuids.append(UUID(str(raw)))
        except (TypeError, ValueError):
            continue
    if not uuids:
        return {}
    rows = (
        await db.execute(
            select(ORMResource.id, ORMResource.url).where(
                ORMResource.id.in_(uuids),
                ORMResource.deleted_at.is_(None),
            )
        )
    ).all()
    return {str(row[0]): str(row[1]) for row in rows if row[1]}


def _field(obj: Any, key: str, default: Any = None) -> Any:
    """仓储可能返回 ORM 实体或已序列化 dict，统一取值入口。"""
    value = obj.get(key, default) if isinstance(obj, dict) else getattr(obj, key, default)
    return default if value is None else value


_PLACEHOLDER_NAME = re.compile(
    r"(^|[\s\-_/])(e2e|batch\d*|no variant|seo|test|p[1-9]|gate ok|reverify)([\s\-_/]|$)",
    re.IGNORECASE,
)
_PLACEHOLDER_NAME_ZH = ("测试", "审核")

# 物种关键词：用于识别用户宠物/问句中的犬猫指向，并约束推荐不串物种
_SPECIES_KEYWORDS: dict[str, tuple[str, ...]] = {
    "dog": (
        "狗",
        "犬",
        "泰迪",
        "贵宾",
        "比熊",
        "柯基",
        "柴犬",
        "金毛",
        "拉布拉多",
        "哈士奇",
        "萨摩耶",
        "边牧",
        "牧羊犬",
        "博美",
        "雪纳瑞",
        "法斗",
        "斗牛",
        "约克夏",
        "吉娃娃",
        "dog",
        "dogs",
        "puppy",
        "poodle",
        "teddy",
        "retriever",
        "corgi",
        "husky",
        "beagle",
        "chihuahua",
        "bulldog",
        "schnauzer",
        "pomeranian",
        "canine",
    ),
    "cat": (
        "猫",
        "猫咪",
        "英短",
        "美短",
        "布偶",
        "橘猫",
        "蓝猫",
        "暹罗",
        "缅因",
        "折耳",
        "cat",
        "cats",
        "kitten",
        "kitty",
        "feline",
        "ragdoll",
        "siamese",
        "tabby",
    ),
}

# 中文诉求 -> 商品库英文关键词（类目/标签以英文为主，补齐跨语言召回）
_QUERY_SYNONYMS: dict[str, tuple[str, ...]] = {
    "玩具": ("toy", "toys", "play", "interactive", "chew"),
    "抓板": ("scratcher", "scratching", "cardboard"),
    "猫抓": ("scratcher", "scratching"),
    "狗粮": ("food", "dry", "kibble", "formula"),
    "猫粮": ("food", "dry", "kibble", "formula"),
    "主粮": ("food", "kibble"),
    "零食": ("treat", "treats", "snack", "chew"),
    "窝": ("bed", "sofa", "bolster", "crate", "mat"),
    "床": ("bed", "sofa", "bolster", "mat"),
    "垫": ("bed", "mat", "pad"),
    "牵引": ("leash", "harness", "collar", "walk"),
    "项圈": ("collar", "harness"),
    "胸背": ("harness",),
    "饮水": ("fountain", "water", "drinker"),
    "喝水": ("fountain", "water"),
    "碗": ("bowl", "feeder"),
    "喂食": ("feeder", "bowl", "automatic"),
    "洗护": ("shampoo", "grooming", "brush", "conditioner"),
    "沐浴": ("shampoo", "grooming"),
    "梳": ("brush", "grooming", "comb"),
    "猫砂": ("litter", "clumping"),
    "驱虫": ("flea", "tick", "dewormer"),
    "营养": ("supplement", "vitamin", "health"),
    "关节": ("joint", "hip", "glucosamine"),
    "磨牙": ("chew", "dental", "teething"),
    "航空箱": ("crate", "carrier"),
    "衣服": ("clothes", "apparel", "coat"),
}


def _is_placeholder(item: dict[str, Any]) -> bool:
    """过滤 E2E/测试批次等内部占位商品，避免污染 C 端推荐。"""
    name = str(item.get("name") or "").strip()
    if not name:
        return True
    if any(word in name for word in _PLACEHOLDER_NAME_ZH):
        return True
    return bool(_PLACEHOLDER_NAME.search(name))


def _declared_species(product: Any) -> list[str]:
    suitable = _field(product, "suitable_for", None)
    if isinstance(suitable, dict):
        raw = suitable.get("species")
        if isinstance(raw, str):
            return [raw.lower()] if raw else []
        if isinstance(raw, list):
            return [str(entry).lower() for entry in raw if entry]
    return []


async def _catalog_snapshot(db: AsyncSession) -> list[dict[str, Any]]:
    page = await SQLAlchemyProductRepository.list_products(db, page=1, page_size=MAX_CATALOG_SCAN)
    items = page.get("items") or []
    snapshot: list[dict[str, Any]] = []
    pending: set[str] = set()
    for product in items:
        image_url, resource_id = _first_image_ref(_field(product, "images"))
        item = {
            "id": str(_field(product, "id", "")),
            "name": str(_field(product, "name", "") or ""),
            "category": str(_field(product, "category", "") or ""),
            "price": _price_text(_field(product, "price")),
            "slug": str(_field(product, "slug", "") or ""),
            "image": image_url,
            "image_resource_id": None if image_url else resource_id,
            "sales": int(_field(product, "sales", 0) or 0),
            "species": _declared_species(product),
            "tags": [str(tag) for tag in (_field(product, "tags", None) or [])],
            "breed_groups": [str(group) for group in (_field(product, "breed_groups", None) or [])],
        }
        if _is_placeholder(item):
            continue
        if item["image_resource_id"]:
            pending.add(str(item["image_resource_id"]))
        snapshot.append(item)
    url_map = await _resource_url_map(db, pending) if pending else {}
    for item in snapshot:
        pending_id = item.pop("image_resource_id", None)
        if not item["image"] and pending_id:
            item["image"] = url_map.get(str(pending_id))
    return snapshot


def _catalog_text(catalog: list[dict[str, Any]]) -> str:
    if not catalog:
        return "（当前没有与该诉求品类/物种匹配的在售商品，请如实说明暂未匹配到，不要用其他品类凑数）"
    lines = [
        f"- {item['name']}｜{item['category']}｜{item['price']}｜id={item['id']}" for item in catalog if item["name"]
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


def _expand_query_tokens(text: str) -> set[str]:
    """在 2-gram 基础上补齐中文诉求到英文字段关键词的映射。"""
    tokens = _tokens(text)
    lowered = (text or "").lower()
    for term, synonyms in _QUERY_SYNONYMS.items():
        if term in lowered:
            tokens.update(synonyms)
    return tokens


def _detect_species(*texts: Any) -> set[str]:
    blob = " ".join(str(item) for item in texts if item).lower()
    if not blob:
        return set()
    return {species for species, keywords in _SPECIES_KEYWORDS.items() if any(word in blob for word in keywords)}


def _has_category_intent(text: str) -> bool:
    lowered = (text or "").lower()
    return any(term in lowered for term in _QUERY_SYNONYMS)


_SERVICE_INTENT_TERMS = (
    "订单",
    "物流",
    "快递",
    "发货",
    "退款",
    "退货",
    "换货",
    "售后",
    "发票",
    "支付",
    "付款",
    "优惠券",
    "优惠码",
    "催单",
)


def _is_service_intent(text: str) -> bool:
    """订单/物流/售后等履约类提问，不该顺带推送商品。"""
    lowered = (text or "").lower()
    return any(term in lowered for term in _SERVICE_INTENT_TERMS)


def _query_families(text: str) -> list[tuple[str, tuple[str, ...]]]:
    """用户提问里出现的品类诉求（中文词 + 对应商品侧关键词）。"""
    lowered = (text or "").lower()
    return [(term, synonyms) for term, synonyms in _QUERY_SYNONYMS.items() if term in lowered]


def _item_in_families(item: dict[str, Any], families: list[tuple[str, tuple[str, ...]]]) -> bool:
    """商品是否属于用户诉求的品类；只按问题品类判定，避免回复里提到的商品反向带偏。"""
    haystack = " ".join(
        [
            str(item.get("name", "")),
            str(item.get("category", "")),
            " ".join(str(tag) for tag in item.get("tags") or []),
        ]
    ).lower()
    for term, synonyms in families:
        if term in haystack:
            return True
        if any(word in haystack for word in synonyms):
            return True
    return False


def _item_species(item: dict[str, Any]) -> set[str]:
    declared = {str(entry).lower() for entry in (item.get("species") or []) if entry}
    if declared:
        return declared
    haystack = " ".join(
        [
            str(item.get("name", "")),
            str(item.get("category", "")),
            " ".join(str(tag) for tag in item.get("tags") or []),
            " ".join(str(group) for group in item.get("breed_groups") or []),
        ]
    )
    return _detect_species(haystack)


def _score_item(
    item: dict[str, Any],
    reply_tokens: set[str],
    question_tokens: set[str],
    target_species: set[str],
    families: list[tuple[str, tuple[str, ...]]] | None = None,
) -> tuple[int, list[str]]:
    """单商品打分：品类一致 + 语义重合 + 物种一致性；任一项冲突直接判零。"""
    if families and not _item_in_families(item, families):
        return 0, []
    name_tokens = _tokens(str(item.get("name", "")))
    meta_tokens = _tokens(
        " ".join(
            [
                str(item.get("category", "")),
                " ".join(str(tag) for tag in item.get("tags") or []),
                " ".join(str(group) for group in item.get("breed_groups") or []),
            ]
        )
    )
    score = 0
    hits: list[str] = []
    if name_tokens & question_tokens:
        score += 6
        hits.append("query_name")
    if name_tokens & reply_tokens:
        score += 5
        hits.append("reply_name")
    if meta_tokens & question_tokens:
        score += 4
        hits.append("meta")
    if meta_tokens & reply_tokens:
        score += 2
        hits.append("reply_meta")
    if not score:
        return 0, []
    if target_species:
        item_species = _item_species(item)
        if item_species and not (item_species & target_species):
            return 0, []
        if item_species:
            score += 4
            hits.append("species")
    return score, hits


def _confidence(score: int) -> float:
    return round(min(0.96, 0.45 + 0.06 * max(score, 0)), 2)


def _match_reason(hits: list[str], species: set[str], cjk: bool) -> str:
    if cjk:
        labels: list[str] = []
        if "species" in hits:
            preferred = "dog" if "dog" in species else "cat" if "cat" in species else ""
            labels.append({"dog": "犬用", "cat": "猫用"}.get(preferred, "适用你的宠物"))
        if hits and {"query_name", "meta"} & set(hits):
            labels.append("匹配你的需求")
        elif "reply_name" in hits or "reply_meta" in hits:
            labels.append("回复中提及")
        if "hot" in hits:
            labels = ["热销推荐"]
        return " · ".join(labels) or "相关商品"
    labels_en: list[str] = []
    if "species" in hits:
        labels_en.append("species match")
    if "hot" in hits:
        labels_en = ["popular pick"]
    elif {"query_name", "meta"} & set(hits):
        labels_en.append("matches your request")
    elif {"reply_name", "reply_meta"} & set(hits):
        labels_en.append("mentioned in reply")
    return " · ".join(labels_en) or "related item"


def rank_catalog(
    catalog: list[dict[str, Any]],
    question: str,
    target_species: set[str] | None = None,
    limit: int = MAX_CATALOG_ITEMS,
) -> list[dict[str, Any]]:
    """把与当前提问最相关的商品排到前面，供系统提示词使用。"""
    question_tokens = _expand_query_tokens(question)
    species = target_species or _detect_species(question)
    families = _query_families(question)
    scored: list[tuple[int, int, dict[str, Any]]] = []
    for item in catalog:
        score, _hits = _score_item(item, set(), question_tokens, species, families)
        scored.append((score, int(item.get("sales") or 0), item))
    scored.sort(key=lambda row: (-row[0], -row[1]))
    ranked = [row[2] for row in scored if row[0] > 0]
    if not ranked and not families and not _is_service_intent(question):
        # 用户没提品类（如「推荐点什么」）时给物种相符的热销，避免整份清单为空
        fallback: list[dict[str, Any]] = []
        for item in sorted(catalog, key=lambda entry: -int(entry.get("sales") or 0)):
            item_species = _item_species(item)
            if species and item_species and not (item_species & species):
                continue
            fallback.append(item)
            if len(fallback) >= limit:
                break
        ranked = fallback
    return ranked[:limit] if ranked else []


def pick_recommendations(
    catalog: list[dict[str, Any]],
    reply: str,
    question: str,
    limit: int = MAX_RECOMMENDATIONS,
    target_species: set[str] | None = None,
) -> list[dict[str, Any]]:
    """按「需求相关性 + 物种一致性」挑商品，宁缺勿滥，不再用销量硬凑。"""
    reply_tokens = _tokens(reply)
    question_tokens = _expand_query_tokens(question)
    species = target_species if target_species else _detect_species(question)
    families = _query_families(question)
    cjk = _is_cjk(question)

    scored: list[tuple[int, int, dict[str, Any], list[str]]] = []
    for item in catalog:
        score, hits = _score_item(item, reply_tokens, question_tokens, species, families)
        if score < MIN_RECOMMEND_SCORE:
            continue
        scored.append((score, int(item.get("sales") or 0), item, hits))
    scored.sort(key=lambda row: (-row[0], -row[1]))
    picked = scored[:limit]

    # 仅在用户没提任何品类（如“推荐点什么”）时才用热销兜底
    if not picked and not _has_category_intent(question) and not _is_service_intent(question):
        popular: list[dict[str, Any]] = []
        for item in sorted(catalog, key=lambda entry: -int(entry.get("sales") or 0)):
            item_species = _item_species(item)
            if species and item_species and not (item_species & species):
                continue
            popular.append(item)
            if len(popular) >= limit:
                break
        picked = [(MIN_RECOMMEND_SCORE, int(item.get("sales") or 0), item, ["hot"]) for item in popular]

    return [
        {
            # 前端契约字段（product_id/product_name/confidence/reason）
            "product_id": item["id"],
            "product_name": item["name"],
            "confidence": _confidence(score),
            "reason": _match_reason(hits, species, cjk),
            # 兼容旧字段
            "id": item["id"],
            "name": item["name"],
            "price": item["price"],
            "image": item.get("image"),
            "slug": item["slug"],
        }
        for score, _sales, item, hits in picked
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

    # 登录后首次发言：先接管该访客标识下的游客会话，保证历史上下文延续
    await claim_guest_conversations(db, user_id=user_id, guest_key=guest_key)
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
    pet_species = (
        _detect_species(
            getattr(pet, "breed", "") or "",
            getattr(pet, "breed_custom", "") or "",
            getattr(pet, "species", "") or "",
        )
        if pet is not None
        else set()
    )
    target_species = _detect_species(text) | pet_species
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        catalog=_catalog_text(rank_catalog(catalog, text, target_species)),
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
        recommendations = pick_recommendations(catalog, reply, text, target_species=target_species)
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
        "recommendations": pick_recommendations(catalog, "", text, target_species=target_species),
        "status": "handoff",
        "reason": result.reason,
    }


def _is_cjk(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text or ""))


def new_guest_key() -> str:
    return f"guest-{uuid4().hex}"


async def claim_guest_conversations(
    db: AsyncSession,
    *,
    user_id: UUID | None,
    guest_key: str | None,
) -> int:
    """登录用户回到同一浏览器时，接管其游客期会话，避免历史记录丢失。"""
    if user_id is None or not guest_key:
        return 0
    claimed = await SQLAlchemyAIChatRepository.claim_guest_conversations(db, user_id=user_id, guest_key=guest_key)
    if claimed:
        await db.commit()
        logger.info("认领游客会话 %s 条 → user=%s", claimed, user_id)
    return claimed


async def list_conversations_for_owner(
    db: AsyncSession,
    *,
    user_id: UUID | None,
    guest_key: str | None,
    limit: int = 50,
) -> dict[str, Any]:
    await claim_guest_conversations(db, user_id=user_id, guest_key=guest_key)
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
    owner_ok = (
        (user_id is not None and conversation.user_id == user_id)
        or (user_id is None and guest_key and conversation.guest_key == guest_key)
        or (guest_key and conversation.user_id is None and conversation.guest_key == guest_key)
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
    owner_ok = (
        (user_id is not None and conversation.user_id == user_id)
        or (user_id is None and guest_key and conversation.guest_key == guest_key)
        or (guest_key and conversation.user_id is None and conversation.guest_key == guest_key)
    )
    if not owner_ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    rows = await SQLAlchemyAIChatRepository.list_messages(db, conv_uuid)
    return {"items": [row.to_dict() for row in rows]}
