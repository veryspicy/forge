"""C-end Auth API — login / register / me."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from forge.infrastructure.persistence.models import ORMUser
from forge.infrastructure.persistence.repositories.user_repo import SQLAlchemyUserRepository
from forge.main.config import settings
from forge.main.dependencies import get_db

router = APIRouter(tags=["C-end Auth"])

security_scheme = HTTPBearer(auto_error=False)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    user: dict


class MeResponse(BaseModel):
    user_id: str
    email: str
    name: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_token(email: str, role: str) -> tuple[str, dict]:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": email,
        "role": role,
        "iat": now,
        "exp": expire,
    }
    token = jwt.encode(payload, settings.secret_key, algorithm="HS256")
    return token, payload


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
) -> dict:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先登录")
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.secret_key,
            algorithms=["HS256"],
        )
        return {"sub": payload.get("sub", ""), "role": payload.get("role", "customer")}
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已过期，请重新登录")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/auth/login", response_model=AuthResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    repo = SQLAlchemyUserRepository()
    user: ORMUser | None = await repo.get_by_email(db, body.email)
    if user is None or not pwd_context.verify(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号或密码不正确")
    token, _ = _create_token(user.email, user.role)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": str(user.id),
        "user": {
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "role": user.role,
        },
    }


@router.post("/auth/register", response_model=AuthResponse)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    repo = SQLAlchemyUserRepository()
    existing = await repo.get_by_email(db, body.email)
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    password_hash = pwd_context.hash(body.password)
    user: ORMUser = await repo.create(db, body.email, password_hash, body.name)
    # commit is handled by get_db dependency; flush + refresh to get full row
    await db.flush()
    await db.refresh(user)

    token, _ = _create_token(user.email, user.role)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": str(user.id),
        "user": {
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "role": user.role,
        },
    }


@router.get("/auth/me", response_model=MeResponse)
async def me(
    user_claims: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    email = user_claims.get("sub", "")
    repo = SQLAlchemyUserRepository()
    user: ORMUser | None = await repo.get_by_email(db, email)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    return {"user_id": str(user.id), "email": user.email, "name": user.name}
