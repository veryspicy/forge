from collections.abc import AsyncGenerator
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from forge.infrastructure.persistence.models import ORMAdminUser
from forge.main.config import settings

engine = create_async_engine(settings.database_url, echo=settings.debug)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

security_scheme = HTTPBearer(auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),  # noqa: B008 — FastAPI 依赖标准写法
    db: AsyncSession = Depends(get_db),  # noqa: B008 — FastAPI 依赖标准写法
) -> dict[str, Any]:
    """校验 JWT 并返回当前管理员 claims。

    - 无 token / 无效 token → 401
    - 账号不存在或已禁用 → 401
    - role 以 admin_users.role 为准（不信任 token 中的 role）
    """
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="UNAUTHORIZED")
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.secret_key,
            algorithms=["HS256"],
        )
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from None

    email = payload.get("sub", "")
    admin = (await db.execute(select(ORMAdminUser).where(ORMAdminUser.email == email))).scalar_one_or_none()
    if admin is None or not admin.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="UNAUTHORIZED")

    return {
        "sub": admin.email,
        "user_id": str(admin.id),
        "role": admin.role,
    }
