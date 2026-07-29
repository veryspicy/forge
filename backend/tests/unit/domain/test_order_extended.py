"""Unit tests for Order aggregate — extended methods (review, procurement)."""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest
from forge.domain.order.models import Order, OrderStatus, ShippingAddress


def _make_order(status: OrderStatus = OrderStatus.PENDING) -> Order:
    """Helper: create an order in a given state, walking the state machine.

    Valid transitions: PENDING→CONFIRMED→PAID→PENDING_REVIEW→PROCURING→...
    """
    order = Order.create(user_id=uuid4())

    # PENDING → CONFIRMED → PAID (base path)
    if status in (
        OrderStatus.CONFIRMED,
        OrderStatus.PAID,
        OrderStatus.PENDING_REVIEW,
        OrderStatus.PROCURING,
        OrderStatus.SHIPPED,
        OrderStatus.PROCURE_FAILED,
        OrderStatus.DELIVERED,
    ):
        order.transition_status(OrderStatus.CONFIRMED)

    if status in (
        OrderStatus.PAID,
        OrderStatus.PENDING_REVIEW,
        OrderStatus.PROCURING,
        OrderStatus.SHIPPED,
        OrderStatus.PROCURE_FAILED,
        OrderStatus.DELIVERED,
    ):
        order.confirm_payment("pi_test_123")

    if status in (
        OrderStatus.PENDING_REVIEW,
        OrderStatus.PROCURING,
        OrderStatus.PROCURE_FAILED,
    ):
        order.submit_for_review()

    if status in (OrderStatus.PROCURING, OrderStatus.PROCURE_FAILED):
        order.approve()

    if status == OrderStatus.PROCURE_FAILED:
        order.mark_procure_failed("out of stock")

    if status == OrderStatus.SHIPPED:
        order.transition_status(OrderStatus.PROCESSING)
        order.ship("TN-001")

    if status == OrderStatus.DELIVERED:
        order.transition_status(OrderStatus.PROCESSING)
        order.ship("TN-001")
        order.transition_status(OrderStatus.DELIVERED)

    return order


class TestOrderReview:
    """订单审核流程 单元测试。"""

    def test_submit_for_review_from_paid(self):
        order = _make_order(OrderStatus.PAID)
        order.submit_for_review()
        assert order.status == OrderStatus.PENDING_REVIEW

    def test_approve_order(self):
        order = _make_order(OrderStatus.PENDING_REVIEW)
        order.approve()
        assert order.status == OrderStatus.PROCURING

    def test_reject_order_with_reason(self):
        order = _make_order(OrderStatus.PENDING_REVIEW)
        order.reject("Supplier unavailable")
        assert order.status == OrderStatus.CANCELLED
        assert order.review_reason == "Supplier unavailable"

    def test_start_procurement(self):
        order = _make_order(OrderStatus.PROCURING)
        order.start_procurement(supplier_id="SUP-001")
        assert order.supplier_id == "SUP-001"

    def test_mark_procure_failed(self):
        order = _make_order(OrderStatus.PROCURING)
        order.mark_procure_failed("Out of stock")
        assert order.status == OrderStatus.PROCURE_FAILED
        assert order.review_reason == "Out of stock"

    def test_invalid_transition_shipped_cannot_approve(self):
        order = _make_order(OrderStatus.SHIPPED)
        with pytest.raises(ValueError, match="Cannot transition from SHIPPED"):
            order.approve()

    def test_approve_without_pending_review_raises(self):
        order = _make_order(OrderStatus.PROCURING)
        with pytest.raises(ValueError, match="Cannot transition from PROCURING"):
            order.approve()

    def test_submit_for_review_from_not_paid_raises(self):
        order = _make_order(OrderStatus.PENDING)
        with pytest.raises(ValueError, match="Cannot transition from PENDING"):
            order.submit_for_review()

    def test_reject_records_reason_then_cancel(self):
        order = _make_order(OrderStatus.PENDING_REVIEW)
        order.reject("Fraud detected")
        assert order.status == OrderStatus.CANCELLED
        assert order.review_reason == "Fraud detected"

    def test_refund_from_procure_failed(self):
        order = _make_order(OrderStatus.PROCURE_FAILED)
        order.refund("Supplier out of business")
        assert order.status == OrderStatus.REFUNDED
