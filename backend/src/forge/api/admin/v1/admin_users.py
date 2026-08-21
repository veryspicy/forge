"""Admin - Admin Users API（多对多角色分配）。"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from forge.infrastructure.persistence.models import ORMAdminUser, ORMRole
from forge.infrastructure.persistence.repositories.user_repo import SQLAlchemyAdminUserRepository
from forge.main.dependencies import get_db
from forge.main.rbac import require_permission

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AdminUserCreate(BaseModel):
    email: str
    password: str
    display_name: str
    is_active: bool = True
    role_ids: list[str] = []


class AdminUserUpdate(BaseModel):
    display_name: str | None = None
    is_active: bool | None = None
    password: str | None = None


class RoleAssign(BaseModel):
    role_ids: list[str]


def _admin_dict(u: ORMAdminUser) -> dict[str, object]:
    return {
        "id": str(u.id),
        "email": u.email,
        "display_name": u.display_name,
        "role": u.role,
        "roles": [{"id": str(r.id), "name": r.name, "display_name": r.display_name} for r in u.roles],
        "is_active": u.is_active,
        "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }


async def _load_roles(db: AsyncSession, role_ids: list[str]) -> list[ORMRole]:
    if not role_ids:
        return []
    uuids = [UUID(r) for r in role_ids]
    rows = (await db.execute(select(ORMRole).where(ORMRole.id.in_(uuids)))).scalars().all()
    if len(rows) != len(set(uuids)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="INVALID_ROLE_IDS",
        )
    return list(rows)


@router.get("/")
async def list_admin_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: dict[str, object] = Depends(require_permission("admin_users", "manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict[str, object]:
    repo = SQLAlchemyAdminUserRepository()
    result: dict[str, object] = await repo.list_admin_users(db, page=page, page_size=page_size)
    return result


@router.post("/")
async def create_admin_user(
    body: AdminUserCreate,
    admin: dict[str, object] = Depends(require_permission("admin_users", "manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict[str, object]:
    repo = SQLAlchemyAdminUserRepository()
    existing = await repo.get_by_email(db, body.email)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="EMAIL_EXISTS",
        )

    roles = await _load_roles(db, body.role_ids)
    admin_user = ORMAdminUser(
        email=body.email,
        password_hash=pwd_context.hash(body.password),
        display_name=body.display_name,
        role=roles[0].name if roles else "user",
        is_active=body.is_active,
    )
    admin_user.roles = roles
    db.add(admin_user)
    await db.flush()

    fresh = (
        await db.execute(
            select(ORMAdminUser).where(ORMAdminUser.id == admin_user.id).options(selectinload(ORMAdminUser.roles))
        )
    ).scalar_one()
    return _admin_dict(fresh)


@router.put("/{user_id}")
async def update_admin_user(
    user_id: UUID,
    body: AdminUserUpdate,
    admin: dict[str, object] = Depends(require_permission("admin_users", "manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict[str, object]:
    user = (
        await db.execute(
            select(ORMAdminUser).where(ORMAdminUser.id == user_id).options(selectinload(ORMAdminUser.roles))
        )
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ADMIN_USER_NOT_FOUND")

    if str(user.id) == admin.get("user_id") and body.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CANNOT_DISABLE_SELF",
        )
    if "super_admin" in [r.name for r in user.roles] and body.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SUPER_ADMIN_CANNOT_DISABLE",
        )

    if body.display_name is not None:
        user.display_name = body.display_name
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.password:
        user.password_hash = pwd_context.hash(body.password)
    await db.flush()
    return _admin_dict(user)


@router.put("/{user_id}/roles")
async def assign_roles(
    user_id: UUID,
    body: RoleAssign,
    admin: dict[str, object] = Depends(require_permission("admin_users", "manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict[str, object]:
    user = (
        await db.execute(
            select(ORMAdminUser).where(ORMAdminUser.id == user_id).options(selectinload(ORMAdminUser.roles))
        )
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ADMIN_USER_NOT_FOUND")

    roles = await _load_roles(db, body.role_ids)
    user.roles = roles
    user.role = roles[0].name if roles else "user"
    await db.flush()
    return _admin_dict(user)


@router.delete("/{user_id}")
async def delete_admin_user(
    user_id: UUID,
    admin: dict[str, object] = Depends(require_permission("admin_users", "manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict[str, object]:
    user = (
        await db.execute(
            select(ORMAdminUser).where(ORMAdminUser.id == user_id).options(selectinload(ORMAdminUser.roles))
        )
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ADMIN_USER_NOT_FOUND")

    if str(user.id) == admin.get("user_id"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CANNOT_DELETE_SELF",
        )
    if "super_admin" in [r.name for r in user.roles]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SUPER_ADMIN_PROTECTED",
        )
    await db.delete(user)
    await db.flush()
    return {"ok": True}
