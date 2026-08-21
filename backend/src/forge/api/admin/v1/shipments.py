from fastapi import APIRouter, Depends

from forge.main.rbac import require_permission

router = APIRouter()


@router.get("/")
async def list_shipments(admin: dict = Depends(require_permission("shipments", "view"))):
    return {"items": [], "total": 0}
