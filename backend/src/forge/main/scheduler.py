"""定时任务调度（P2-5：每晚增量同步供应商库存/价格）。"""

from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from forge.application.services.supplier_source_service import SupplierSourceService
from forge.infrastructure.persistence.models import ORMSupplier
from forge.main.dependencies import async_session_factory

# 触发厂商适配器注册，保证定时同步能解析供应商 provider
import forge.suppliers.bootstrap  # noqa: F401  (isort:skip)

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")

_SYNC_JOB_ID = "daily_supplier_sync"
_SYNC_HOUR = 3  # 每日凌晨 3 点增量同步


async def _run_daily_supplier_sync() -> None:
    """对所有已配置 provider 且启用中的供应商执行增量同步。"""
    async with async_session_factory() as db:
        suppliers = (
            await db.scalars(
                select(ORMSupplier).where(
                    ORMSupplier.provider_code.is_not(None),
                    ORMSupplier.is_active.is_(True),
                )
            )
        ).all()
        if not suppliers:
            logger.info("定时供应商同步：无已配置供应商，跳过")
            return
        for supplier in suppliers:
            try:
                log = await SupplierSourceService.sync_supplier(
                    db,
                    supplier=supplier,
                    trigger_type="scheduled",
                )
                logger.info(
                    "定时供应商同步完成 supplier=%s status=%s updated=%s",
                    supplier.name,
                    log.status,
                    log.items_updated,
                )
            except Exception:  # noqa: BLE001 - 单个供应商失败不影响其余
                logger.exception("定时供应商同步失败 supplier=%s", supplier.name)


def start_scheduler() -> None:
    if scheduler.running:
        return
    scheduler.add_job(
        _run_daily_supplier_sync,
        CronTrigger(hour=_SYNC_HOUR, minute=0),
        id=_SYNC_JOB_ID,
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    logger.info("供应商定时同步已启动（每日 %02d:00）", _SYNC_HOUR)


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("供应商定时同步已停止")
