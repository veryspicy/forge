from fastapi import APIRouter, Depends

from forge.main.rbac import require_permission

router = APIRouter()


@router.get("/")
async def list_shipments(
    admin: dict[str, object] = Depends(require_permission("shipments", "view")),
) -> dict[str, object]:
    return {"items": [], "total": 0}
