from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from forge.application.services.app_settings_service import get_all_settings, set_setting
from forge.main.dependencies import get_db
from forge.main.rbac import require_permission

router = APIRouter()


class SettingUpdate(BaseModel):
    value: Any


@router.get("/")
async def get_settings(
    admin: dict[str, object] = Depends(require_permission("settings", "manage")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    return await get_all_settings(db)


@router.put("/{key}")
async def put_setting(
    key: str,
    payload: SettingUpdate,
    admin: dict[str, object] = Depends(require_permission("settings", "manage")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if not key or not all(c.isalnum() or c == "_" for c in key):
        raise HTTPException(status_code=400, detail="非法的配置键")
    updated_by = str(admin.get("sub") or admin.get("email") or admin.get("username") or "admin")
    await set_setting(db, key, payload.value, updated_by=updated_by)
    await db.commit()
    return {"key": key, "value": payload.value}
