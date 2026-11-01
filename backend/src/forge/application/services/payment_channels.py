"""Real-world payment channel adapters (PayPal first).

PayPal integration follows the Orders v2 API:

    1. create_session -> POST /v2/checkout/orders (intent=CAPTURE)
       returns order id + approve link; stored as payment_intent_id.
    2. customer approves on PayPal (Smart Buttons / redirect).
    3. capture -> POST /v2/checkout/orders/{id}/capture -> COMPLETED.
    4. handle_webhook -> verify-webhook-signature API, then normalize events.

Notes:
    - Amounts are strings in major units (not minor units like Stripe).
    - Webhook verification is API-based (PayPal does not use locally
      computed HMAC): the transmission headers + webhook_id + event body are
      sent back to PayPal for verification.

Env knobs (read lazily per call, no app_settings coupling):

    PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET / PAYPAL_MODE (sandbox|live)
    PAYPAL_WEBHOOK_ID (created in the PayPal developer dashboard)
"""

from __future__ import annotations

import base64
import os
from decimal import Decimal
from typing import Any

import httpx

from forge.api.errors import APIError, ErrorCode
from forge.application.services.payment_gateway import (
    CaptureResult,
    ChannelCapabilities,
    PaymentChannel,
    PaymentSession,
    RefundResult,
    WebhookEvent,
)


class PayPalChannel(PaymentChannel):
    """Orders v2 API adapter for one-time payments (intent=CAPTURE)."""

    channel = "paypal"
    capabilities = ChannelCapabilities(
        flow="popup",
        supports_refund=True,
        supported_currencies=("USD", "EUR", "GBP", "AUD", "CAD", "JPY", "CNY"),
    )

    def __init__(self) -> None:
        self._client_id = os.getenv("PAYPAL_CLIENT_ID")
        self._client_secret = os.getenv("PAYPAL_CLIENT_SECRET")
        self._mode = (os.getenv("PAYPAL_MODE", "sandbox") or "sandbox").lower()
        self._webhook_id = os.getenv("PAYPAL_WEBHOOK_ID")
        self._base_url = "https://api-m.sandbox.paypal.com" if self._mode == "sandbox" else "https://api-m.paypal.com"

    def _require_credentials(self) -> None:
        if not self._client_id or not self._client_secret:
            raise APIError(
                ErrorCode.PAYMENT_GATEWAY_ERROR,
                message="PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET are not configured.",
            )

    async def _access_token(self, client: httpx.AsyncClient) -> str:
        self._require_credentials()
        auth = base64.b64encode(f"{self._client_id}:{self._client_secret}".encode()).decode()
        resp = await client.post(
            f"{self._base_url}/v1/oauth2/token",
            headers={"Authorization": f"Basic {auth}", "Accept": "application/json"},
            data={"grant_type": "client_credentials"},
        )
        if resp.status_code != 200:
            raise APIError(
                ErrorCode.PAYMENT_GATEWAY_ERROR,
                message=f"PayPal auth failed (HTTP {resp.status_code}).",
            )
        token = resp.json().get("access_token")
        if not token:
            raise APIError(ErrorCode.PAYMENT_GATEWAY_ERROR, message="PayPal auth returned no access_token.")
        return str(token)

    @staticmethod
    def _amount_str(amount: Decimal) -> str:
        # PayPal uses string amounts in major units, NOT minor units.
        return f"{amount:.2f}"

    async def create_session(
        self,
        reference: str,
        amount: Decimal,
        currency: str,
        **ctx: Any,
    ) -> PaymentSession:
        self._require_credentials()
        return_url = str(ctx.get("return_url") or "")
        cancel_url = str(ctx.get("cancel_url") or "")
        shipping_preference = str(ctx.get("shipping_preference") or "GET_FROM_FILE")
        async with httpx.AsyncClient(timeout=30) as client:
            token = await self._access_token(client)
            resp = await client.post(
                f"{self._base_url}/v2/checkout/orders",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={
                    "intent": "CAPTURE",
                    "purchase_units": [
                        {
                            "reference_id": str(reference),
                            "custom_id": str(reference),
                            "amount": {"currency_code": currency.upper(), "value": self._amount_str(amount)},
                        }
                    ],
                    "application_context": {
                        "return_url": return_url,
                        "cancel_url": cancel_url,
                        "shipping_preference": shipping_preference,
                        "user_action": "PAY_NOW",
                    },
                },
            )
            if resp.status_code not in (200, 201):
                raise APIError(
                    ErrorCode.PAYMENT_GATEWAY_ERROR,
                    message=f"PayPal create order failed (HTTP {resp.status_code}).",
                )
            data = resp.json()
            order_id = data.get("id")
            approve_url = next(
                (link.get("href", "") for link in data.get("links", []) if link.get("rel") == "approve"),
                "",
            )
            if not order_id:
                raise APIError(ErrorCode.PAYMENT_GATEWAY_ERROR, message="PayPal create order returned no id.")
            return PaymentSession(
                channel=self.channel,
                session_id=order_id,
                status="requires_action",
                approve_url=approve_url or None,
                amount=amount,
                currency=currency.upper(),
                channel_meta={"order_id": order_id, "status": data.get("status", "")},
            )

    async def capture(self, session_id: str, **ctx: Any) -> CaptureResult:
        self._require_credentials()
        async with httpx.AsyncClient(timeout=30) as client:
            token = await self._access_token(client)
            resp = await client.post(
                f"{self._base_url}/v2/checkout/orders/{session_id}/capture",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={},
            )
            if resp.status_code not in (200, 201):
                raise APIError(
                    ErrorCode.PAYMENT_GATEWAY_ERROR,
                    message=f"PayPal capture failed (HTTP {resp.status_code}).",
                )
            data = resp.json()
            status = data.get("status", "")
            if status != "COMPLETED":
                return CaptureResult(
                    success=False,
                    session_id=session_id,
                    status="requires_action",
                    error_code="PAYPAL_NOT_COMPLETED",
                    error_message=f"PayPal order status is {status}, expected COMPLETED.",
                )
            captures = data.get("purchase_units", [{}])[0].get("payments", {}).get("captures", [])
            capture = captures[0] if captures else {}
            capture_id = capture.get("id")
            if not capture_id:
                raise APIError(ErrorCode.PAYMENT_GATEWAY_ERROR, message="PayPal capture returned no capture id.")
            return CaptureResult(
                success=True,
                session_id=session_id,
                transaction_id=capture_id,
                status="paid",
                channel_meta={
                    "paypal_order_id": session_id,
                    "capture_status": capture.get("status", ""),
                    "capture_amount": capture.get("amount", {}),
                },
            )

    async def refund(self, transaction_id: str, amount: Decimal, reason: str | None = None) -> RefundResult:
        self._require_credentials()
        body: dict[str, Any] = {
            "amount": {"value": self._amount_str(amount), "currency_code": "USD"},
        }
        if reason:
            body["note_to_payer"] = reason
        async with httpx.AsyncClient(timeout=30) as client:
            token = await self._access_token(client)
            resp = await client.post(
                f"{self._base_url}/v2/payments/captures/{transaction_id}/refund",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json=body,
            )
            if resp.status_code not in (200, 201):
                return RefundResult(
                    success=False,
                    transaction_id=transaction_id,
                    error_code="PAYPAL_REFUND_FAILED",
                    error_message=f"PayPal refund failed (HTTP {resp.status_code}).",
                )
            data = resp.json()
            return RefundResult(
                success=True,
                transaction_id=transaction_id,
                refund_id=data.get("id"),
            )

    async def handle_webhook(self, headers: dict[str, Any], body: dict[str, Any]) -> WebhookEvent:
        """Verify PayPal webhook signature via the verify-webhook-signature API."""
        self._require_credentials()
        if not self._webhook_id:
            raise APIError(ErrorCode.PAYMENT_GATEWAY_ERROR, message="PAYPAL_WEBHOOK_ID is not configured.")
        transmission_id = str(headers.get("paypal-transmission-id") or "")
        transmission_time = str(headers.get("paypal-transmission-time") or "")
        cert_url = str(headers.get("paypal-cert-url") or "")
        auth_algo = str(headers.get("paypal-auth-algo") or "")
        transmission_sig = str(headers.get("paypal-transmission-sig") or "")
        if not (transmission_id and transmission_time and cert_url and auth_algo and transmission_sig):
            raise APIError(ErrorCode.PAYMENT_GATEWAY_ERROR, message="PayPal webhook headers are incomplete.")
        async with httpx.AsyncClient(timeout=30) as client:
            token = await self._access_token(client)
            resp = await client.post(
                f"{self._base_url}/v1/notifications/verify-webhook-signature",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={
                    "auth_algo": auth_algo,
                    "cert_url": cert_url,
                    "transmission_id": transmission_id,
                    "transmission_sig": transmission_sig,
                    "transmission_time": transmission_time,
                    "webhook_id": self._webhook_id,
                    "webhook_event": body,
                },
            )
            if resp.status_code != 200:
                raise APIError(ErrorCode.PAYMENT_GATEWAY_ERROR, message="PayPal webhook verify call failed.")
            if resp.json().get("verification_status") != "SUCCESS":
                raise APIError(ErrorCode.PAYMENT_GATEWAY_ERROR, message="PayPal webhook signature verification failed.")

        event_name = str(body.get("event_type") or "")
        resource = body.get("resource") or {}
        event_type = "unknown"
        if event_name == "CHECKOUT.ORDER.APPROVED":
            event_type = "order.approved"
        elif event_name in {"PAYMENT.CAPTURE.COMPLETED", "PAYMENT.CAPTURE.PENDING", "PAYMENT.CAPTURE.DENIED"}:
            event_type = {
                "PAYMENT.CAPTURE.COMPLETED": "payment.captured",
                "PAYMENT.CAPTURE.PENDING": "payment.pending",
                "PAYMENT.CAPTURE.DENIED": "payment.denied",
            }[event_name]
        elif event_name in {"PAYMENT.CAPTURE.REFUNDED", "PAYMENT.CAPTURE.REVERSED"}:
            event_type = "payment.refunded"
        amount_value = resource.get("amount", {}).get("value")
        related = resource.get("supplementary_data", {}).get("related_ids", {})
        session_id = str(related.get("order_id") or "") or str(resource.get("id") or "")
        return WebhookEvent(
            channel=self.channel,
            event_type=event_type,
            session_id=session_id,
            transaction_id=str(resource.get("id") or ""),
            amount=Decimal(str(amount_value)) if amount_value is not None else None,
            currency=resource.get("amount", {}).get("currency_code"),
            raw=body,
        )
