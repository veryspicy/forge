from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_roles():
    return {"items": [], "total": 0}
