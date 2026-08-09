from fastapi import APIRouter, Depends
from forge.main.dependencies import get_current_admin

router = APIRouter()


@router.get("/")
async def get_dashboard(admin: dict = Depends(get_current_admin)):
    return {
        "total_orders": 0,
        "total_revenue": 0,
        "total_users": 0,
        "total_products": 0,
        "recent_orders": [],
        "order_trend": [],
    }
