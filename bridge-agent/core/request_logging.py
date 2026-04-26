"""
core/request_logging.py
------------------------
HTTP request/response logging middleware.

Emits two structured log lines per request:
  → request  line: method, path, client IP
  ← response line: method, path, status code, duration_ms, request_id

A UUID request_id is generated for every inbound request and:
  1. Stored in a ContextVar so all log lines within the request carry it.
  2. Returned to the caller as the X-Request-ID response header.

This makes it trivial to grep all log lines for a single request across
the entire call stack (routes → service → agent → clients).
"""

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from core.logging_config import request_id_var

logger = logging.getLogger(__name__)

# Paths excluded from access logs (noisy and not useful for debugging)
_SILENT_PATHS = frozenset({"/health", "/", "/openapi.json", "/redoc"})


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip logging for health checks and UI root
        if request.url.path in _SILENT_PATHS:
            return await call_next(request)

        rid = str(uuid.uuid4())
        token = request_id_var.set(rid)

        logger.info(
            "request",
            extra={
                "http_method": request.method,
                "http_path": request.url.path,
                "client_ip": _client_ip(request),
            },
        )

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "unhandled exception",
                extra={
                    "http_method": request.method,
                    "http_path": request.url.path,
                },
            )
            raise
        finally:
            request_id_var.reset(token)

        duration_ms = round((time.perf_counter() - start) * 1000, 1)

        logger.info(
            "response",
            extra={
                "http_method": request.method,
                "http_path": request.url.path,
                "http_status": response.status_code,
                "duration_ms": duration_ms,
            },
        )

        response.headers["X-Request-ID"] = rid
        return response


def _client_ip(request: Request) -> str:
    """Return the real client IP, respecting X-Forwarded-For if present."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
