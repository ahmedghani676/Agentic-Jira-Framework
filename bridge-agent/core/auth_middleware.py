"""
core/auth_middleware.py
-----------------------
API key authentication middleware.

Enforces X-API-Key header on all /api/* routes when API_KEY is configured.
Excluded paths (health check, UI, static assets) pass through without auth
so load balancers and browser clients are never blocked.

If API_KEY is empty or unset the middleware is a no-op, which allows running
without auth in local development.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from config import settings
from constants import ErrorMessages, HTTPStatus

# Paths that never require authentication
_EXCLUDED_PREFIXES = ("/health", "/", "/static", "/docs", "/redoc", "/openapi.json")


class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Auth disabled — pass everything through (dev mode)
        if not settings.api_key:
            return await call_next(request)

        # Excluded paths — UI, health check, Swagger docs
        if any(request.url.path.startswith(p) for p in _EXCLUDED_PREFIXES):
            return await call_next(request)

        if request.headers.get("X-API-Key") != settings.api_key:
            return JSONResponse(
                status_code=HTTPStatus.UNAUTHORIZED,
                content={"detail": ErrorMessages.UNAUTHORIZED},
            )

        return await call_next(request)
