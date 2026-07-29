"""Unit tests for ShipmentService (mock repository)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from forge.application.dtos.shipment_dtos import ShipmentCreateDTO, TrackingUpdateDTO
from forge.application.services.shipment_service import ShipmentService
from forge.domain.shipment.models import Shipment


@pytest.fixture
def shipment_service(mock_shipment_repo):
    return ShipmentService(repo=mock_shipment_repo)


class TestShipmentService:
    @pytest.mark.asyncio
    async def test_create_shipment(self, shipment_service, mock_shipment_repo):
        order_id = uuid4()
        dto = ShipmentCreateDTO(
            order_id=order_id,
            tracking_number="TN-999",
            carrier="FedEx",
        )

        async def _fake_save(shipment):
            shipment.id = uuid4()
            return shipment

        mock_shipment_repo.save.side_effect = _fake_save

        result = await shipment_service.create_shipment(dto)
        assert result.order_id == order_id
        assert result.tracking_number == "TN-999"
        assert result.carrier == "FedEx"
        mock_shipment_repo.save.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_shipments_by_order(self, shipment_service, mock_shipment_repo):
        order_id = uuid4()
        s1 = Shipment.create(order_id=order_id, tracking_number="A")
        s2 = Shipment.create(order_id=order_id, tracking_number="B")
        mock_shipment_repo.get_by_order_id.return_value = [s1, s2]

        results = await shipment_service.get_shipments_by_order(order_id)
        assert len(results) == 2
        assert results[0].tracking_number == "A"
        assert results[1].tracking_number == "B"
        mock_shipment_repo.get_by_order_id.assert_awaited_once_with(order_id)

    @pytest.mark.asyncio
    async def test_get_shipments_by_order_empty(self, shipment_service, mock_shipment_repo):
        mock_shipment_repo.get_by_order_id.return_value = []
        results = await shipment_service.get_shipments_by_order(uuid4())
        assert results == []

    @pytest.mark.asyncio
    async def test_update_tracking(self, shipment_service, mock_shipment_repo):
        shipment = Shipment.create(order_id=uuid4())
        shipment.id = uuid4()
        mock_shipment_repo.get_by_id.return_value = shipment

        events = [{"status": "PICKED_UP", "location": "Warehouse"}]

        async def _fake_save(s):
            return s

        mock_shipment_repo.save.side_effect = _fake_save

        dto = TrackingUpdateDTO(events=events)
        result = await shipment_service.update_tracking(shipment.id, dto)
        assert result is not None
        assert len(shipment.events) == 1
        assert shipment.events[0]["status"] == "PICKED_UP"

    @pytest.mark.asyncio
    async def test_update_tracking_not_found(self, shipment_service, mock_shipment_repo):
        mock_shipment_repo.get_by_id.return_value = None
        dto = TrackingUpdateDTO(events=[{"x": 1}])
        result = await shipment_service.update_tracking(uuid4(), dto)
        assert result is None

    @pytest.mark.asyncio
    async def test_update_tracking_with_status(self, shipment_service, mock_shipment_repo):
        shipment = Shipment.create(order_id=uuid4())
        shipment.id = uuid4()
        mock_shipment_repo.get_by_id.return_value = shipment

        async def _fake_save(s):
            return s

        mock_shipment_repo.save.side_effect = _fake_save

        dto = TrackingUpdateDTO(events=[{"status": "PICKED_UP"}], status="PICKED_UP")
        result = await shipment_service.update_tracking(shipment.id, dto)
        assert result is not None
        assert shipment.status.name == "PICKED_UP"
