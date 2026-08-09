from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_chat_requests():
    return {"items": [], "total": 0}
