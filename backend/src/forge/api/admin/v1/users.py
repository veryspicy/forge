"""Admin - Customers API (C-end users) 管理。

覆盖：列表（搜索/筛选/分页）、详情（宠物 + 订单聚合）、新增（管理员代建）、
编辑、冻结/解冻、密码重置、删除保护（有业务数据禁删仅冻结）。
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from forge.api.errors import APIError, ErrorCode
from forge.infrastructure.persistence.models import ORMOrder, ORMPetProfile, ORMUser
from forge.infrastructure.persistence.repositories.user_repo import SQLAlchemyUserRepository
from forge.main.dependencies import get_db
from forge.main.rbac import require_permission

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class CustomerCreate(BaseModel):
    """管理员代建客户（与 C 端注册同字段语义 + 可选 phone / is_active）。"""

    email: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=6, max_length=128)
    name: str = Field(min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=50)
    is_active: bool = True


class CustomerUpdate(BaseModel):
    email: str | None = Field(default=None, min_length=1, max_length=320)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=50)
    is_active: bool | None = None


class PasswordReset(BaseModel):
    password: str = Field(min_length=6, max_length=128)


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------


def _user_dict(u: ORMUser) -> dict[str, object]:
    return {
        "id": str(u.id),
        "email": u.email,
        "name": u.name,
        "phone": u.phone,
        "role": u.role,
        "is_active": u.is_active,
        "created_at": u.created_at.isoformat() if u.created_at else None,
        "updated_at": u.updated_at.isoformat() if u.updated_at else None,
    }


def _pet_dict(p: ORMPetProfile) -> dict[str, object]:
    return {
        "id": str(p.id),
        "name": p.name,
        "breed": p.breed,
        "breed_custom": p.breed_custom,
        "birthday": p.birthday.isoformat() if p.birthday else None,
        "weight": p.weight,
        "gender": p.gender,
        "lifecycle": p.lifecycle,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


def _order_dict(o: ORMOrder) -> dict[str, object]:
    return {
        "id": str(o.id),
        "order_number": o.order_number,
        "total": str(o.total),
        "currency": o.currency,
        "status": o.status,
        "created_at": o.created_at.isoformat() if o.created_at else None,
    }


def _normalize_phone(value: str | None) -> str | None:
    """空串归一为 None，避免空字符串占位。"""
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


async def _load_customer_or_404(db: AsyncSession, user_id: UUID) -> ORMUser:
    repo = SQLAlchemyUserRepository()
    user = await repo.get_by_id(db, user_id)
    if user is None:
        raise APIError(code=ErrorCode.CUSTOMER_NOT_FOUND) from None
    return user


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/")
async def list_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = Query(default=None, max_length=200),
    status: str | None = Query(default=None, pattern="^(active|disabled)$"),
    admin: dict[str, object] = Depends(require_permission("users", "view")),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict[str, object]:
    repo = SQLAlchemyUserRepository()
    result: dict[str, object] = await repo.list_users(
        db, page=page, page_size=page_size, keyword=keyword, status=status
    )
    return result


@router.get("/{user_id}")
async def get_customer_detail(
    user_id: UUID,
    admin: dict[str, object] = Depends(require_permission("users", "view")),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict[str, object]:
    repo = SQLAlchemyUserRepository()
    user = await _load_customer_or_404(db, user_id)
    counts = await repo.business_counts(db, user_id)
    pets = await repo.list_pets_by_owner(db, user_id)
    recent_orders = await repo.list_recent_orders(db, user_id, limit=5)
    return {
        **_user_dict(user),
        "stats": {"orders": counts["orders"], "pets": counts["pets"]},
        "pets": [_pet_dict(p) for p in pets],
        "orders": {
            "total": counts["orders"],
            "recent": [_order_dict(o) for o in recent_orders],
        },
    }


@router.post("/")
async def create_customer(
    body: CustomerCreate,
    admin: dict[str, object] = Depends(require_permission("users", "manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict[str, object]:
    repo = SQLAlchemyUserRepository()
    existing = await repo.get_by_email(db, body.email.strip())
    if existing is not None:
        raise APIError(code=ErrorCode.EMAIL_ALREADY_REGISTERED) from None
    user = await repo.create(
        db,
        email=body.email.strip(),
        password_hash=pwd_context.hash(body.password),
        name=body.name.strip(),
        phone=_normalize_phone(body.phone),
        is_active=body.is_active,
    )
    await db.flush()
    await db.commit()
    await db.refresh(user)
    return _user_dict(user)


@router.put("/{user_id}")
async def update_customer(
    user_id: UUID,
    body: CustomerUpdate,
    admin: dict[str, object] = Depends(require_permission("users", "manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict[str, object]:
    repo = SQLAlchemyUserRepository()
    user = await _load_customer_or_404(db, user_id)

    if body.email is not None:
        email = body.email.strip()
        if email != user.email:
            existing = await repo.get_by_email(db, email)
            if existing is not None and str(existing.id) != str(user.id):
                raise APIError(code=ErrorCode.EMAIL_ALREADY_REGISTERED) from None
        user.email = email  # type: ignore[assignment]
    if body.name is not None:
        user.name = body.name.strip()  # type: ignore[assignment]
    if body.phone is not None:
        user.phone = _normalize_phone(body.phone)  # type: ignore[assignment]
    if body.is_active is not None:
        user.is_active = body.is_active  # type: ignore[assignment]
    await db.flush()
    await db.commit()
    await db.refresh(user)
    return _user_dict(user)


@router.put("/{user_id}/password")
async def reset_customer_password(
    user_id: UUID,
    body: PasswordReset,
    admin: dict[str, object] = Depends(require_permission("users", "manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict[str, object]:
    """首期后台代设密码；后期邮件重置能力在 service 层扩展。"""
    user = await _load_customer_or_404(db, user_id)
    user.password_hash = pwd_context.hash(body.password)
    await db.flush()
    await db.commit()
    return {"ok": True}


@router.delete("/{user_id}")
async def delete_customer(
    user_id: UUID,
    admin: dict[str, object] = Depends(require_permission("users", "manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict[str, object]:
    """有订单 / 宠物档案的客户禁止物理删除，仅可冻结；无业务数据才允许删除。"""
    repo = SQLAlchemyUserRepository()
    user = await _load_customer_or_404(db, user_id)
    counts = await repo.business_counts(db, user_id)
    if counts["orders"] > 0 or counts["pets"] > 0:
        raise APIError(code=ErrorCode.CUSTOMER_CANNOT_DELETE) from None
    await db.delete(user)
    await db.flush()
    await db.commit()
    return {"ok": True}
