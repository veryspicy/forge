import typing
from collections.abc import AsyncIterator, Awaitable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import cast

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
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

from forge.api.errors import register_error_handlers  # noqa: E402

register_error_handlers(app)


async def _product_validation_handler(request: Request, exc: Exception) -> JSONResponse:
    """ProductValidationError -> 400 with field-level errors (never 500)."""
    pve = cast("ProductValidationError", exc)
    errors = [
        {"field": field, "code": "VALIDATION_ERROR", "message": message}
        for field, message in pve.errors.items()
    ]
    return JSONResponse(
        status_code=400,
        content={"code": "BAD_REQUEST", "message": "Bad request.", "status": 400, "errors": errors},
    )


try:
    from forge.application.services.product_service import ProductValidationError

    app.add_exception_handler(ProductValidationError, _product_validation_handler)
except ImportError:
    pass

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


@app.middleware("http")
async def _uploads_signature_gate(
    request: Request, call_next: typing.Callable[[Request], Awaitable[Response]]
) -> Response:
    """P3 signed-URL gate for /uploads/** (local-storage fallback path).

    /minio/** is gated inside minio_proxy.py; this middleware covers the
    StaticFiles mount so both protected media paths share the same policy.
    """
    if request.url.path.startswith("/uploads/"):
        from forge.infrastructure.services.url_signer import verify_url

        if not verify_url(
            request.url.path,
            exp=request.query_params.get("exp"),
            sig=request.query_params.get("sig"),
        ):
            return Response(status_code=403, content="forbidden: missing or invalid signature")
    return await call_next(request)

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
    from forge.api.v1.products import router as public_products_router

    app.include_router(public_products_router, prefix="/api/v1")
except ImportError:
    pass

try:
    from forge.api.v1.pets import router as public_pets_router

    app.include_router(public_pets_router, prefix="/api/v1")
except ImportError:
    pass

try:
    from forge.api.v1.cart import router as public_cart_router

    app.include_router(public_cart_router, prefix="/api/v1")
except ImportError:
    pass

try:
    from forge.api.v1.orders import router as public_orders_router

    app.include_router(public_orders_router, prefix="/api/v1")
except ImportError:
    pass

try:
    from forge.api.v1.reviews import public_reviews_router as public_product_reviews_router
    from forge.api.v1.reviews import router as public_reviews_router

    app.include_router(public_reviews_router, prefix="/api/v1")
    app.include_router(public_product_reviews_router, prefix="/api/v1")
except ImportError:
    pass

try:
    from forge.api.v1.returns import router as public_returns_router

    app.include_router(public_returns_router, prefix="/api/v1")
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
