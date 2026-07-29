"""Shared fixtures for Admin API tests using dependency_overrides."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

FAKE_ADMIN_ID = "d290f1ee-6c54-4b01-90e6-d701748f0851"


@pytest.fixture
def fake_db_session():
    """An AsyncMock simulating AsyncSession."""
    return AsyncMock()


@pytest.fixture
def override_auth(test_client, fake_db_session):
    """Override get_db and get_current_user_id for admin unit tests."""
    from forge.main import dependencies

    async def _fake_get_db():
        yield fake_db_session

    async def _fake_user_id():
        return UUID(FAKE_ADMIN_ID)

    test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
    test_client.app.dependency_overrides[dependencies.get_current_user_id] = _fake_user_id

    yield

    test_client.app.dependency_overrides.clear()
