"""Shared fixtures for Admin API tests using dependency_overrides."""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import UUID

import pytest

FAKE_ADMIN_ID = "d290f1ee-6c54-4b01-90e6-d701748f0851"


@pytest.fixture
def fake_db_session():
    """An AsyncMock simulating AsyncSession."""
    return AsyncMock()


@pytest.fixture
def override_auth(test_client, fake_db_session):
    """Override get_db and get_current_admin for admin unit tests."""
    from forge.main import dependencies

    async def _fake_get_db():
        yield fake_db_session

    async def _fake_admin():
        return {"id": UUID(FAKE_ADMIN_ID), "role": "super_admin", "roles": ["super_admin"]}

    test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
    test_client.app.dependency_overrides[dependencies.get_current_admin] = _fake_admin

    yield

    test_client.app.dependency_overrides.clear()
