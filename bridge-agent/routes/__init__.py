"""
routes/__init__.py
------------------
Registers all API routers onto the FastAPI application.

Add new routers here as the API grows — never import them directly in main.py
or core/app.py. This file is the single place that owns route registration.
"""

from fastapi import FastAPI

from routes.health import router as health_router
from routes.agent import router as agent_router
from routes.ui import router as ui_router


def register_routes(app: FastAPI) -> None:
    """
    Attach all routers to the application instance.

    Args:
        app: The FastAPI application built by core/app.py.
    """
    app.include_router(health_router)
    app.include_router(agent_router)
    app.include_router(ui_router)
