"""Payment gateway abstraction with an in-process mock provider.

Stripe-style intent flow so the real provider can be swapped later without
changing order endpoints:

    intent = gateway.create_payment_intent(order_number, amount, currency, method)
    result = gateway.confirm(intent.id, card=card)

Environment knobs (read lazily, no settings-model coupling):

    FORGE_PAYMENT_PROVIDER  - "mock" (default) | "stripe" (reserved)
    FORGE_MOCK_PAYMENT_DECLINE - "1" forces every confirm to decline (QA helper)
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
# Domain DTOs (mirror a small subset of Stripe objects)
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


class PaymentGateway(ABC):
    """Provider-agnostic gateway contract."""

    @abstractmethod
    async def create_payment_intent(
        self,
        reference: str,
        amount: Decimal,
        currency: str,
        method: str,
    ) -> PaymentIntent: ...

    @abstractmethod
    async def confirm(self, intent_id: str, card: dict[str, Any] | None = None) -> PaymentResult: ...


# ---------------------------------------------------------------------------
# Mock provider (test-cards: 4242... success, 4000 0000 0000 0002 decline)
# ---------------------------------------------------------------------------

_SUPPORTED_METHODS = {"card", "paypal"}
_SUCCESS_CARDS = {"4242424242424242"}
_DECLINE_CARDS = {"4000000000000002"}


class MockPaymentGateway(PaymentGateway):
    """Deterministic in-process gateway for development & e2e verification.

    - Always approves supported methods unless the card number is a known
      decline card or FORGE_MOCK_PAYMENT_DECLINE=1 is set.
    - Persists nothing; confirms are idempotent by intent id in-memory only.
    """

    def __init__(self) -> None:
        self._confirmed: set[str] = set()

    @staticmethod
    def _force_decline() -> bool:
        return os.getenv("FORGE_MOCK_PAYMENT_DECLINE", "") == "1"

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
        if intent_id in self._confirmed:
            # Idempotent replay returns success (Stripe-like behavior).
            return PaymentResult(success=True, intent_id=intent_id, transaction_id=f"txn_mock_{intent_id[-8:]}")
        card_number = str((card or {}).get("number") or "").replace(" ", "").replace("-", "")
        if self._force_decline() or (card_number and card_number in _DECLINE_CARDS):
            return PaymentResult(
                success=False,
                intent_id=intent_id,
                error_code="PAYMENT_DECLINED",
                error_message="Your card was declined.",
            )
        if card_number and card_number not in _SUCCESS_CARDS and len(card_number) >= 13:
            # Unknown test numbers behave like a generic decline unless they
            # look like the classic Visa success card.
            return PaymentResult(
                success=False,
                intent_id=intent_id,
                error_code="PAYMENT_DECLINED",
                error_message="Your card was declined.",
            )
        self._confirmed.add(intent_id)
        return PaymentResult(
            success=True,
            intent_id=intent_id,
            transaction_id=f"txn_mock_{secrets.token_hex(8)}",
        )


_gateway: PaymentGateway | None = None


def get_payment_gateway() -> PaymentGateway:
    """Return configured gateway singleton (provider resolved from env)."""
    global _gateway
    if _gateway is None:
        provider = os.getenv("FORGE_PAYMENT_PROVIDER", "mock").lower()
        if provider == "mock":
            _gateway = MockPaymentGateway()
        else:
            raise APIError(
                ErrorCode.PAYMENT_GATEWAY_ERROR,
                message=f"Payment provider '{provider}' is not configured.",
            )
    return _gateway
