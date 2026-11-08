"""Stripe channel adapter (Checkout Session, hosted redirect flow).

Why Checkout Session instead of PaymentIntents + Stripe.js:

    - no publishable key / Stripe.js bundle required on the storefront,
    - Stripe hosts the card form, so PCI scope stays on Stripe's side,
    - Apple Pay / Google Pay / Link / local methods come for free,
    - the returned ``url`` maps 1:1 onto ``PaymentSession.redirect_url``,
      which the storefront already understands (same shape as PayPal
      approve_url redirect).

Flow:

    1. create_session -> POST /v1/checkout/sessions (mode=payment)
       returns session id (cs_...) + hosted url. The id is persisted on the
       order as payment_intent_id, channel name in payment_channel_meta.
    2. customer pays on Stripe -> Stripe calls POST /webhooks/stripe
       (checkout.session.completed) -> order marked paid.
    3. capture (fallback, used when the customer returns to the storefront
       before the webhook lands) -> GET /v1/checkout/sessions/{id} and check
       payment_status == "paid".
    4. refund -> POST /v1/refunds against the PaymentIntent id.

Amounts: Stripe uses integer minor units, and currencies in
``ZERO_DECIMAL_CURRENCIES`` have no minor unit at all (JPY 1000 is "1000",
not "100000").

Webhook verification: Stripe-Signature is a *local* HMAC-SHA256 over
"<timestamp>.<raw body>" with STRIPE_WEBHOOK_SECRET. The raw request bytes
are mandatory (re-serializing parsed JSON changes the signature), which is
why ``handle_webhook`` accepts ``raw_body``.

Env knobs (read lazily per call, no app_settings coupling):

    STRIPE_SECRET_KEY       - sk_test_... / sk_live_...
    STRIPE_WEBHOOK_SECRET   - whsec_... (endpoint signing secret)
    STRIPE_API_BASE         - optional, defaults to https://api.stripe.com
    STRIPE_WEBHOOK_TOLERANCE_SECONDS - optional, defaults to 300
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from decimal import Decimal
from typing import Any
from urllib.parse import urlencode

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

# Currencies that Stripe treats as having no minor unit (amount is the
# integer major value). Sending "amount * 100" for these is rejected.
ZERO_DECIMAL_CURRENCIES = frozenset(
    {
        "bif",
        "clp",
        "djf",
        "gnf",
        "jpy",
        "kmf",
        "krw",
        "mga",
        "pyg",
        "rwf",
        "ugx",
        "vnd",
        "vuv",
        "xaf",
        "xof",
        "xpf",
    }
)

# Stripe Checkout supports ~135 presentment currencies; we advertise the ones
# this storefront actually prices in plus common settlement currencies.
SUPPORTED_CURRENCIES = (
    "USD",
    "EUR",
    "GBP",
    "CAD",
    "AUD",
    "JPY",
    "CNY",
    "HKD",
    "SGD",
    "NZD",
    "CHF",
    "SEK",
    "NOK",
    "DKK",
    "PLN",
    "AED",
    "BRL",
    "MXN",
)

# Stripe event -> normalized event type understood by webhooks.py
_EVENT_MAP = {
    "checkout.session.completed": "payment.captured",
    "checkout.session.async_payment_succeeded": "payment.captured",
    "checkout.session.async_payment_failed": "payment.denied",
    "checkout.session.expired": "payment.denied",
    "charge.refunded": "payment.refunded",
    "charge.refund.updated": "payment.refunded",
}


def _flatten_form(prefix: str, payload: dict[str, Any], out: dict[str, str]) -> None:
    """Flatten a nested dict/list into Stripe's bracket-key form fields."""
    for key, value in payload.items():
        name = f"{prefix}[{key}]" if prefix else str(key)
        if isinstance(value, dict):
            _flatten_form(name, value, out)
        elif isinstance(value, (list, tuple)):
            for index, item in enumerate(value):
                if isinstance(item, dict):
                    _flatten_form(f"{name}[{index}]", item, out)
                else:
                    out[f"{name}[{index}]"] = str(item)
        elif isinstance(value, bool):
            out[name] = "true" if value else "false"
        elif value is not None:
            out[name] = str(value)


class StripeChannel(PaymentChannel):
    """Stripe Checkout Session adapter (hosted redirect flow)."""

    channel = "stripe"
    capabilities = ChannelCapabilities(
        flow="redirect",
        supports_refund=True,
        supported_currencies=SUPPORTED_CURRENCIES,
    )

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._secret_key = os.getenv("STRIPE_SECRET_KEY")
        self._webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
        self._base_url = (os.getenv("STRIPE_API_BASE") or "https://api.stripe.com").rstrip("/")
        # Injected only by tests (httpx.MockTransport); None keeps real networking.
        self._transport = transport

    # -- helpers ------------------------------------------------------------

    @property
    def configured(self) -> bool:
        """True when a secret key is present (used by /payment-channels probes)."""
        return bool(self._secret_key)

    def _require_credentials(self) -> None:
        if not self._secret_key:
            raise APIError(
                ErrorCode.PAYMENT_GATEWAY_ERROR,
                message="STRIPE_SECRET_KEY is not configured.",
            )

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=30, transport=self._transport)

    @staticmethod
    def _to_minor_units(amount: Decimal, currency: str) -> int:
        if currency.lower() in ZERO_DECIMAL_CURRENCIES:
            return int(amount.to_integral_value())
        return int((amount * 100).to_integral_value())

    @staticmethod
    def _encode(payload: dict[str, Any]) -> str:
        """Encode a nested payload into Stripe's bracket form encoding.

        Stripe's REST API expects ``application/x-www-form-urlencoded`` with
        bracket notation, e.g. ``line_items[0][price_data][unit_amount]=1999``.
        Pulling in the official SDK just for this would add a dependency to
        audit, so the encoding is done here.
        """
        flat: dict[str, str] = {}
        _flatten_form("", payload, flat)
        return urlencode(flat)

    def _error(self, action: str, resp: httpx.Response) -> APIError:
        detail = ""
        try:
            body = resp.json()
            err = body.get("error") or {}
            detail = str(err.get("message") or "")
        except Exception:  # noqa: BLE001 - error payload shape is not guaranteed
            detail = (resp.text or "")[:200]
        message = f"Stripe {action} failed (HTTP {resp.status_code})."
        if detail:
            message = f"{message} {detail}"
        return APIError(ErrorCode.PAYMENT_GATEWAY_ERROR, message=message)

    def _auth_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._secret_key}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

    # -- contract -----------------------------------------------------------

    async def create_session(
        self,
        reference: str,
        amount: Decimal,
        currency: str,
        **ctx: Any,
    ) -> PaymentSession:
        self._require_credentials()
        code = currency.upper()
        if code not in self.capabilities.supported_currencies:
            raise APIError(
                ErrorCode.PAYMENT_METHOD_UNSUPPORTED,
                message=f"Stripe channel does not support currency '{code}'.",
            )
        return_url = str(ctx.get("return_url") or "")
        cancel_url = str(ctx.get("cancel_url") or "")
        if not return_url:
            raise APIError(
                ErrorCode.PAYMENT_GATEWAY_ERROR,
                message="Stripe channel requires return_url.",
            )
        payload: dict[str, Any] = {
            "mode": "payment",
            "success_url": return_url,
            "cancel_url": cancel_url or return_url,
            "client_reference_id": str(reference),
            "metadata": {"order_number": str(reference)},
            "payment_intent_data": {"metadata": {"order_number": str(reference)}},
            "line_items": [
                {
                    "quantity": 1,
                    "price_data": {
                        "currency": code.lower(),
                        "unit_amount": self._to_minor_units(amount, code),
                        "product_data": {"name": f"Order {reference}"},
                    },
                }
            ],
        }
        async with self._client() as client:
            resp = await client.post(
                f"{self._base_url}/v1/checkout/sessions",
                headers=self._auth_headers(),
                content=self._encode(payload),
            )
            if resp.status_code not in (200, 201):
                raise self._error("create checkout session", resp)
            data = resp.json()
            session_id = data.get("id")
            if not session_id:
                raise APIError(ErrorCode.PAYMENT_GATEWAY_ERROR, message="Stripe session returned no id.")
            return PaymentSession(
                channel=self.channel,
                session_id=str(session_id),
                status="requires_action",
                redirect_url=data.get("url") or None,
                amount=amount,
                currency=code,
                channel_meta={
                    "stripe_status": data.get("status", ""),
                    "payment_status": data.get("payment_status", ""),
                    "checkout_url": data.get("url") or "",
                },
            )

    async def capture(self, session_id: str, **ctx: Any) -> CaptureResult:
        """Confirm by reading the session back from Stripe (webhook fallback)."""
        self._require_credentials()
        async with self._client() as client:
            resp = await client.get(
                f"{self._base_url}/v1/checkout/sessions/{session_id}",
                headers={"Authorization": f"Bearer {self._secret_key}"},
            )
            if resp.status_code != 200:
                raise self._error("retrieve checkout session", resp)
            data = resp.json()
            payment_status = str(data.get("payment_status") or "")
            if payment_status != "paid":
                return CaptureResult(
                    success=False,
                    session_id=session_id,
                    status="requires_action",
                    error_code="STRIPE_NOT_PAID",
                    error_message=f"Stripe session payment_status is '{payment_status}', expected 'paid'.",
                )
            payment_intent = data.get("payment_intent")
            return CaptureResult(
                success=True,
                session_id=session_id,
                transaction_id=str(payment_intent) if payment_intent else None,
                status="paid",
                channel_meta={
                    "stripe_session_id": session_id,
                    "payment_intent": payment_intent,
                    "amount_total": data.get("amount_total"),
                    "currency": data.get("currency"),
                },
            )

    async def refund(self, transaction_id: str, amount: Decimal, reason: str | None = None) -> RefundResult:
        self._require_credentials()
        payload: dict[str, Any] = {"payment_intent": transaction_id}
        if amount and amount > 0:
            payload["amount"] = self._to_minor_units(amount, "USD")
        if reason:
            payload["metadata"] = {"reason": reason[:200]}
        async with self._client() as client:
            resp = await client.post(
                f"{self._base_url}/v1/refunds",
                headers=self._auth_headers(),
                content=self._encode(payload),
            )
            if resp.status_code not in (200, 201):
                return RefundResult(
                    success=False,
                    transaction_id=transaction_id,
                    error_code="STRIPE_REFUND_FAILED",
                    error_message=self._error("refund", resp).message,
                )
            data = resp.json()
            return RefundResult(
                success=True,
                transaction_id=transaction_id,
                refund_id=data.get("id"),
            )

    def _verify_signature(self, headers: dict[str, Any], raw_body: bytes) -> None:
        if not self._webhook_secret:
            raise APIError(ErrorCode.PAYMENT_GATEWAY_ERROR, message="STRIPE_WEBHOOK_SECRET is not configured.")
        signature_header = ""
        for key, value in headers.items():
            if key.lower() == "stripe-signature":
                signature_header = str(value)
                break
        if not signature_header:
            raise APIError(ErrorCode.PAYMENT_GATEWAY_ERROR, message="Stripe webhook missing Stripe-Signature header.")

        timestamp = ""
        signatures: list[str] = []
        for part in signature_header.split(","):
            name, _, value = part.partition("=")
            name = name.strip()
            if name == "t":
                timestamp = value.strip()
            elif name == "v1":
                signatures.append(value.strip())
        if not timestamp or not signatures:
            raise APIError(ErrorCode.PAYMENT_GATEWAY_ERROR, message="Stripe webhook signature header is malformed.")

        tolerance = int(os.getenv("STRIPE_WEBHOOK_TOLERANCE_SECONDS", "300") or "300")
        try:
            signed_at = int(timestamp)
        except ValueError:
            raise APIError(ErrorCode.PAYMENT_GATEWAY_ERROR, message="Stripe webhook timestamp is invalid.") from None
        if tolerance > 0 and abs(int(time.time()) - signed_at) > tolerance:
            raise APIError(ErrorCode.PAYMENT_GATEWAY_ERROR, message="Stripe webhook timestamp is outside tolerance.")

        signed_payload = timestamp.encode() + b"." + raw_body
        expected = hmac.new(self._webhook_secret.encode(), signed_payload, hashlib.sha256).hexdigest()
        if not any(hmac.compare_digest(expected, candidate) for candidate in signatures):
            raise APIError(ErrorCode.PAYMENT_GATEWAY_ERROR, message="Stripe webhook signature verification failed.")

    async def handle_webhook(
        self,
        headers: dict[str, Any],
        body: dict[str, Any],
        raw_body: bytes | None = None,
    ) -> WebhookEvent:
        if raw_body is None:
            # Re-serializing parsed JSON cannot reproduce Stripe's signature.
            raise APIError(
                ErrorCode.PAYMENT_GATEWAY_ERROR,
                message="Stripe webhook requires the raw request body for signature verification.",
            )
        self._verify_signature(headers, raw_body)

        event_name = str(body.get("type") or "")
        event_type = _EVENT_MAP.get(event_name, "unknown")
        data_object = (body.get("data") or {}).get("object") or {}

        if event_name.startswith("checkout.session."):
            # For checkout events the object is the Session: its id is what we
            # stored as payment_intent_id on the order.
            session_id = str(data_object.get("id") or "")
            transaction_id = data_object.get("payment_intent")
            amount_total = data_object.get("amount_total")
            currency = data_object.get("currency")
            amount = Decimal(str(amount_total)) / 100 if amount_total is not None else None
            if event_name == "checkout.session.completed" and data_object.get("payment_status") not in {
                "paid",
                "no_payment_required",
            }:
                # Deferred payment methods settle later via async_payment_succeeded.
                event_type = "payment.pending"
        else:
            # charge.* events: the PaymentIntent id is what we stored as
            # payment_transaction_id on the order.
            transaction_id = data_object.get("payment_intent") or data_object.get("id")
            session_id = str(data_object.get("payment_intent") or "")
            amount_refunded = data_object.get("amount_refunded") or data_object.get("amount")
            currency = data_object.get("currency")
            amount = Decimal(str(amount_refunded)) / 100 if amount_refunded is not None else None

        return WebhookEvent(
            channel=self.channel,
            event_type=event_type,
            session_id=session_id or None,
            transaction_id=str(transaction_id) if transaction_id else None,
            amount=amount,
            currency=str(currency).upper() if currency else None,
            raw=body,
        )
