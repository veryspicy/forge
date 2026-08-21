"""Admin Auth API — login / me / logout."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from forge.infrastructure.persistence.models import ORMAdminUser
from forge.infrastructure.persistence.repositories.user_repo import SQLAlchemyAdminUserRepository
from forge.main.config import settings
from forge.main.dependencies import get_current_admin, get_db
from forge.main.rbac import permissions_for

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserInfo(BaseModel):
    id: str
    email: str
    name: str
    roles: list[str]
    permissions: list[str] = []


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    repo = SQLAlchemyAdminUserRepository()
    admin: ORMAdminUser | None = await repo.get_by_email(db, body.email)
    if admin is None or not pwd_context.verify(body.password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="INVALID_CREDENTIALS",
        )
    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ACCOUNT_DISABLED",
        )

    # Update last_login_at
    admin.last_login_at = datetime.now()
    await db.flush()

    payload = {
        "sub": admin.email,
        "role": admin.role,
        "exp": datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes),
    }
    token = jwt.encode(payload, settings.secret_key, algorithm="HS256")
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "user_id": admin.email,
            "email": admin.email,
            "name": admin.display_name,
            "role": admin.role,
        },
    }


@router.get("/me", response_model=UserInfo)
async def me(admin_claims: dict = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    if not admin_claims:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="UNAUTHORIZED")

    email = admin_claims.get("sub", "")
    repo = SQLAlchemyAdminUserRepository()
    admin: ORMAdminUser | None = await repo.get_by_email(db, email)
    if admin is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="USER_NOT_FOUND")

    roles = admin_claims.get("roles") or [admin_claims.get("role", "")]
    return {
        "id": str(admin.id),
        "email": admin.email,
        "name": admin.display_name,
        "roles": roles,
        "permissions": await permissions_for(db, roles),
    }
