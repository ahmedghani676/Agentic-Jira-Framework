"""
core/app.py
-----------
FastAPI application factory.

create_app() is the single place where the application is assembled:
  lifespan → logging → app instance → middleware → static files → routes.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from core.logging_config import configure_logging
from core.middleware import register_middleware
from core.startup import validate_config
from routes import register_routes

STATIC_DIR = Path(__file__).parent.parent / "static"


@asynccontextmanager
async def _lifespan(app: FastAPI):
    """Run startup validation before accepting traffic, nothing on shutdown yet."""
    validate_config()
    yield


def create_app() -> FastAPI:
    """
    Build and return a fully configured FastAPI application.

    Steps
    -----
    1. Configure structured JSON logging (must be first).
    2. Create the FastAPI instance with lifespan for startup validation.
    3. Register middleware (auth, request logging, CORS).
    4. Mount the static files directory.
    5. Register all API routers.
    """
    configure_logging()

    app = FastAPI(
        title="WorkFlex Bridge Agent",
        description=(
            "AI agent that reads Microsoft Teams #feature-requests messages, "
            "cross-references HubSpot CRM for ARR, deduplicates against Jira, "
            "and creates or updates tickets automatically."
        ),
        version="1.0.0",
        lifespan=_lifespan,
    )

    register_middleware(app)

    app.mount(
        "/static",
        StaticFiles(directory=str(STATIC_DIR)),
        name="static",
    )

    register_routes(app)

    return app
