from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

_UPLOADS_DIR = Path(__file__).resolve().parents[3] / "uploads"
_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Startup
    try:
        from forge.main.scheduler import start_scheduler

        start_scheduler()
    except ImportError:
        pass
    yield
    # Shutdown
    try:
        from forge.main.scheduler import stop_scheduler

        stop_scheduler()
    except ImportError:
        pass


app = FastAPI(
    title="Forge Backend",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount(
    "/uploads",
    StaticFiles(directory=str(_UPLOADS_DIR), check_dir=False),
    name="uploads",
)

try:
    from forge.api.minio_proxy import minio_router

    app.include_router(minio_router)
except ImportError:
    pass


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "healthy", "version": "0.1.0"}


# Include routers
try:
    from forge.api.admin.v1.router import admin_router

    app.include_router(admin_router)
except ImportError:
    pass

try:
    from forge.api.v1.auth import router as public_auth_router

    app.include_router(public_auth_router, prefix="/api/v1")
except ImportError:
    pass

try:
    from forge.api.v1.site_profile import router as public_site_profile_router

    app.include_router(public_site_profile_router, prefix="/api/v1")
except ImportError:
    pass

try:
    from forge.api.admin.v1.routes import router as routes_router

    app.include_router(routes_router)
except ImportError:
    pass

# 对外 MCP Server（P3）：/mcp/sse + /mcp/messages/
try:
    from forge.mcp import build_mcp_app

    app.mount("/mcp", build_mcp_app(), name="mcp")
except ImportError:
    pass
