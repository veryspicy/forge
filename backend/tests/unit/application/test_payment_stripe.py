"""Stripe channel adapter unit tests (no network: httpx.MockTransport)."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from decimal import Decimal
from typing import Any

import httpx
import pytest

from forge.api.errors import APIError
from forge.application.services.payment_stripe import StripeChannel

WEBHOOK_SECRET = "whsec_test_secret"


@pytest.fixture(autouse=True)
def _stripe_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_DUMMY")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", WEBHOOK_SECRET)
    monkeypatch.setenv("STRIPE_API_BASE", "https://api.stripe.test")


def _channel(handler: Any) -> StripeChannel:
    return StripeChannel(transport=httpx.MockTransport(handler))


def _sign(raw: bytes, secret: str = WEBHOOK_SECRET, timestamp: int | None = None) -> str:
    ts = str(timestamp if timestamp is not None else int(time.time()))
    digest = hmac.new(secret.encode(), ts.encode() + b"." + raw, hashlib.sha256).hexdigest()
    return f"t={ts},v1={digest}"


async def _no_call(request: httpx.Request) -> httpx.Response:  # pragma: no cover - guard
    raise AssertionError(f"unexpected network call: {request.method} {request.url}")


# ---------------------------------------------------------------------------
# create_session
# ---------------------------------------------------------------------------


async def test_create_session_builds_hosted_checkout_and_encodes_form() -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("authorization")
        captured["form"] = dict(httpx.QueryParams(request.content.decode()))
        return httpx.Response(
            200,
            json={
                "id": "cs_test_123",
                "url": "https://checkout.stripe.com/c/pay/cs_test_123",
                "status": "open",
                "payment_status": "unpaid",
            },
        )

    session = await _channel(handler).create_session(
        "ORD-1001",
        Decimal("129.99"),
        "USD",
        return_url="https://shop.example.com/en/orders/ORD-1001?stripe=1",
        cancel_url="https://shop.example.com/en/orders/ORD-1001",
    )

    assert captured["method"] == "POST"
    assert captured["url"] == "https://api.stripe.test/v1/checkout/sessions"
    assert captured["auth"] == "Bearer sk_test_DUMMY"
    assert captured["form"]["mode"] == "payment"
    assert captured["form"]["line_items[0][price_data][unit_amount]"] == "12999"
    assert captured["form"]["line_items[0][price_data][currency]"] == "usd"
    assert captured["form"]["line_items[0][quantity]"] == "1"
    assert captured["form"]["client_reference_id"] == "ORD-1001"
    assert captured["form"]["metadata[order_number]"] == "ORD-1001"
    assert captured["form"]["success_url"].startswith("https://shop.example.com/en/orders/ORD-1001")
    assert session.session_id == "cs_test_123"
    assert session.status == "requires_action"
    assert session.redirect_url == "https://checkout.stripe.com/c/pay/cs_test_123"
    assert session.currency == "USD"


async def test_create_session_zero_decimal_currency_is_not_multiplied() -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["form"] = dict(httpx.QueryParams(request.content.decode()))
        return httpx.Response(200, json={"id": "cs_jpy", "url": "https://pay.test/cs_jpy"})

    await _channel(handler).create_session("ORD-2002", Decimal("1000"), "JPY", return_url="https://shop.test/rtn")

    # JPY has no minor unit: 1000 yen must be sent as 1000, not 100000.
    assert captured["form"]["line_items[0][price_data][unit_amount]"] == "1000"


async def test_create_session_requires_return_url() -> None:
    with pytest.raises(APIError) as exc:
        await _channel(_no_call).create_session("ORD-1", Decimal("10"), "USD")
    assert "return_url" in exc.value.message


async def test_create_session_rejects_unsupported_currency() -> None:
    with pytest.raises(APIError):
        await _channel(_no_call).create_session(
            "ORD-1", Decimal("10"), "XYZ", return_url="https://shop.test/rtn"
        )


async def test_missing_secret_key_raises_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    channel = _channel(_no_call)
    assert channel.configured is False
    with pytest.raises(APIError) as exc:
        await channel.create_session("ORD-1", Decimal("10"), "USD", return_url="https://shop.test/rtn")
    assert "STRIPE_SECRET_KEY" in exc.value.message


# ---------------------------------------------------------------------------
# capture
# ---------------------------------------------------------------------------


async def test_capture_paid_session_returns_payment_intent_as_transaction() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert str(request.url) == "https://api.stripe.test/v1/checkout/sessions/cs_test_123"
        return httpx.Response(
            200,
            json={
                "id": "cs_test_123",
                "payment_status": "paid",
                "payment_intent": "pi_test_777",
                "amount_total": 12999,
            },
        )

    result = await _channel(handler).capture("cs_test_123")

    assert result.success is True
    assert result.status == "paid"
    assert result.transaction_id == "pi_test_777"


async def test_capture_unpaid_session_requires_action() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"id": "cs_test_123", "payment_status": "unpaid"})

    result = await _channel(handler).capture("cs_test_123")

    assert result.success is False
    assert result.status == "requires_action"
    assert result.error_code == "STRIPE_NOT_PAID"


# ---------------------------------------------------------------------------
# refund
# ---------------------------------------------------------------------------


async def test_refund_posts_payment_intent() -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["form"] = dict(httpx.QueryParams(request.content.decode()))
        return httpx.Response(200, json={"id": "re_test_1"})

    result = await _channel(handler).refund("pi_test_777", Decimal("50.00"), "damaged item")

    assert captured["url"] == "https://api.stripe.test/v1/refunds"
    assert captured["form"]["payment_intent"] == "pi_test_777"
    assert captured["form"]["amount"] == "5000"
    assert result.success is True
    assert result.refund_id == "re_test_1"


async def test_refund_failure_returns_error_result() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(402, json={"error": {"message": "charge has already been refunded"}})

    result = await _channel(handler).refund("pi_test_777", Decimal("50.00"))

    assert result.success is False
    assert result.error_code == "STRIPE_REFUND_FAILED"
    assert "already been refunded" in (result.error_message or "")


# ---------------------------------------------------------------------------
# webhook: signature verification + normalization
# ---------------------------------------------------------------------------


def _session_event(session_id: str = "cs_test_123", payment_status: str = "paid") -> dict[str, Any]:
    return {
        "id": "evt_test_1",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": session_id,
                "object": "checkout.session",
                "payment_status": payment_status,
                "payment_intent": "pi_test_777",
                "amount_total": 12999,
                "currency": "usd",
            }
        },
    }


async def test_webhook_valid_signature_normalizes_captured_event() -> None:
    body = _session_event()
    raw = json.dumps(body, separators=(",", ":")).encode()

    event = await _channel(_no_call).handle_webhook({"stripe-signature": _sign(raw)}, body, raw)

    assert event.channel == "stripe"
    assert event.event_type == "payment.captured"
    assert event.session_id == "cs_test_123"
    assert event.transaction_id == "pi_test_777"
    assert event.amount == Decimal("129.99")
    assert event.currency == "USD"


async def test_webhook_unpaid_session_is_pending_not_captured() -> None:
    body = _session_event(payment_status="unpaid")
    raw = json.dumps(body, separators=(",", ":")).encode()

    event = await _channel(_no_call).handle_webhook({"stripe-signature": _sign(raw)}, body, raw)

    assert event.event_type == "payment.pending"


async def test_webhook_invalid_signature_is_rejected() -> None:
    body = _session_event()
    raw = json.dumps(body, separators=(",", ":")).encode()

    with pytest.raises(APIError) as exc:
        await _channel(_no_call).handle_webhook({"stripe-signature": _sign(raw, secret="whsec_wrong")}, body, raw)
    assert "signature verification failed" in exc.value.message


async def test_webhook_tampered_body_is_rejected() -> None:
    body = _session_event()
    raw = json.dumps(body, separators=(",", ":")).encode()
    header = _sign(raw)
    tampered = json.dumps(_session_event(session_id="cs_attacker"), separators=(",", ":")).encode()

    with pytest.raises(APIError):
        await _channel(_no_call).handle_webhook({"stripe-signature": header}, body, tampered)


async def test_webhook_expired_timestamp_is_rejected() -> None:
    body = _session_event()
    raw = json.dumps(body, separators=(",", ":")).encode()
    stale = _sign(raw, timestamp=int(time.time()) - 5000)

    with pytest.raises(APIError) as exc:
        await _channel(_no_call).handle_webhook({"stripe-signature": stale}, body, raw)
    assert "tolerance" in exc.value.message


async def test_webhook_missing_raw_body_is_rejected() -> None:
    body = _session_event()

    with pytest.raises(APIError) as exc:
        await _channel(_no_call).handle_webhook({"stripe-signature": "t=1,v1=deadbeef"}, body, None)
    assert "raw request body" in exc.value.message


async def test_webhook_refund_event_maps_to_payment_refunded() -> None:
    body = {
        "id": "evt_test_2",
        "type": "charge.refunded",
        "data": {
            "object": {
                "id": "ch_test_1",
                "object": "charge",
                "payment_intent": "pi_test_777",
                "amount_refunded": 5000,
                "currency": "usd",
            }
        },
    }
    raw = json.dumps(body, separators=(",", ":")).encode()

    event = await _channel(_no_call).handle_webhook({"stripe-signature": _sign(raw)}, body, raw)

    assert event.event_type == "payment.refunded"
    assert event.transaction_id == "pi_test_777"
    assert event.amount == Decimal("50.00")


async def test_webhook_missing_secret_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)
    body = _session_event()
    raw = json.dumps(body, separators=(",", ":")).encode()

    with pytest.raises(APIError) as exc:
        await _channel(_no_call).handle_webhook({"stripe-signature": _sign(raw)}, body, raw)
    assert "STRIPE_WEBHOOK_SECRET" in exc.value.message
