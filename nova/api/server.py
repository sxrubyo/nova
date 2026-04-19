"""FastAPI server bootstrap."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from nova.api.middleware import AuthMiddleware, LoggingMiddleware, QuotaMiddleware, RateLimitMiddleware, RequestIDMiddleware
from nova.api.routes import agents, analytics, auth, connectors, discovery, evaluate, gateway, gmail, ledger, realtime, settings, status, webhooks, workspaces
from nova.constants import NOVA_VERSION
from nova.exceptions import NovaException
from nova.kernel import NovaKernel, get_kernel


def _resolve_frontend_dist(app_kernel: NovaKernel, serve_frontend: bool) -> Path | None:
    if not serve_frontend or not app_kernel.config.frontend_enabled:
        return None
    dist_dir = Path(app_kernel.config.frontend_dist_dir)
    index_file = dist_dir / "index.html"
    if not dist_dir.is_dir() or not index_file.is_file():
        return None
    return dist_dir


def create_app(kernel: NovaKernel | None = None, *, serve_frontend: bool = True) -> FastAPI:
    """Create a configured FastAPI application."""

    app_kernel = kernel or get_kernel()
    frontend_dist = _resolve_frontend_dist(app_kernel, serve_frontend)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.kernel = app_kernel
        await app_kernel.initialize()
        yield

    app = FastAPI(
        title="Nova OS API",
        version=NOVA_VERSION,
        description="AI Governance & Control Platform",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        lifespan=lifespan,
    )
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(AuthMiddleware)
    app.add_middleware(QuotaMiddleware)

    app.include_router(status.router)
    app.include_router(auth.router)
    app.include_router(evaluate.router)
    app.include_router(agents.router)
    app.include_router(gmail.router)
    app.include_router(ledger.router)
    app.include_router(analytics.router)
    app.include_router(gateway.router)
    app.include_router(connectors.router)
    app.include_router(workspaces.router)
    app.include_router(settings.router)
    app.include_router(webhooks.router)
    app.include_router(discovery.router)
    app.include_router(realtime.router)

    @app.get("/", response_model=None)
    async def root():
        if frontend_dist is not None:
            return FileResponse(frontend_dist / "index.html")
        return {"name": "Nova OS", "version": NOVA_VERSION, "status": "operational"}

    if frontend_dist is not None:

        @app.get("/{full_path:path}", include_in_schema=False, response_model=None)
        async def spa_fallback(full_path: str):
            normalized = full_path.lstrip("/")
            if normalized.startswith("api/") or normalized in {"api", "openapi.json"}:
                return JSONResponse(status_code=404, content={"detail": "Not Found"})

            candidate = (frontend_dist / normalized).resolve()
            if candidate.is_file() and (candidate == frontend_dist or frontend_dist in candidate.parents):
                return FileResponse(candidate)

            return FileResponse(frontend_dist / "index.html")

    @app.exception_handler(NovaException)
    async def handle_nova_exception(_: Request, exc: NovaException) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": {"code": exc.code, "message": exc.message, "eval_id": exc.eval_id}},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(request: Request, exc: Exception) -> JSONResponse:
        logger = getattr(getattr(request.app.state, "kernel", None), "logger", None)
        if logger is not None:
            logger.exception("unhandled_api_exception", path=request.url.path, method=request.method, error=str(exc))
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": {"code": "internal_error", "message": "unexpected server error"}},
        )

    return app


app = create_app()
