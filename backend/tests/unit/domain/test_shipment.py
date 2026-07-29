"""Unit tests for Shipment aggregate root."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest
from forge.domain.shipment.models import Shipment, ShipmentStatus


class TestShipment:
    """物流聚合根 单元测试。"""

    def test_create_shipment(self):
        order_id = uuid4()
        shipment = Shipment.create(
            order_id=order_id,
            supplier_id="SUP-001",
            tracking_number="TN-123456",
            carrier="DHL",
            tracking_url="https://track.dhl.com/123",
            origin="New York",
            destination="Los Angeles",
        )
        assert shipment.order_id == order_id
        assert shipment.tracking_number == "TN-123456"
        assert shipment.carrier == "DHL"
        assert shipment.tracking_url == "https://track.dhl.com/123"
        assert shipment.origin == "New York"
        assert shipment.destination == "Los Angeles"
        assert shipment.status == ShipmentStatus.PENDING

    def test_create_shipment_defaults(self):
        order_id = uuid4()
        shipment = Shipment.create(order_id=order_id)
        assert shipment.supplier_id == ""
        assert shipment.tracking_number == ""
        assert shipment.carrier == ""

    def test_update_tracking(self):
        shipment = Shipment.create(order_id=uuid4())
        events = [
            {"timestamp": "2026-06-24T10:00:00Z", "location": "NYC", "status": "PICKED_UP"},
            {"timestamp": "2026-06-24T14:00:00Z", "location": "JFK", "status": "IN_TRANSIT"},
        ]
        shipment.update_tracking(events)
        assert len(shipment.events) == 2
        assert shipment.events[0]["status"] == "PICKED_UP"

    def test_update_tracking_empty_list_noop(self):
        shipment = Shipment.create(order_id=uuid4())
        original_updated_at = shipment.updated_at
        shipment.update_tracking([])
        assert len(shipment.events) == 0

    def test_add_event(self):
        shipment = Shipment.create(order_id=uuid4())
        shipment.add_event({"location": "LA", "status": "OUT_FOR_DELIVERY"})
        assert len(shipment.events) == 1
        assert shipment.events[0]["location"] == "LA"

    def test_mark_delivered(self):
        shipment = Shipment.create(order_id=uuid4())
        shipment.mark_picked_up()
        shipment.mark_in_transit()
        shipment.mark_out_for_delivery()
        shipment.mark_delivered()
        assert shipment.status == ShipmentStatus.DELIVERED
        assert shipment.actual_delivery is not None

    def test_delivered_tracking_frozen(self):
        """DELIVERED and FAILED statuses have no allowed transitions."""
        shipment = Shipment.create(order_id=uuid4())
        shipment.mark_picked_up()
        shipment.mark_in_transit()
        shipment.mark_out_for_delivery()
        shipment.mark_delivered()
        # Cannot transition from DELIVERED
        with pytest.raises(ValueError, match="Cannot transition shipment from DELIVERED"):
            shipment.mark_in_transit()

    def test_invalid_status_transition(self):
        """Cannot jump from PENDING to DELIVERED."""
        shipment = Shipment.create(order_id=uuid4())
        with pytest.raises(ValueError, match="Cannot transition shipment from PENDING"):
            shipment.mark_delivered()

    def test_mark_picked_up(self):
        shipment = Shipment.create(order_id=uuid4())
        shipment.mark_picked_up()
        assert shipment.status == ShipmentStatus.PICKED_UP

    def test_mark_in_transit(self):
        shipment = Shipment.create(order_id=uuid4())
        shipment.mark_picked_up()
        shipment.mark_in_transit()
        assert shipment.status == ShipmentStatus.IN_TRANSIT

    def test_mark_failed(self):
        shipment = Shipment.create(order_id=uuid4())
        shipment.mark_failed("Package damaged")
        assert shipment.status == ShipmentStatus.FAILED
        assert shipment.notes == "Package damaged"

    def test_failed_frozen(self):
        shipment = Shipment.create(order_id=uuid4())
        shipment.mark_failed()
        with pytest.raises(ValueError, match="Cannot transition shipment from FAILED"):
            shipment.mark_picked_up()
