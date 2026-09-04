"""User & Admin User — SQLAlchemy Repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from forge.infrastructure.persistence.models import ORMAdminUser, ORMOrder, ORMPetProfile, ORMUser


class SQLAlchemyUserRepository:
    """C-end 用户数据库访问封装。"""

    @staticmethod
    async def get_by_email(db: AsyncSession, email: str) -> ORMUser | None:
        stmt = select(ORMUser).where(ORMUser.email == email)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_id(db: AsyncSession, user_id: UUID) -> ORMUser | None:
        stmt = select(ORMUser).where(ORMUser.id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def create(
        db: AsyncSession,
        email: str,
        password_hash: str,
        name: str,
        phone: str | None = None,
        is_active: bool = True,
    ) -> ORMUser:
        user = ORMUser(
            email=email,
            password_hash=password_hash,
            name=name,
            phone=phone,
            role="customer",
            is_active=is_active,
        )
        db.add(user)
        await db.flush()
        return user

    @staticmethod
    async def list_users(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        keyword: str | None = None,
        status: str | None = None,
    ) -> dict[str, object]:
        filters = []
        if keyword:
            kw = f"%{keyword.strip()}%"
            filters.append(or_(ORMUser.email.ilike(kw), ORMUser.name.ilike(kw), ORMUser.phone.ilike(kw)))
        if status == "active":
            filters.append(ORMUser.is_active.is_(True))
        elif status == "disabled":
            filters.append(ORMUser.is_active.is_(False))

        total_query = select(func.count(ORMUser.id)).where(*filters)
        total = (await db.execute(total_query)).scalar_one()

        query = (
            select(ORMUser)
            .where(*filters)
            .order_by(ORMUser.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(query)
        users = result.scalars().all()

        return {
            "items": [
                {
                    "id": str(u.id),
                    "email": u.email,
                    "name": u.name,
                    "phone": u.phone,
                    "role": u.role,
                    "is_active": u.is_active,
                    "created_at": u.created_at.isoformat() if u.created_at else None,
                }
                for u in users
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @staticmethod
    async def business_counts(db: AsyncSession, user_id: UUID) -> dict[str, int]:
        """客户业务数据计数（订单 / 宠物档案），用于删除保护与详情聚合。"""
        order_total = (
            await db.execute(select(func.count(ORMOrder.id)).where(ORMOrder.user_id == user_id))
        ).scalar_one()
        pet_total = (
            await db.execute(select(func.count(ORMPetProfile.id)).where(ORMPetProfile.owner_id == user_id))
        ).scalar_one()
        return {"orders": order_total, "pets": pet_total}

    @staticmethod
    async def list_pets_by_owner(db: AsyncSession, owner_id: UUID) -> list[ORMPetProfile]:
        stmt = select(ORMPetProfile).where(ORMPetProfile.owner_id == owner_id).order_by(ORMPetProfile.created_at.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def list_recent_orders(db: AsyncSession, user_id: UUID, limit: int = 5) -> list[ORMOrder]:
        stmt = select(ORMOrder).where(ORMOrder.user_id == user_id).order_by(ORMOrder.created_at.desc()).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def count(db: AsyncSession) -> int:
        result = await db.execute(select(func.count(ORMUser.id)))
        return result.scalar_one()


class SQLAlchemyAdminUserRepository:
    """Admin 用户数据库访问封装。"""

    @staticmethod
    async def get_by_email(db: AsyncSession, email: str) -> ORMAdminUser | None:
        stmt = select(ORMAdminUser).where(ORMAdminUser.email == email)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_admin_users(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, object]:
        total_query = select(func.count(ORMAdminUser.id))
        total = (await db.execute(total_query)).scalar_one()

        query = (
            select(ORMAdminUser)
            .options(selectinload(ORMAdminUser.roles))
            .order_by(ORMAdminUser.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(query)
        users = result.scalars().all()

        return {
            "items": [
                {
                    "id": str(u.id),
                    "email": u.email,
                    "display_name": u.display_name,
                    "role": u.role,
                    "roles": [{"id": str(r.id), "name": r.name, "display_name": r.display_name} for r in u.roles],
                    "is_active": u.is_active,
                    "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
                    "created_at": u.created_at.isoformat() if u.created_at else None,
                }
                for u in users
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
