from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_admin_users():
    return {"items": [], "total": 0}
