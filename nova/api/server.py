"""FastAPI server bootstrap."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from nova.api.middleware import AuthMiddleware, LoggingMiddleware, QuotaMiddleware, RateLimitMiddleware, RequestIDMiddleware
from nova.api.routes import agents, analytics, auth, evaluate, gateway, ledger, settings, status, webhooks, workspaces
from nova.constants import NOVA_VERSION
from nova.exceptions import NovaException
from nova.kernel import NovaKernel, get_kernel


def create_app(kernel: NovaKernel | None = None) -> FastAPI:
    """Create a configured FastAPI application."""

    app_kernel = kernel or get_kernel()

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
    app.include_router(ledger.router)
    app.include_router(analytics.router)
    app.include_router(gateway.router)
    app.include_router(workspaces.router)
    app.include_router(settings.router)
    app.include_router(webhooks.router)

    @app.get("/")
    async def root() -> dict:
        return {"name": "Nova OS", "version": NOVA_VERSION, "status": "operational"}

    @app.exception_handler(NovaException)
    async def handle_nova_exception(_: Request, exc: NovaException) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": {"code": exc.code, "message": exc.message, "eval_id": exc.eval_id}},
        )

    return app


app = create_app()
