"""Admin - Roles API（DB 权威 RBAC）。"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from forge.infrastructure.persistence.models import ORMPermission, ORMRole
from forge.main.dependencies import get_db
from forge.main.rbac import require_permission

router = APIRouter()


class RoleCreate(BaseModel):
    name: str
    display_name: str
    description: str | None = None
    permission_ids: list[str] = []


class RoleUpdate(BaseModel):
    display_name: str | None = None
    description: str | None = None
    permission_ids: list[str] | None = None


def _permission_dict(p: ORMPermission) -> dict[str, object]:
    return {
        "id": str(p.id),
        "code": p.code,
        "display_name": p.display_name,
        "module": p.module,
    }


def _role_dict(r: ORMRole) -> dict[str, object]:
    return {
        "id": str(r.id),
        "name": r.name,
        "display_name": r.display_name,
        "description": r.description,
        "is_system": r.is_system,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "permissions": [_permission_dict(p) for p in r.permissions],
    }


async def _load_permissions(db: AsyncSession, permission_ids: list[str]) -> list[ORMPermission]:
    if not permission_ids:
        return []
    uuids = [UUID(p) for p in permission_ids]
    rows = (await db.execute(select(ORMPermission).where(ORMPermission.id.in_(uuids)))).scalars().all()
    if len(rows) != len(set(uuids)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="INVALID_PERMISSION_IDS",
        )
    return list(rows)


@router.get("/permissions")
async def list_permissions(
    admin: dict[str, object] = Depends(require_permission("admin_roles", "manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict[str, object]:
    rows = (await db.execute(select(ORMPermission).order_by(ORMPermission.module, ORMPermission.code))).scalars().all()
    return {"permissions": [_permission_dict(p) for p in rows]}


@router.get("/")
async def list_roles(
    admin: dict[str, object] = Depends(require_permission("admin_roles", "manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict[str, object]:
    total_query = select(func.count(ORMRole.id))
    total = (await db.execute(total_query)).scalar_one()

    query = select(ORMRole).options(selectinload(ORMRole.permissions)).order_by(ORMRole.created_at.desc())
    result = await db.execute(query)
    roles = result.scalars().all()

    return {
        "items": [_role_dict(r) for r in roles],
        "total": total,
    }


@router.post("/")
async def create_role(
    body: RoleCreate,
    admin: dict[str, object] = Depends(require_permission("admin_roles", "manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict[str, object]:
    exists = (await db.execute(select(ORMRole).where(ORMRole.name == body.name))).scalar_one_or_none()
    if exists is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ROLE_NAME_EXISTS",
        )

    role = ORMRole(
        name=body.name,
        display_name=body.display_name,
        description=body.description,
        is_system=False,
    )
    role.permissions = await _load_permissions(db, body.permission_ids)
    db.add(role)
    await db.flush()

    fresh = (
        await db.execute(select(ORMRole).where(ORMRole.id == role.id).options(selectinload(ORMRole.permissions)))
    ).scalar_one()
    return _role_dict(fresh)


@router.put("/{role_id}")
async def update_role(
    role_id: UUID,
    body: RoleUpdate,
    admin: dict[str, object] = Depends(require_permission("admin_roles", "manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict[str, object]:
    role = (
        await db.execute(select(ORMRole).where(ORMRole.id == role_id).options(selectinload(ORMRole.permissions)))
    ).scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ROLE_NOT_FOUND")

    if role.name == "super_admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SUPER_ADMIN_ROLE_FIXED",
        )

    if body.display_name is not None:
        role.display_name = body.display_name
    if body.description is not None:
        role.description = body.description
    if body.permission_ids is not None:
        role.permissions = await _load_permissions(db, body.permission_ids)
    await db.flush()
    return _role_dict(role)


@router.delete("/{role_id}")
async def delete_role(
    role_id: UUID,
    admin: dict[str, object] = Depends(require_permission("admin_roles", "manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict[str, object]:
    role = (await db.execute(select(ORMRole).where(ORMRole.id == role_id))).scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ROLE_NOT_FOUND")
    if role.is_system or role.name == "super_admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SYSTEM_ROLE_PROTECTED",
        )
    await db.delete(role)
    await db.flush()
    return {"ok": True}
