"""Pet profile - SQLAlchemy Repository (C-end pet_profiles)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from forge.infrastructure.persistence.models import ORMPetProfile


def _now() -> datetime:
    # 表列 TIMESTAMP WITHOUT TIME ZONE，须用 naive UTC 赋值，避免 asyncpg aware/naive 混用报错
    return datetime.now(UTC).replace(tzinfo=None)


class SQLAlchemyPetProfileRepository:
    """宠物档案数据库访问封装。"""

    @staticmethod
    async def list_by_owner(db: AsyncSession, owner_id: UUID) -> list[ORMPetProfile]:
        rows = (
            await db.execute(
                select(ORMPetProfile)
                .where(ORMPetProfile.owner_id == owner_id)
                .order_by(ORMPetProfile.created_at.desc())
            )
        ).scalars().all()
        return list(rows)

    @staticmethod
    async def get_by_id(db: AsyncSession, pet_id: UUID) -> ORMPetProfile | None:
        return (
            await db.execute(select(ORMPetProfile).where(ORMPetProfile.id == pet_id))
        ).scalar_one_or_none()

    @staticmethod
    async def create(db: AsyncSession, owner_id: UUID, data: dict[str, Any]) -> ORMPetProfile:
        pet = ORMPetProfile(
            owner_id=owner_id,
            name=data["name"],
            breed=(data.get("breed") or "UNKNOWN").strip() or "UNKNOWN",
            breed_custom=data.get("breed_custom"),
            birthday=data.get("birthday"),
            weight=data.get("weight"),
            gender=(data.get("gender") or "UNKNOWN").strip() or "UNKNOWN",
            spayed_neutered=bool(data.get("spayed_neutered", False)),
            health_notes=data.get("health_notes") or [],
            allergies=data.get("allergies") or [],
            lifecycle=(data.get("lifecycle") or "UNKNOWN").strip() or "UNKNOWN",
        )
        db.add(pet)
        await db.flush()
        await db.refresh(pet)
        return pet

    @staticmethod
    async def update(db: AsyncSession, pet: ORMPetProfile, data: dict[str, Any]) -> ORMPetProfile:
        for key in (
            "name",
            "breed",
            "breed_custom",
            "birthday",
            "weight",
            "gender",
            "spayed_neutered",
            "health_notes",
            "allergies",
            "lifecycle",
        ):
            if key in data and data[key] is not None:
                setattr(pet, key, data[key])
        pet.updated_at = _now()  # type: ignore[assignment]
        await db.flush()
        await db.refresh(pet)
        return pet

    @staticmethod
    async def delete(db: AsyncSession, pet: ORMPetProfile) -> None:
        await db.delete(pet)
        await db.flush()
