from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from forge.api.errors import APIError, ErrorCode
from forge.infrastructure.persistence.repositories.shipment_repo import SQLAlchemyAdminShipmentRepository
from forge.main.dependencies import get_db
from forge.main.rbac import require_permission

router = APIRouter()


class AdminShipmentArchiveRequest(BaseModel):
    """批量归档（软删除）运单入参；单次上限 200，与订单/售后归档口径一致。"""

    model_config = ConfigDict(extra="forbid")

    shipment_ids: list[str] = Field(default_factory=list, max_length=200)


@router.get("/")
async def list_shipments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(default=None, alias="status"),
    keyword: str | None = Query(default=None, max_length=200),
    admin: dict[str, object] = Depends(require_permission("shipments", "view")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    """后台运单分页列表（默认剔除已归档），支持状态与关键词（运单号/承运商/订单号）筛选。"""
    repo = SQLAlchemyAdminShipmentRepository()
    return await repo.list_admin_shipments(
        db,
        status=status.strip().lower() if status and status.strip() else None,
        keyword=keyword.strip() if keyword and keyword.strip() else None,
        page=page,
        page_size=page_size,
    )


@router.post("/archive")
async def archive_shipments(
    payload: AdminShipmentArchiveRequest,
    admin: dict[str, object] = Depends(require_permission("shipments", "archive")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    """批量归档（软删除）运单：从后台列表中隐去，不物理删除，可逆。"""
    ids = [s.strip() for s in payload.shipment_ids if s and s.strip()]
    if not ids:
        raise APIError(ErrorCode.VALIDATION_ERROR, message="shipment_ids cannot be empty.")
    repo = SQLAlchemyAdminShipmentRepository()
    return await repo.archive_shipments(db, ids)


@router.delete("/{shipment_id}")
async def archive_shipment(
    shipment_id: str,
    admin: dict[str, object] = Depends(require_permission("shipments", "archive")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    """单条归档（软删除）运单；运单不存在时返回 404。"""
    repo = SQLAlchemyAdminShipmentRepository()
    result = await repo.archive_shipments(db, [shipment_id])
    if result["archived"] == 0 and result["missing"]:
        raise APIError(ErrorCode.INVALID_ID, message="Shipment does not exist.")
    return result
