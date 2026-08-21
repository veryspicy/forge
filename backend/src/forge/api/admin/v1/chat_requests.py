from fastapi import APIRouter, Depends

from forge.main.rbac import require_permission

router = APIRouter()


@router.get("/")
async def list_chat_requests(admin: dict = Depends(require_permission("chat_requests", "view"))):
    return {"items": [], "total": 0}
