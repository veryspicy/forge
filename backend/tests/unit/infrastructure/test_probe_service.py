"""Unit tests for AIProbeService (mock all dependencies)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from forge.infrastructure.ai.probe_service import AIProbeService
from forge.infrastructure.ai.supplier_search import MockSupplierAdapter, SupplierProductResult


@pytest.fixture
def mock_adapter():
    adapter = MockSupplierAdapter(latency_ms=0)
    return adapter


@pytest.fixture
def mock_llm():
    client = AsyncMock()
    client.chat_completion = AsyncMock()
    return client


@pytest.fixture
def probe_service(mock_adapter, mock_llm, mock_pricing_service, mock_product_service):
    return AIProbeService(
        supplier_adapters=[mock_adapter],
        pricing_service=mock_pricing_service,
        product_service=mock_product_service,
        llm_client=mock_llm,
    )


def _fake_llm_response(params: dict) -> str:
    return json.dumps(params)


class TestAIProbeService:
    @pytest.mark.asyncio
    async def test_extract_search_params(self, probe_service, mock_llm):
        mock_llm.chat_completion.return_value = _fake_llm_response({
            "pet_type": "DOG",
            "category": "FOOD",
            "keywords": ["grain-free", "dog food", "organic"],
            "max_budget": None,
            "region": None,
        })
        params = await probe_service.extract_search_params("I need grain-free organic dog food")
        assert params["pet_type"] == "DOG"
        assert params["category"] == "FOOD"
        assert "grain-free" in params["keywords"]

    @pytest.mark.asyncio
    async def test_extract_search_params_fallback_on_error(self, probe_service, mock_llm):
        mock_llm.chat_completion.side_effect = Exception("API error")
        params = await probe_service.extract_search_params("dog food grain-free organic")
        # Fallback: keywords are the first 5 words of the query
        assert "keywords" in params
        assert len(params["keywords"]) > 0
        assert params["pet_type"] is None

    @pytest.mark.asyncio
    async def test_extract_search_params_strips_markdown(self, probe_service, mock_llm):
        mock_llm.chat_completion.return_value = '```json\n{"pet_type":"CAT","category":null,"keywords":["litter"],"max_budget":null,"region":null}\n```'
        params = await probe_service.extract_search_params("cat litter")
        assert params["pet_type"] == "CAT"

    @pytest.mark.asyncio
    async def test_probe_returns_results(self, probe_service, mock_llm, mock_pricing_service):
        mock_llm.chat_completion.return_value = _fake_llm_response({
            "pet_type": "DOG",
            "category": "FOOD",
            "keywords": ["dog food"],
            "max_budget": None,
            "region": None,
        })
        mock_pricing_service.calculate_price.return_value = MagicMock(final_price=40.0)

        results = await probe_service.probe("dog food", region="US")
        assert len(results) > 0
        for r in results:
            assert r.supplier_product is not None
            assert isinstance(r.suggested_retail_price, float)

    @pytest.mark.asyncio
    async def test_auto_create_below_threshold(self, probe_service, mock_llm, mock_pricing_service):
        mock_llm.chat_completion.return_value = _fake_llm_response({
            "pet_type": "DOG",
            "category": None,
            "keywords": ["dental chew"],
            "max_budget": None,
            "region": None,
        })
        mock_pricing_service.calculate_price.return_value = MagicMock(final_price=21.0)

        results = await probe_service.probe("dental chews", auto_create_threshold=50.0)
        # Dental Chew Sticks cost $12.00, should be auto_create=True
        auto_creates = [r for r in results if r.auto_create]
        assert len(auto_creates) > 0
        assert all(r.supplier_product.cost_price <= 50.0 for r in auto_creates)

    @pytest.mark.asyncio
    async def test_no_auto_create_above_threshold(self, probe_service, mock_llm, mock_pricing_service):
        mock_llm.chat_completion.return_value = _fake_llm_response({
            "pet_type": "CAT",
            "category": None,
            "keywords": ["self-cleaning litter box"],
            "max_budget": None,
            "region": None,
        })
        mock_pricing_service.calculate_price.return_value = MagicMock(final_price=280.0)

        results = await probe_service.probe("self-cleaning litter box", auto_create_threshold=50.0)
        # Self-cleaning litter box costs $199, above threshold
        for r in results:
            if r.supplier_product.cost_price > 50.0:
                assert r.auto_create is False
                assert r.needs_review is True

    @pytest.mark.asyncio
    async def test_probe_results_sorted(self, probe_service, mock_llm, mock_pricing_service):
        mock_llm.chat_completion.return_value = _fake_llm_response({
            "pet_type": None,
            "category": None,
            "keywords": ["toy"],
            "max_budget": None,
            "region": None,
        })
        mock_pricing_service.calculate_price.return_value = MagicMock(final_price=30.0)

        results = await probe_service.probe("pet toys", auto_create_threshold=20.0)
        # Auto-create (below threshold) first, then by cost ascending
        for i in range(len(results) - 1):
            a, b = results[i], results[i + 1]
            assert (not a.auto_create) <= (not b.auto_create)

    @pytest.mark.asyncio
    async def test_auto_create_product_no_product_service(self, mock_adapter, mock_llm, mock_pricing_service):
        svc = AIProbeService(
            supplier_adapters=[mock_adapter],
            pricing_service=mock_pricing_service,
            product_service=None,
            llm_client=mock_llm,
        )
        result = await svc.auto_create_product(
            SupplierProductResult(
                supplier_id="s1",
                supplier_name="test",
                supplier_sku="SKU-1",
                title="Test",
                description="",
                cost_price=10.0,
                currency="USD",
                images=[],
                category="FOOD",
                pet_types=["DOG"],
                specifications={},
                stock_status="in_stock",
            ),
            region="US",
        )
        assert result is None
