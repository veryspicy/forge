from fastapi import APIRouter, Depends
from forge.main.dependencies import get_current_admin

router = APIRouter()


@router.get("/")
async def list_products(admin: dict = Depends(get_current_admin)):
    return {"items": [], "total": 0}


@router.get("/{product_id}")
async def get_product(product_id: str, admin: dict = Depends(get_current_admin)):
    return {"id": product_id}
