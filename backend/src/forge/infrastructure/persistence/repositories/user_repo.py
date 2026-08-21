"""User & Admin User — SQLAlchemy Repository."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from forge.infrastructure.persistence.models import ORMAdminUser, ORMUser


class SQLAlchemyUserRepository:
    """C-end 用户数据库访问封装。"""

    @staticmethod
    async def get_by_email(db: AsyncSession, email: str) -> ORMUser | None:
        stmt = select(ORMUser).where(ORMUser.email == email)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def create(db: AsyncSession, email: str, password_hash: str, name: str) -> ORMUser:
        user = ORMUser(
            email=email,
            password_hash=password_hash,
            name=name,
            role="customer",
        )
        db.add(user)
        await db.flush()
        return user

    @staticmethod
    async def list_users(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        total_query = select(func.count(ORMUser.id))
        total = (await db.execute(total_query)).scalar_one()

        query = select(ORMUser).order_by(ORMUser.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(query)
        users = result.scalars().all()

        return {
            "items": [
                {
                    "id": str(u.id),
                    "email": u.email,
                    "name": u.name,
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
    ) -> dict:
        total_query = select(func.count(ORMAdminUser.id))
        total = (await db.execute(total_query)).scalar_one()

        query = (
            select(ORMAdminUser)
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
