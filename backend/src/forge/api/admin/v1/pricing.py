from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_pricing():
    return {"items": [], "total": 0}
