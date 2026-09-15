# mypy: ignore-errors
"""Unit tests for Returns API — C 端售后申请 + Admin 审批/退款。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import UUID

from forge.api.errors import APIError, ErrorCode

OWNER_ID = UUID("11111111-1111-4111-8111-111111111111")
ORDER_ID = UUID("22222222-2222-4222-8222-222222222222")
ITEM_ID = UUID("33333333-3333-4333-8333-333333333333")
RETURN_ID = UUID("44444444-4444-4444-8444-444444444444")


class _FakeReturnItem:
    def __init__(self) -> None:
        self.id = UUID("55555555-5555-4555-8555-555555555555")
        self.order_item_id = ITEM_ID
        self.name = "Test Product"
        self.sku = "SKU-1"
        self.unit_price = Decimal("10.00")
        self.quantity = 1


class _FakeReturn:
    """Minimal object consumed by SQLAlchemyReturnRepository.to_dict."""

    def __init__(self, status: str = "requested") -> None:
        now = datetime(2026, 9, 12, 10, 0, 0)
        self.id = RETURN_ID
        self.return_number = "RT-20260912-ABC123"
        self.order_id = ORDER_ID
        self.user_id = OWNER_ID
        self.status = status
        self.reason = "damaged"
        self.note = None
        self.refund_method = "original"
        self.refund_amount = Decimal("10.00")
        self.refund_shipping = False
        self.restock = True
        self.requested_at = now
        self.deadline_at = None
        self.reviewed_at = None
        self.reviewed_by = None
        self.review_note = None
        self.carrier = None
        self.tracking_number = None
        self.shipped_at = None
        self.received_at = None
        self.refunded_at = None
        self.refund_id = None
        self.cancelled_at = None
        self.closed_reason = None
        self.created_at = now
        self.updated_at = now
        self.items = [_FakeReturnItem()]


def _setup_customer_auth(test_client):
    from forge.api.v1.auth import get_current_user
    from forge.main import dependencies

    async def _fake_get_db():
        yield AsyncMock()

    async def _fake_user():
        return {"sub": "buyer@example.com"}

    test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
    test_client.app.dependency_overrides[get_current_user] = _fake_user


def _patch_owner():
    return patch(
        "forge.api.v1.orders.SQLAlchemyUserRepository.get_by_email",
        new_callable=AsyncMock,
        return_value=SimpleNamespace(id=OWNER_ID),
    )


class TestCustomerReturnsAPI:
    """C 端 /api/v1/returns 售后申请链路。"""

    def test_list_returns_success(self, test_client):
        from forge.infrastructure.persistence.repositories.return_repo import SQLAlchemyReturnRepository

        _setup_customer_auth(test_client)
        with (
            _patch_owner(),
            patch.object(
                SQLAlchemyReturnRepository,
                "list_customer_returns",
                new_callable=AsyncMock,
                return_value={"items": [], "total": 0, "page": 1, "page_size": 10},
            ),
        ):
            resp = test_client.get("/api/v1/returns")
        test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_list_returns_filters_by_order_number(self, test_client):
        from forge.infrastructure.persistence.repositories.return_repo import SQLAlchemyReturnRepository

        _setup_customer_auth(test_client)
        with (
            _patch_owner(),
            patch.object(
                SQLAlchemyReturnRepository,
                "list_customer_returns",
                new_callable=AsyncMock,
                return_value={"items": [], "total": 0, "page": 1, "page_size": 10},
            ) as mocked,
        ):
            resp = test_client.get("/api/v1/returns?order_number=FG-TEST-0001")
        test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert mocked.await_args.kwargs["order_number"] == "FG-TEST-0001"

    def test_list_returns_unauthorized(self, test_client):
        resp = test_client.get("/api/v1/returns")
        assert resp.status_code == 401

    def test_create_return_success(self, test_client):
        from forge.infrastructure.persistence.repositories import order_repo, return_repo

        _setup_customer_auth(test_client)
        fake_return = _FakeReturn()
        with (
            _patch_owner(),
            patch.object(
                order_repo.SQLAlchemyCustomerOrderRepository,
                "get_by_user_and_number",
                new_callable=AsyncMock,
                return_value=SimpleNamespace(id=ORDER_ID, order_number="FG-TEST-0001"),
            ),
            patch.object(
                return_repo.SQLAlchemyReturnRepository,
                "create_return_request",
                new_callable=AsyncMock,
                return_value=fake_return,
            ),
        ):
            resp = test_client.post(
                "/api/v1/returns",
                json={
                    "order_number": "FG-TEST-0001",
                    "items": [{"order_item_id": str(ITEM_ID), "quantity": 1}],
                    "reason": "damaged",
                },
            )
        test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200
        body = resp.json()
        assert body["return_number"] == "RT-20260912-ABC123"
        assert body["status"] == "requested"
        assert body["items"][0]["quantity"] == 1

    def test_create_return_quantity_exceeds(self, test_client):
        from forge.infrastructure.persistence.repositories import order_repo, return_repo

        _setup_customer_auth(test_client)
        with (
            _patch_owner(),
            patch.object(
                order_repo.SQLAlchemyCustomerOrderRepository,
                "get_by_user_and_number",
                new_callable=AsyncMock,
                return_value=SimpleNamespace(id=ORDER_ID, order_number="FG-TEST-0001"),
            ),
            patch.object(
                return_repo.SQLAlchemyReturnRepository,
                "create_return_request",
                new_callable=AsyncMock,
                side_effect=APIError(ErrorCode.RETURN_QUANTITY_EXCEEDS, message="exceeds"),
            ),
        ):
            resp = test_client.post(
                "/api/v1/returns",
                json={
                    "order_number": "FG-TEST-0001",
                    "items": [{"order_item_id": str(ITEM_ID), "quantity": 5}],
                    "reason": "damaged",
                },
            )
        test_client.app.dependency_overrides.clear()
        assert resp.status_code == 422

    def test_eligibility_success(self, test_client):
        from forge.infrastructure.persistence.repositories import order_repo, return_repo

        _setup_customer_auth(test_client)
        with (
            _patch_owner(),
            patch.object(
                order_repo.SQLAlchemyCustomerOrderRepository,
                "get_by_user_and_number",
                new_callable=AsyncMock,
                return_value=SimpleNamespace(id=ORDER_ID, order_number="FG-TEST-0001"),
            ),
            patch.object(
                return_repo.SQLAlchemyReturnRepository,
                "return_eligibility",
                new_callable=AsyncMock,
                return_value={"eligible": True, "items": [], "refundable_amount": 10.0},
            ),
        ):
            resp = test_client.get("/api/v1/returns/eligibility?order_number=FG-TEST-0001")
        test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert resp.json()["eligible"] is True

    def test_cancel_return_success(self, test_client):
        from forge.infrastructure.persistence.repositories.return_repo import SQLAlchemyReturnRepository

        _setup_customer_auth(test_client)
        fake_return = _FakeReturn(status="cancelled")
        with (
            _patch_owner(),
            patch.object(
                SQLAlchemyReturnRepository,
                "get_return_request",
                new_callable=AsyncMock,
                return_value=fake_return,
            ),
            patch.object(
                SQLAlchemyReturnRepository,
                "cancel_return_request",
                new_callable=AsyncMock,
                return_value=fake_return,
            ),
        ):
            resp = test_client.post("/api/v1/returns/RT-20260912-ABC123/cancel", json={"reason": "changed mind"})
        test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

    def test_get_return_not_owner(self, test_client):
        from forge.infrastructure.persistence.repositories.return_repo import SQLAlchemyReturnRepository

        _setup_customer_auth(test_client)
        other = _FakeReturn()
        other.user_id = UUID("99999999-9999-4999-8999-999999999999")
        with (
            _patch_owner(),
            patch.object(
                SQLAlchemyReturnRepository,
                "get_return_request",
                new_callable=AsyncMock,
                return_value=other,
            ),
        ):
            resp = test_client.get("/api/v1/returns/RT-20260912-ABC123")
        test_client.app.dependency_overrides.clear()
        assert resp.status_code == 404


class TestAdminReturnsAPI:
    """Admin /api/admin/v1/returns 审批与退款链路。"""

    def test_list_returns(self, test_client, override_auth):
        from forge.infrastructure.persistence.repositories.return_repo import SQLAlchemyReturnRepository

        with patch.object(
            SQLAlchemyReturnRepository,
            "list_admin_returns",
            new_callable=AsyncMock,
            return_value={"items": [{"return_number": "RT-1"}], "total": 1},
        ):
            resp = test_client.get("/api/admin/v1/returns/")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_returns_stats(self, test_client, override_auth):
        from forge.infrastructure.persistence.repositories.return_repo import SQLAlchemyReturnRepository

        with patch.object(
            SQLAlchemyReturnRepository,
            "return_stats",
            new_callable=AsyncMock,
            return_value={
                "requested": 2,
                "approved": 1,
                "received": 0,
                "refunded": 3,
                "rejected": 0,
                "cancelled": 0,
                "closed": 0,
                "refunded_amount": 29.9,
                "total": 6,
            },
        ):
            resp = test_client.get("/api/admin/v1/returns/stats")
        assert resp.status_code == 200
        assert resp.json()["requested"] == 2
        assert resp.json()["refunded_amount"] == 29.9

    def test_review_return(self, test_client, override_auth):
        from forge.infrastructure.persistence.repositories.return_repo import SQLAlchemyReturnRepository

        fake_return = _FakeReturn(status="approved")
        with (
            patch.object(
                SQLAlchemyReturnRepository,
                "get_return_request",
                new_callable=AsyncMock,
                return_value=fake_return,
            ),
            patch.object(
                SQLAlchemyReturnRepository,
                "review_return_request",
                new_callable=AsyncMock,
                return_value=fake_return,
            ) as review_mock,
        ):
            resp = test_client.post(
                "/api/admin/v1/returns/RT-20260912-ABC123/review",
                json={"approved": True, "note": "ok", "restock": True},
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"
        assert review_mock.await_args.kwargs["approved"] is True

    def test_review_return_reject_requires_note(self, test_client, override_auth):
        from forge.infrastructure.persistence.repositories.return_repo import SQLAlchemyReturnRepository

        fake_return = _FakeReturn(status="requested")
        with (
            patch.object(
                SQLAlchemyReturnRepository,
                "get_return_request",
                new_callable=AsyncMock,
                return_value=fake_return,
            ),
            patch.object(
                SQLAlchemyReturnRepository,
                "review_return_request",
                new_callable=AsyncMock,
            ) as review_mock,
        ):
            resp = test_client.post(
                "/api/admin/v1/returns/RT-20260912-ABC123/review",
                json={"approved": False, "note": "  "},
            )
        assert resp.status_code == 422, resp.text
        assert fake_return.status == "requested"
        review_mock.assert_not_awaited()

    def test_refund_return(self, test_client, override_auth):
        from forge.infrastructure.persistence.repositories.return_repo import SQLAlchemyReturnRepository

        fake_return = _FakeReturn(status="refunded")
        with (
            patch.object(
                SQLAlchemyReturnRepository,
                "get_return_request",
                new_callable=AsyncMock,
                return_value=fake_return,
            ),
            patch.object(
                SQLAlchemyReturnRepository,
                "execute_return_refund",
                new_callable=AsyncMock,
                return_value=fake_return,
            ),
        ):
            resp = test_client.post("/api/admin/v1/returns/RT-20260912-ABC123/refund", json={})
        assert resp.status_code == 200
        assert resp.json()["status"] == "refunded"

    def test_returns_require_permission(self, test_client):
        resp = test_client.get("/api/admin/v1/returns/")
        assert resp.status_code == 401
