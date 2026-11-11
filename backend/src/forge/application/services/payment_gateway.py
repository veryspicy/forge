"""Payment gateway abstraction with pluggable channel adapters.

Design: Channel Adapter model. Each payment provider (mock / paypal /
stripe / alipay / wechat ...) implements ``PaymentChannel`` with four
capabilities:

    create_session -> PaymentSession  (channel-specific launch data)
    capture        -> CaptureResult   (server-side finalize)
    refund         -> RefundResult    (optional capability)
    handle_webhook -> WebhookEvent    (verified, normalized)

Providers register into ``PaymentRegistry``; which channels are enabled for
a site is driven by the ``payment.enabled_channels`` app_settings KV (with
env fallback ``FORGE_PAYMENT_ENABLED_CHANNELS``), so multiple channels can
coexist (e.g. mock + paypal during QA).

Backward-compat: the legacy Stripe-style intent flow
(``create_payment_intent`` / ``confirm``) is preserved for the mock channel
and the existing ``POST /orders/{order_number}/pay`` endpoint, so the C-end
mock checkout keeps working untouched.

Environment knobs (read lazily, no settings-model coupling):

    FORGE_PAYMENT_PROVIDER          - "mock" (default) | "paypal" | ...
    FORGE_PAYMENT_ENABLED_CHANNELS  - comma list; falls back to provider
    PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET / PAYPAL_MODE (sandbox|live)
    FORGE_MOCK_PAYMENT_DECLINE      - "1" forces every mock capture to decline
"""

from __future__ import annotations

import os
import secrets
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from forge.api.errors import APIError, ErrorCode

# ---------------------------------------------------------------------------
# Domain DTOs (unified, channel-agnostic)
# ---------------------------------------------------------------------------


@dataclass
class ChannelCapabilities:
    """Static capability flags used by checkout UI and business rules."""

    flow: str = "redirect"  # redirect | popup | qr | client_token | mock
    supports_refund: bool = False
    supports_subscription: bool = False
    supported_currencies: tuple[str, ...] = ("USD", "EUR", "GBP")


@dataclass
class PaymentSession:
    """Launch data returned after ``create_session``.

    ``session_id`` is the channel-side reference (PayPal order id, Stripe PI
    id, Alipay trade no ...) stored on the order as payment_intent_id.
    Exactly one of approve_url / redirect_url / qr_code / client_token is
    typically populated depending on the channel flow.
    """

    channel: str
    session_id: str
    status: str  # requires_action | paid | failed
    approve_url: str | None = None
    redirect_url: str | None = None
    qr_code: str | None = None
    client_token: str | None = None
    amount: Decimal | None = None
    currency: str | None = None
    channel_meta: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class CaptureResult:
    success: bool
    session_id: str
    transaction_id: str | None = None
    status: str = "failed"  # paid | requires_action | failed
    error_code: str | None = None
    error_message: str | None = None
    channel_meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class RefundResult:
    success: bool
    transaction_id: str | None = None
    refund_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None


@dataclass
class WebhookEvent:
    """Normalized inbound webhook event after channel signature verification."""

    channel: str
    event_type: str  # payment.captured | payment.refunded | payment.denied | ...
    session_id: str | None = None
    transaction_id: str | None = None
    amount: Decimal | None = None
    currency: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Legacy DTOs (mock intent flow, kept for backward compatibility)
# ---------------------------------------------------------------------------


@dataclass
class PaymentIntent:
    id: str
    amount: int  # minor units (cents)
    currency: str
    status: str  # requires_payment_method | succeeded | requires_capture
    method: str  # card | paypal
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class PaymentResult:
    success: bool
    intent_id: str
    transaction_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None


# ---------------------------------------------------------------------------
# Channel contract
# ---------------------------------------------------------------------------


class PaymentChannel(ABC):
    """Provider-agnostic channel contract.

    A channel must implement all four methods; capability flags in
    ``capabilities`` tell the caller which optional paths are safe to use.
    """

    channel: str
    capabilities: ChannelCapabilities

    @property
    def configured(self) -> bool:
        """Whether runtime credentials are present.

        ``False`` means the channel is registered but cannot take real money
        yet; callers (e.g. /orders/payment-channels) hide it from the
        storefront instead of letting the customer hit a hard error.
        """
        return True

    @abstractmethod
    async def create_session(
        self,
        reference: str,
        amount: Decimal,
        currency: str,
        **ctx: Any,
    ) -> PaymentSession: ...

    @abstractmethod
    async def capture(self, session_id: str, **ctx: Any) -> CaptureResult: ...

    @abstractmethod
    async def refund(self, transaction_id: str, amount: Decimal, reason: str | None = None) -> RefundResult: ...

    @abstractmethod
    async def handle_webhook(
        self,
        headers: dict[str, Any],
        body: dict[str, Any],
        raw_body: bytes | None = None,
    ) -> WebhookEvent:
        """Verify + normalize an inbound webhook.

        ``raw_body`` carries the untouched request bytes; channels that sign
        the raw payload locally (Stripe) require it, API-verified channels
        (PayPal) may ignore it.
        """
        ...


# ---------------------------------------------------------------------------
# Mock channel (test-cards: 4242... success, 4000 0000 0000 0002 decline)
# ---------------------------------------------------------------------------

_SUPPORTED_METHODS = {"card", "paypal"}
_SUCCESS_CARDS = {"4242424242424242"}
_DECLINE_CARDS = {"4000000000000002"}


class MockPaymentChannel(PaymentChannel):
    """Deterministic in-process channel for development & e2e verification.

    - Implements the unified PaymentChannel contract.
    - Keeps the legacy create_payment_intent/confirm methods so the existing
      ``POST /orders/{order_number}/pay`` endpoint keeps working.
    - Confirms are idempotent by session id in-memory only.
    """

    channel = "mock"
    capabilities = ChannelCapabilities(flow="mock", supports_refund=True)

    def __init__(self) -> None:
        self._confirmed: set[str] = set()

    @staticmethod
    def _force_decline() -> bool:
        return os.getenv("FORGE_MOCK_PAYMENT_DECLINE", "") == "1"

    # -- unified contract ---------------------------------------------------

    async def create_session(
        self,
        reference: str,
        amount: Decimal,
        currency: str,
        **ctx: Any,
    ) -> PaymentSession:
        method = str(ctx.get("method") or "card").lower()
        if method not in _SUPPORTED_METHODS:
            raise APIError(
                ErrorCode.PAYMENT_METHOD_UNSUPPORTED,
                message=f"Payment method '{method}' is not supported.",
            )
        session_id = f"pi_mock_{secrets.token_hex(8)}"
        return PaymentSession(
            channel=self.channel,
            session_id=session_id,
            status="requires_action",
            amount=amount,
            currency=currency.upper(),
            channel_meta={"method": method},
        )

    async def capture(self, session_id: str, **ctx: Any) -> CaptureResult:
        if session_id in self._confirmed:
            # Idempotent replay returns success (Stripe-like behavior).
            return CaptureResult(
                success=True,
                session_id=session_id,
                transaction_id=f"txn_mock_{session_id[-8:]}",
                status="paid",
            )
        card_number = str((ctx.get("card") or {}).get("number") or "").replace(" ", "").replace("-", "")
        if self._force_decline() or (card_number and card_number in _DECLINE_CARDS):
            return CaptureResult(
                success=False,
                session_id=session_id,
                error_code="PAYMENT_DECLINED",
                error_message="Your card was declined.",
                status="failed",
            )
        if card_number and card_number not in _SUCCESS_CARDS and len(card_number) >= 13:
            # Unknown test numbers behave like a generic decline unless they
            # look like the classic Visa success card.
            return CaptureResult(
                success=False,
                session_id=session_id,
                error_code="PAYMENT_DECLINED",
                error_message="Your card was declined.",
                status="failed",
            )
        self._confirmed.add(session_id)
        return CaptureResult(
            success=True,
            session_id=session_id,
            transaction_id=f"txn_mock_{secrets.token_hex(8)}",
            status="paid",
        )

    async def refund(self, transaction_id: str, amount: Decimal, reason: str | None = None) -> RefundResult:
        return RefundResult(success=True, transaction_id=transaction_id, refund_id=f"ref_mock_{secrets.token_hex(8)}")

    async def handle_webhook(
        self,
        headers: dict[str, Any],
        body: dict[str, Any],
        raw_body: bytes | None = None,
    ) -> WebhookEvent:
        # Mock channels have no inbound webhooks.
        raise APIError(ErrorCode.PAYMENT_GATEWAY_ERROR, message="Mock channel does not accept webhooks.")

    # -- legacy intent flow (backward compatibility) ------------------------

    async def create_payment_intent(
        self,
        reference: str,
        amount: Decimal,
        currency: str,
        method: str,
    ) -> PaymentIntent:
        if method not in _SUPPORTED_METHODS:
            raise APIError(
                ErrorCode.PAYMENT_METHOD_UNSUPPORTED,
                message=f"Payment method '{method}' is not supported.",
            )
        return PaymentIntent(
            id=f"pi_mock_{secrets.token_hex(8)}",
            amount=int((amount * 100).to_integral_value()),
            currency=currency.upper(),
            status="requires_payment_method",
            method=method,
        )

    async def confirm(self, intent_id: str, card: dict[str, Any] | None = None) -> PaymentResult:
        return await self._confirm_legacy(intent_id, card)

    async def _confirm_legacy(self, intent_id: str, card: dict[str, Any] | None = None) -> PaymentResult:
        result = await self.capture(intent_id, card=card or {})
        return PaymentResult(
            success=result.success,
            intent_id=intent_id,
            transaction_id=result.transaction_id,
            error_code=result.error_code,
            error_message=result.error_message,
        )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class PaymentRegistry:
    """In-process channel registry.

    Channels register by class at import time; ``get`` raises for unknown
    channels. Which channels are *enabled* for a site is a business decision
    (app_settings ``payment.enabled_channels``), not a registry concern.
    """

    def __init__(self) -> None:
        self._channels: dict[str, PaymentChannel] = {}

    def register(self, channel: PaymentChannel) -> None:
        self._channels[channel.channel] = channel

    def get(self, channel_name: str) -> PaymentChannel:
        key = channel_name.lower()
        channel = self._channels.get(key)
        if channel is None:
            raise APIError(
                ErrorCode.PAYMENT_GATEWAY_ERROR,
                message=f"Payment channel '{channel_name}' is not registered.",
            )
        return channel

    def available(self) -> list[str]:
        return sorted(self._channels)

    def is_registered(self, channel_name: str) -> bool:
        return channel_name.lower() in self._channels


_registry: PaymentRegistry | None = None


def get_payment_registry() -> PaymentRegistry:
    """Return the process-wide channel registry (populated on first use)."""
    global _registry
    if _registry is None:
        _registry = PaymentRegistry()
        _registry.register(MockPaymentChannel())
        # Real-world channels register via lazy import; constructing a channel
        # is side-effect free (credentials are read lazily per call).
        from forge.application.services.payment_channels import PayPalChannel
        from forge.application.services.payment_stripe import StripeChannel

        _registry.register(PayPalChannel())
        _registry.register(StripeChannel())
    return _registry


# ---------------------------------------------------------------------------
# Legacy facade
# ---------------------------------------------------------------------------

_gateway: Any | None = None


def get_payment_gateway() -> Any:
    """Backward-compatible legacy facade.

    Returns a provider object exposing the Stripe-style intent flow used by
    ``POST /orders/{order_number}/pay``. For the default ``mock`` provider it
    is the MockPaymentChannel instance itself; other providers should expose
    the same legacy methods until the orders API migrates to sessions.
    """
    global _gateway
    if _gateway is None:
        provider = os.getenv("FORGE_PAYMENT_PROVIDER", "mock").lower()
        registry = get_payment_registry()
        if provider == "mock":
            _gateway = registry.get("mock")
        elif provider in {"paypal", "stripe", "alipay", "wechat"}:
            # Defer to the unified channel registry; the channel must expose
            # legacy methods or the legacy pay endpoint will raise.
            try:
                _gateway = registry.get(provider)
            except APIError:
                raise APIError(
                    ErrorCode.PAYMENT_GATEWAY_ERROR,
                    message=f"Payment provider '{provider}' is not configured.",
                ) from None
        else:
            raise APIError(
                ErrorCode.PAYMENT_GATEWAY_ERROR,
                message=f"Payment provider '{provider}' is not configured.",
            )
    return _gateway
