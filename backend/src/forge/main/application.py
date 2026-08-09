from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from forge.main.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown


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


@app.get("/health")
async def health_check():
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
    from forge.api.v1.diy import router as public_diy_router

    app.include_router(public_diy_router, prefix="/api/v1")
except ImportError:
    pass

try:
    from forge.api.admin.v1.routes import router as routes_router

    app.include_router(routes_router)
except ImportError:
    pass
