"""C-end Auth API — login / register / me."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from forge.api.errors import APIError, ErrorCode
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
    user: dict[str, object]


class MeResponse(BaseModel):
    user_id: str
    email: str
    name: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_token(email: str, role: str) -> tuple[str, dict[str, object]]:
    now = datetime.now(UTC)
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
) -> dict[str, object]:
    if credentials is None:
        raise APIError(code=ErrorCode.UNAUTHORIZED)
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.secret_key,
            algorithms=["HS256"],
        )
        return {"sub": payload.get("sub", ""), "role": payload.get("role", "customer")}
    except JWTError:
        raise APIError(code=ErrorCode.TOKEN_EXPIRED) from None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/auth/login", response_model=AuthResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)) -> dict[str, object]:
    repo = SQLAlchemyUserRepository()
    user: ORMUser | None = await repo.get_by_email(db, body.email)
    if user is None or not pwd_context.verify(body.password, user.password_hash):
        raise APIError(code=ErrorCode.INVALID_CREDENTIALS)
    token, _ = _create_token(str(user.email), str(user.role))
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
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)) -> dict[str, object]:
    repo = SQLAlchemyUserRepository()
    existing = await repo.get_by_email(db, body.email)
    if existing is not None:
        raise APIError(code=ErrorCode.EMAIL_ALREADY_REGISTERED)

    password_hash = pwd_context.hash(body.password)
    user: ORMUser = await repo.create(db, body.email, password_hash, body.name)
    # commit is handled by get_db dependency; flush + refresh to get full row
    await db.flush()
    await db.refresh(user)

    token, _ = _create_token(str(user.email), str(user.role))
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
    user_claims: dict[str, object] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    email = user_claims.get("sub", "")
    repo = SQLAlchemyUserRepository()
    user: ORMUser | None = await repo.get_by_email(db, email)  # type: ignore[arg-type]
    if user is None:
        raise APIError(code=ErrorCode.USER_NOT_FOUND)
    return {"user_id": str(user.id), "email": user.email, "name": user.name}
