"""统一支付 Webhook 入口（多渠道适配器 P0）。

- POST /webhooks/{channel}：按渠道名路由到对应 PaymentChannel.handle_webhook
  （渠道自行完成签名验签并归一化为 WebhookEvent）。
- 已验签事件按 event_type 驱动订单状态：
    payment.captured  -> 按 session_id 定位订单并 mark_paid（幂等：已支付直接跳过）
    payment.refunded  -> 本期仅记录，不改变订单状态（退款流水接入后续迭代）
    order.approved    -> 客户端流程提示，不落库
- 重复投递天然幂等：order.payment_status == paid 时直接返回 200。
"""

from __future__ import annotations

import json
from typing import Any, cast

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from forge.application.services import payment_config_service
from forge.application.services.payment_gateway import get_payment_registry
from forge.infrastructure.persistence.models import ORMOrder
from forge.infrastructure.persistence.repositories.order_repo import SQLAlchemyCustomerOrderRepository
from forge.main.dependencies import get_db

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


async def _find_order_by_session(db: AsyncSession, session_id: str | None) -> ORMOrder | None:
    if not session_id:
        return None
    row = (
        await db.execute(select(ORMOrder).where(ORMOrder.payment_intent_id == session_id).limit(1))
    ).scalar_one_or_none()
    if row is None:
        row = (
            await db.execute(select(ORMOrder).where(ORMOrder.payment_transaction_id == session_id).limit(1))
        ).scalar_one_or_none()
    return row


@router.post("/{channel}")
async def receive_webhook(
    channel: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """渠道 webhook 统一入口：验签 -> 归一化 -> 驱动订单状态。

    原始请求体（raw bytes）必须原样传给渠道：Stripe 的 Stripe-Signature 是
    对 "<timestamp>.<raw body>" 计算的 HMAC，重新序列化 JSON 会导致验签必然失败。
    """
    # 刷新渠道运行期配置，保证 webhook 验签用的是后台最新配置的签名密钥
    await payment_config_service.refresh(db)
    payment_channel = get_payment_registry().get(channel)
    headers = dict(request.headers)
    raw_body = await request.body()
    body: dict[str, Any] = json.loads(raw_body) if raw_body else {}
    event = await payment_channel.handle_webhook(headers, body, raw_body)

    if event.event_type == "payment.captured":
        order = await _find_order_by_session(db, event.session_id)
        if order is not None and order.payment_status != "paid":
            business_method = str(order.payment_method or "card").lower()
            if business_method not in {"card", "paypal"}:
                business_method = "card"
            await SQLAlchemyCustomerOrderRepository.mark_paid(
                db,
                order,
                business_method,
                payment_intent_id=event.session_id,
                payment_transaction_id=event.transaction_id,
                payment_channel_meta={"channel": channel, "webhook": "payment.captured", "raw": event.raw},
            )
            await db.commit()
    elif event.event_type == "payment.refunded":
        # 本期仅记录（退款流水接入后续迭代）；不改变订单状态避免误判。
        order = await _find_order_by_session(db, event.transaction_id)
        if order is not None:
            order.payment_channel_meta = cast(
                Any,
                {**(order.payment_channel_meta or {}), "last_refund_webhook": event.raw},
            )
            await db.commit()

    return {"received": "true"}
