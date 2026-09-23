"""Shipment — Admin 运单查询与归档（后台软删除）仓储。

职责边界：
- 本模块只服务后台运单列表 / 归档口径；下单与履约过程中的运单创建仍由 order_repo 承担。
- 归档仅写 shipments.admin_archived_at（后台可见性），运单业务数据与订单链路不受影响。
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from forge.infrastructure.persistence.models import ORMOrder, ORMShipment


class SQLAlchemyAdminShipmentRepository:
    """后台运单仓储：分页列表 + 归档（软删除）。"""

    @staticmethod
    def _now() -> datetime:
        # 列类型为 TIMESTAMP WITHOUT TIME ZONE，统一写 naive UTC，避免 aware/naive 混用
        return datetime.now(UTC).replace(tzinfo=None)

    @staticmethod
    def to_dict(shipment: ORMShipment, *, order_number: str | None = None) -> dict[str, Any]:
        return {
            "id": str(shipment.id),
            "order_id": str(shipment.order_id),
            "order_number": order_number,
            "supplier_id": shipment.supplier_id,
            "carrier": shipment.carrier,
            "tracking_number": shipment.tracking_number,
            "tracking_url": shipment.tracking_url,
            "status": shipment.status,
            "origin": shipment.origin,
            "destination": shipment.destination,
            "estimated_delivery": shipment.estimated_delivery.isoformat() if shipment.estimated_delivery else None,
            "actual_delivery": shipment.actual_delivery.isoformat() if shipment.actual_delivery else None,
            "notes": shipment.notes,
            "created_at": shipment.created_at.isoformat() if shipment.created_at else None,
            "updated_at": shipment.updated_at.isoformat() if shipment.updated_at else None,
        }

    @staticmethod
    async def _order_number_map(db: AsyncSession, order_ids: list[Any]) -> dict[str, str]:
        ids = [oid for oid in order_ids if oid is not None]
        if not ids:
            return {}
        rows = await db.execute(select(ORMOrder.id, ORMOrder.order_number).where(ORMOrder.id.in_(ids)))
        return {str(oid): str(number) for oid, number in rows.all()}

    @staticmethod
    async def list_admin_shipments(
        db: AsyncSession,
        *,
        status: str | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
        archived: bool = False,
    ) -> dict[str, Any]:
        """后台运单分页列表（默认剔除已归档；archived=True 时只列已归档），支持状态与关键词筛选。"""
        conditions: list[Any] = [
            ORMShipment.admin_archived_at.is_not(None) if archived else ORMShipment.admin_archived_at.is_(None)
        ]
        if status:
            conditions.append(ORMShipment.status == status)
        if keyword:
            like = f"%{keyword.strip()}%"
            conditions.append(
                or_(
                    ORMShipment.tracking_number.ilike(like),
                    ORMShipment.carrier.ilike(like),
                    ORMShipment.supplier_id.ilike(like),
                    ORMShipment.order_id.in_(select(ORMOrder.id).where(ORMOrder.order_number.ilike(like))),
                )
            )
        total = int(await db.scalar(select(func.count()).select_from(ORMShipment).where(*conditions)) or 0)
        rows = (
            await db.scalars(
                select(ORMShipment)
                .where(*conditions)
                .order_by(ORMShipment.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
        numbers = await SQLAlchemyAdminShipmentRepository._order_number_map(db, [r.order_id for r in rows])
        return {
            "items": [
                SQLAlchemyAdminShipmentRepository.to_dict(r, order_number=numbers.get(str(r.order_id))) for r in rows
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @staticmethod
    async def archive_shipments(db: AsyncSession, shipment_ids: list[str]) -> dict[str, Any]:
        """后台归档（软删除）：按运单 ID 批量归档，返回 archived / skipped / missing。"""
        requested = list(dict.fromkeys(str(s) for s in shipment_ids if s))
        if not requested:
            return {"archived": 0, "skipped": 0, "missing": []}
        parsed: dict[str, UUID] = {}
        invalid: list[str] = []
        for raw in requested:
            try:
                uid = UUID(raw)
            except ValueError:
                invalid.append(raw)
                continue
            parsed[str(uid)] = uid
        if not parsed:
            return {"archived": 0, "skipped": 0, "missing": invalid}
        rows = (
            await db.execute(
                select(ORMShipment.id, ORMShipment.admin_archived_at).where(ORMShipment.id.in_(list(parsed.values())))
            )
        ).all()
        archived_at: dict[str, Any] = {str(row[0]): row[1] for row in rows}
        targets = [parsed[key] for key, at in archived_at.items() if at is None]
        if targets:
            now = SQLAlchemyAdminShipmentRepository._now()
            await db.execute(
                update(ORMShipment)
                .where(ORMShipment.id.in_(targets), ORMShipment.admin_archived_at.is_(None))
                .values(admin_archived_at=now, updated_at=now)
            )
        missing = invalid + [key for key in parsed if key not in archived_at]
        return {"archived": len(targets), "skipped": len(archived_at) - len(targets), "missing": missing}

    @staticmethod
    async def unarchive_shipments(db: AsyncSession, shipment_ids: list[str]) -> dict[str, Any]:
        """取消归档（恢复）：按运单 ID 批量清空 admin_archived_at，返回 restored / skipped / missing。"""
        requested = list(dict.fromkeys(str(s) for s in shipment_ids if s))
        if not requested:
            return {"restored": 0, "skipped": 0, "missing": []}
        parsed: dict[str, UUID] = {}
        invalid: list[str] = []
        for raw in requested:
            try:
                uid = UUID(raw)
            except ValueError:
                invalid.append(raw)
                continue
            parsed[str(uid)] = uid
        if not parsed:
            return {"restored": 0, "skipped": 0, "missing": invalid}
        rows = (
            await db.execute(
                select(ORMShipment.id, ORMShipment.admin_archived_at).where(ORMShipment.id.in_(list(parsed.values())))
            )
        ).all()
        archived_at: dict[str, Any] = {str(row[0]): row[1] for row in rows}
        targets = [parsed[key] for key, at in archived_at.items() if at is not None]
        if targets:
            now = SQLAlchemyAdminShipmentRepository._now()
            await db.execute(
                update(ORMShipment)
                .where(ORMShipment.id.in_(targets), ORMShipment.admin_archived_at.is_not(None))
                .values(admin_archived_at=None, updated_at=now)
            )
        missing = invalid + [key for key in parsed if key not in archived_at]
        return {"restored": len(targets), "skipped": len(archived_at) - len(targets), "missing": missing}
