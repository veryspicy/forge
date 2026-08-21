from fastapi import APIRouter, Depends

from forge.main.rbac import require_permission

router = APIRouter()


@router.get("/")
async def get_settings(admin: dict = Depends(require_permission("settings", "manage"))):
    return {}
