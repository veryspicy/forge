from fastapi import APIRouter, Depends
from forge.main.dependencies import get_current_admin

router = APIRouter()


@router.get("/")
async def list_orders(admin: dict = Depends(get_current_admin)):
    return {"items": [], "total": 0}


@router.get("/{order_id}")
async def get_order(order_id: str, admin: dict = Depends(get_current_admin)):
    return {"id": order_id}
