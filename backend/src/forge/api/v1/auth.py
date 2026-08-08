"""C-end Auth API — login / register / me."""

from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from jose import JWTError, jwt

from forge.main.config import settings

router = APIRouter(tags=["C-end Auth"])

security_scheme = HTTPBearer(auto_error=False)

# In-memory user store (dev mode)
_users: dict[str, dict] = {
    "test@forge.com": {
        "id": 1,
        "email": "test@forge.com",
        "password": "test123",
        "name": "Test User",
        "role": "customer",
    },
}


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
    user_id: int
    user: dict


class MeResponse(BaseModel):
    user_id: int
    email: str
    name: str


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


@router.post("/auth/login", response_model=AuthResponse)
def login(body: LoginRequest):
    user = _users.get(body.email)
    if not user or user["password"] != body.password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号或密码不正确")
    token, _ = _create_token(user["email"], user["role"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user["id"],
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "role": user["role"],
        },
    }


@router.post("/auth/register", response_model=AuthResponse)
def register(body: RegisterRequest):
    if body.email in _users:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user_id = max((u["id"] for u in _users.values()), default=0) + 1
    user = {
        "id": user_id,
        "email": body.email,
        "password": body.password,
        "name": body.name,
        "role": "customer",
    }
    _users[body.email] = user
    token, _ = _create_token(user["email"], user["role"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user["id"],
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "role": user["role"],
        },
    }


@router.get("/auth/me", response_model=MeResponse)
def me(user: dict = Depends(get_current_user)):
    email = user.get("sub", "")
    stored = _users.get(email)
    name = stored["name"] if stored else email
    user_id = stored["id"] if stored else 0
    return {"user_id": user_id, "email": email, "name": name}
