"""
core/middleware.py
------------------
Middleware registration for the Bridge Agent FastAPI application.

Middleware executes in reverse registration order (last registered = first to run).
Current order (outermost → innermost):
  1. APIKeyMiddleware      — rejects unauthenticated requests immediately
  2. RequestLoggingMiddleware — logs every request/response with timing + request_id
  3. CORSMiddleware        — sets CORS headers on the way out
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.auth_middleware import APIKeyMiddleware
from core.request_logging import RequestLoggingMiddleware


def register_middleware(app: FastAPI) -> None:
    """
    Attach all middleware to the FastAPI application instance.

    Args:
        app: The FastAPI application to configure.
    """
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False,
                       allow_methods=["*"], allow_headers=["*"])
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(APIKeyMiddleware)
