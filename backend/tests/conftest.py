"""Forge — Global test fixtures."""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

# Ensure backend src is on sys.path
backend_root = Path(__file__).resolve().parent.parent / "src"
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

# ---------------------------------------------------------------------------
# Podman PostgreSQL — set before any forge import so database.py
# picks up the correct DATABASE_URL at module load time.
# ---------------------------------------------------------------------------
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/forge",
)
os.environ.setdefault(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/forge_test",
)


# ---------------------------------------------------------------------------
# UUID / datetime / Decimal factories
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_uuid() -> UUID:
    return uuid4()


@pytest.fixture
def now_dt() -> datetime:
    return datetime(2026, 6, 24, 12, 0, 0)


@pytest.fixture
def future_dt(now_dt: datetime) -> datetime:
    return now_dt + timedelta(days=90)


@pytest.fixture
def past_dt(now_dt: datetime) -> datetime:
    return now_dt - timedelta(days=10)


# ---------------------------------------------------------------------------
# DB / repo mocks
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_db_session() -> AsyncMock:
    """Mocked AsyncSession for repository injection."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_supplier_repo() -> AsyncMock:
    """Mocked SQLAlchemySupplierRepository."""
    repo = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.create = AsyncMock()
    repo.update = AsyncMock()
    repo.get_all = AsyncMock()
    return repo


@pytest.fixture
def mock_pricing_rule_repo() -> AsyncMock:
    """Mocked SQLAlchemyPricingRuleRepository."""
    repo = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.save = AsyncMock()
    repo.delete = AsyncMock()
    repo.list_all = AsyncMock()
    repo.list_active_rules = AsyncMock()
    return repo


@pytest.fixture
def mock_promotion_repo() -> AsyncMock:
    """Mocked SQLAlchemyPromotionRepository."""
    repo = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.save = AsyncMock()
    repo.delete = AsyncMock()
    repo.list_all = AsyncMock()
    repo.list_active = AsyncMock()
    return repo


@pytest.fixture
def mock_shipment_repo() -> AsyncMock:
    """Mocked ShipmentRepository."""
    repo = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.save = AsyncMock()
    repo.get_by_order_id = AsyncMock()
    return repo


@pytest.fixture
def mock_product_service() -> AsyncMock:
    """Mocked ProductService."""
    svc = AsyncMock()
    svc.create_product = AsyncMock()
    return svc


@pytest.fixture
def mock_pricing_service() -> AsyncMock:
    """Mocked PricingService for use as dependency."""
    svc = AsyncMock()
    svc.calculate_price = AsyncMock()
    return svc


@pytest.fixture
def mock_llm_client() -> AsyncMock:
    """Mocked OpenAIClient."""
    client = AsyncMock()
    client.chat_completion = AsyncMock()
    return client


# ---------------------------------------------------------------------------
# FastAPI TestClient
# ---------------------------------------------------------------------------

@pytest.fixture
def test_client() -> TestClient:
    """TestClient for the FastAPI app."""
    from forge.main.application import app
    return TestClient(app)
