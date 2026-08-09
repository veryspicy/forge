from fastapi import APIRouter

router = APIRouter()


@router.get("/config")
async def get_site_config():
    return {}
