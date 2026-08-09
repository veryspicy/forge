"""Admin Auth API — login / me / logout."""

from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from jose import jwt

from forge.main.config import settings
from forge.main.dependencies import get_current_admin

router = APIRouter()

# Hardcoded dev admin account
DEV_ADMIN = {
    "email": "admin@forge.com",
    "password": "admin123",
    "name": "Super Admin",
    "role": "super_admin",
}


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
def login(body: LoginRequest):
    if body.email != DEV_ADMIN["email"] or body.password != DEV_ADMIN["password"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="账号或密码不正确",
        )
    payload = {
        "sub": DEV_ADMIN["email"],
        "role": DEV_ADMIN["role"],
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes),
    }
    token = jwt.encode(payload, settings.secret_key, algorithm="HS256")
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "user_id": DEV_ADMIN["email"],
            "email": DEV_ADMIN["email"],
            "name": DEV_ADMIN["name"],
            "role": DEV_ADMIN["role"],
        },
    }


@router.get("/me", response_model=UserInfo)
def me(admin: dict = Depends(get_current_admin)):
    if not admin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先登录")
    return {
        "id": admin.get("sub", ""),
        "email": admin.get("sub", ""),
        "name": "Super Admin",
        "roles": [admin.get("role", "user")],
        "permissions": ["*"],
    }
