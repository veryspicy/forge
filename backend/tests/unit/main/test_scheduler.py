"""Unit tests for the daily supplier sync scheduler."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from forge.main import scheduler as scheduler_mod
from forge.main.scheduler import _run_daily_supplier_sync, start_scheduler, stop_scheduler


def _make_supplier(name="supplier-a", provider_code="zendrop", is_active=True):
    sup = MagicMock()
    sup.name = name
    sup.provider_code = provider_code
    sup.is_active = is_active
    return sup


def _make_sync_log(status="success", items_updated=3):
    log = MagicMock()
    log.status = status
    log.items_updated = items_updated
    return log


class TestStartStop:
    def test_start_scheduler_adds_job_and_starts(self):
        fake = MagicMock()
        fake.running = False
        with patch.object(scheduler_mod, "scheduler", fake):
            start_scheduler()
        fake.add_job.assert_called_once()
        fake.start.assert_called_once()
        assert fake.add_job.call_args.kwargs["id"] == "daily_supplier_sync"

    def test_start_scheduler_already_running_skips(self):
        fake = MagicMock()
        fake.running = True
        with patch.object(scheduler_mod, "scheduler", fake):
            start_scheduler()
        fake.add_job.assert_not_called()
        fake.start.assert_not_called()

    def test_stop_scheduler_shutdown_when_running(self):
        fake = MagicMock()
        fake.running = True
        with patch.object(scheduler_mod, "scheduler", fake):
            stop_scheduler()
        fake.shutdown.assert_called_once()

    def test_stop_scheduler_noop_when_not_running(self):
        fake = MagicMock()
        fake.running = False
        with patch.object(scheduler_mod, "scheduler", fake):
            stop_scheduler()
        fake.shutdown.assert_not_called()


def _make_session_factory(suppliers):
    session = AsyncMock()
    scalars = MagicMock()
    scalars.all.return_value = suppliers
    session.scalars.return_value = scalars
    factory = MagicMock()
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=False)
    factory.return_value = cm
    return factory


class TestDailySync:
    @pytest.mark.asyncio
    async def test_no_suppliers_skips(self):
        with (
            patch("forge.main.scheduler.async_session_factory", _make_session_factory([])),
            patch.object(
                scheduler_mod,
                "SupplierSourceService",
            ) as svc,
        ):
            await _run_daily_supplier_sync()
        svc.sync_supplier.assert_not_called()

    @pytest.mark.asyncio
    async def test_syncs_each_supplier(self):
        with (
            patch(
                "forge.main.scheduler.async_session_factory",
                _make_session_factory([_make_supplier("a"), _make_supplier("b")]),
            ),
            patch.object(
                scheduler_mod,
                "SupplierSourceService",
                sync_supplier=AsyncMock(return_value=_make_sync_log()),
            ) as svc,
        ):
            await _run_daily_supplier_sync()
        assert svc.sync_supplier.await_count == 2

    @pytest.mark.asyncio
    async def test_single_failure_does_not_abort(self):
        with (
            patch(
                "forge.main.scheduler.async_session_factory",
                _make_session_factory([_make_supplier("a")]),
            ),
            patch.object(
                scheduler_mod,
                "SupplierSourceService",
                sync_supplier=AsyncMock(side_effect=RuntimeError("boom")),
            ) as svc,
        ):
            await _run_daily_supplier_sync()
        assert svc.sync_supplier.await_count == 1
