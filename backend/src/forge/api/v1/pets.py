"""C-end Pet Profile API - 宠物档案（列表/创建/详情/更新/删除 + 推荐占位）。

- 依赖 C 端 JWT（auth.get_current_user），owner 由 token 内 email 反查 users.id
- 前端契约（portal-web useApi / stores/pet）：
  GET    /pets/                     -> [pet, ...] 裸数组
  POST   /pets/                     -> pet（201）
  GET    /pets/{id}                 -> pet
  PATCH  /pets/{id}                 -> pet（更新后）
  DELETE /pets/{id}                 -> 204
  GET    /pets/{id}/recommendations -> {items: [...]}
"""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Any, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from forge.api.v1.auth import get_current_user
from forge.infrastructure.persistence.models import ORMPetProfile
from forge.infrastructure.persistence.repositories.pet_repo import SQLAlchemyPetProfileRepository
from forge.infrastructure.persistence.repositories.user_repo import SQLAlchemyUserRepository
from forge.main.dependencies import get_db

router = APIRouter(tags=["C-end Pets"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class PetCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = Field(min_length=1, max_length=200)
    breed: str = Field(default="UNKNOWN", max_length=100)
    breed_custom: str | None = Field(default=None, max_length=200)
    birthday: date | None = None
    weight: float | None = Field(default=None, ge=0, le=2000)
    gender: str = Field(default="UNKNOWN", max_length=20)
    spayed_neutered: bool = False
    health_notes: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    lifecycle: str = Field(default="UNKNOWN", max_length=50)


class PetPatch(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str | None = Field(default=None, min_length=1, max_length=200)
    breed: str | None = Field(default=None, max_length=100)
    breed_custom: str | None = Field(default=None, max_length=200)
    birthday: date | None = None
    weight: float | None = Field(default=None, ge=0, le=2000)
    gender: str | None = Field(default=None, max_length=20)
    spayed_neutered: bool | None = None
    health_notes: list[str] | None = None
    allergies: list[str] | None = None
    lifecycle: str | None = Field(default=None, max_length=50)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _current_owner_id(
    claims: dict[str, object],
    db: AsyncSession,
) -> UUID:
    """按 token email 反查 users.id；用户不存在视为未授权。"""
    email = str(claims.get("sub") or "")
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="UNAUTHORIZED")
    user = await SQLAlchemyUserRepository.get_by_email(db, email)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="UNAUTHORIZED")
    return cast(UUID, user.id)


async def _owned_pet_or_404(db: AsyncSession, pet_id: str, owner_id: UUID) -> ORMPetProfile:
    try:
        parsed = UUID(pet_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Pet not found") from None
    pet = await SQLAlchemyPetProfileRepository.get_by_id(db, parsed)
    if pet is None or pet.owner_id != owner_id:
        raise HTTPException(status_code=404, detail="Pet not found")
    return pet


def _to_datetime(value: date | datetime | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    return datetime.combine(value, time.min)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/pets/")
async def list_my_pets(
    user_claims: dict[str, object] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """当前用户的宠物列表（裸数组，匹配前端 store 契约）。"""
    owner_id = await _current_owner_id(user_claims, db)
    pets = await SQLAlchemyPetProfileRepository.list_by_owner(db, owner_id)
    return [p.to_dict() for p in pets]


@router.post("/pets/", status_code=status.HTTP_201_CREATED)
async def create_pet(
    body: PetCreate,
    user_claims: dict[str, object] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """创建宠物档案（owner 取自当前登录用户）。"""
    owner_id = await _current_owner_id(user_claims, db)
    pet = await SQLAlchemyPetProfileRepository.create(
        db,
        owner_id=owner_id,
        data={
            **body.model_dump(),
            "birthday": _to_datetime(body.birthday),
        },
    )
    return pet.to_dict()


@router.get("/pets/{pet_id}")
async def get_pet(
    pet_id: str,
    user_claims: dict[str, object] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    owner_id = await _current_owner_id(user_claims, db)
    pet = await _owned_pet_or_404(db, pet_id, owner_id)
    return pet.to_dict()


@router.patch("/pets/{pet_id}")
async def update_pet(
    pet_id: str,
    body: PetPatch,
    user_claims: dict[str, object] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    owner_id = await _current_owner_id(user_claims, db)
    pet = await _owned_pet_or_404(db, pet_id, owner_id)
    data = body.model_dump(exclude_unset=True)
    if "birthday" in data:
        data["birthday"] = _to_datetime(data["birthday"])
    updated = await SQLAlchemyPetProfileRepository.update(db, pet, data)
    return updated.to_dict()


@router.delete("/pets/{pet_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pet(
    pet_id: str,
    user_claims: dict[str, object] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    owner_id = await _current_owner_id(user_claims, db)
    pet = await _owned_pet_or_404(db, pet_id, owner_id)
    await SQLAlchemyPetProfileRepository.delete(db, pet)
    return None


@router.get("/pets/{pet_id}/recommendations")
async def pet_recommendations(
    pet_id: str,
    user_claims: dict[str, object] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """宠物个性化商品推荐（契约占位，先返回空列表，后续接入 AI 推荐链路）。"""
    owner_id = await _current_owner_id(user_claims, db)
    await _owned_pet_or_404(db, pet_id, owner_id)
    return {"items": []}
