from fastapi import APIRouter

router = APIRouter()
site_router = APIRouter()


@router.get("/")
async def list_site_profiles():
    return {"items": [], "total": 0}


@site_router.get("/site")
async def get_site():
    return {}
