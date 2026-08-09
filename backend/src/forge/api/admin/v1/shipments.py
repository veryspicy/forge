from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_shipments():
    return {"items": [], "total": 0}
