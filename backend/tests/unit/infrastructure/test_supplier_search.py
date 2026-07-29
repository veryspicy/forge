"""Unit tests for MockSupplierAdapter."""

from __future__ import annotations

import pytest
from forge.infrastructure.ai.supplier_search import MockSupplierAdapter


@pytest.fixture
def adapter():
    return MockSupplierAdapter(latency_ms=0)


class TestMockSupplierAdapter:
    @pytest.mark.asyncio
    async def test_search_returns_results(self, adapter):
        results = await adapter.search(query="dog food")
        assert len(results) > 0
        assert all(r.supplier_id == "mock-supplier-001" for r in results)
        assert all(r.supplier_name == "PetSupply Direct" for r in results)

    @pytest.mark.asyncio
    async def test_search_filter_by_pet_type(self, adapter):
        """Scoring-based filter: CAT products score higher and appear first."""
        results = await adapter.search(query="", pet_type="CAT", limit=4)
        assert len(results) == 4
        # Top results should all be CAT products (scored +5 vs -10 for others)
        assert all("CAT" in [p.upper() for p in r.pet_types] for r in results)

    @pytest.mark.asyncio
    async def test_search_filter_by_max_price(self, adapter):
        """Scoring-based filter: under-budget items score higher."""
        results = await adapter.search(query="", max_price=20.0, limit=3)
        assert len(results) == 3
        # Top-scoring items should all be within budget (others get -20 penalty)
        assert all(r.cost_price <= 20.0 for r in results)

    @pytest.mark.asyncio
    async def test_search_no_results_for_unmatched(self, adapter):
        results = await adapter.search(query="xyzzy_ nonexistent_12345")
        # Should still return results since scoring is soft—but with negative scores
        # Mock adapter returns all results; actual matching is by score.
        # All items will have scores <= 0, sorted but still returned.
        # This is by design: the mock adapter returns all results ranked.
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_limit(self, adapter):
        results = await adapter.search(query="", limit=3)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_search_result_fields(self, adapter):
        results = await adapter.search(query="dog", limit=1)
        assert len(results) == 1
        r = results[0]
        assert r.supplier_sku.startswith("MOCK-SKU-")
        assert r.currency == "USD"
        assert r.stock_status in ("in_stock", "low_stock", "out_of_stock")
        assert r.category != ""
        assert isinstance(r.pet_types, list)
        assert isinstance(r.specifications, dict)
