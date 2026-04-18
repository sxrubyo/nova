"""API middleware stack."""

from __future__ import annotations

from time import monotonic

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from nova.constants import PUBLIC_ENDPOINTS
from nova.observability.logger import get_logger
from nova.observability.tracer import set_request_id
from nova.security.rate_limiter import RateLimiter
from nova.utils.crypto import generate_id


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a stable request id to every request."""

    async def dispatch(self, request: Request, call_next):
        request_id = generate_id("req")
        request.state.request_id = request_id
        set_request_id(request_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Structured request logging."""

    def __init__(self, app) -> None:  # type: ignore[no-untyped-def]
        super().__init__(app)
        self.logger = get_logger("nova.api")

    async def dispatch(self, request: Request, call_next):
        started = monotonic()
        response = await call_next(request)
        self.logger.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round((monotonic() - started) * 1000, 2),
            request_id=getattr(request.state, "request_id", None),
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Global IP-based rate limiting."""

    def __init__(self, app) -> None:  # type: ignore[no-untyped-def]
        super().__init__(app)
        self._limiter: RateLimiter | None = None

    async def dispatch(self, request: Request, call_next):
        if self._limiter is None:
            kernel = getattr(request.app.state, "kernel", None)
            limit = getattr(getattr(kernel, "config", None), "rate_limit_per_minute", 100)
            self._limiter = RateLimiter(limit)
        client_ip = request.client.host if request.client else "unknown"
        if self._limiter is not None and not self._limiter.allow(client_ip):
            return JSONResponse(status_code=429, content={"detail": "rate limit exceeded"})
        return await call_next(request)


class AuthMiddleware(BaseHTTPMiddleware):
    """Reject unauthenticated access to protected routes."""

    async def dispatch(self, request: Request, call_next):
        if request.url.path in PUBLIC_ENDPOINTS or request.url.path.startswith("/api/docs") or request.url.path.startswith("/api/redoc"):
            return await call_next(request)
        if request.headers.get("x-api-key") or request.headers.get("authorization"):
            return await call_next(request)
        return JSONResponse(status_code=401, content={"detail": "authentication required"})


class QuotaMiddleware(BaseHTTPMiddleware):
    """Pre-check workspace quota for evaluation endpoints."""

    async def dispatch(self, request: Request, call_next):
        if request.url.path != "/api/evaluate":
            return await call_next(request)
        workspace_id = request.headers.get("x-workspace-id")
        if not workspace_id:
            return await call_next(request)
        kernel = getattr(request.app.state, "kernel", None)
        if kernel is None:
            return await call_next(request)
        await kernel.initialize()
        if not await kernel.quota_manager.check(workspace_id):
            return JSONResponse(status_code=429, content={"detail": "workspace quota exceeded"})
        return await call_next(request)
