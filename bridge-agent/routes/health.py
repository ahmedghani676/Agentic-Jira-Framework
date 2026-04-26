"""
routes/health.py
----------------
Liveness check endpoint.

GET /health — returns {"status": "ok"} when the service is running.
Used by load balancers, Docker health checks, and monitoring systems.
"""

from fastapi import APIRouter

from constants import HTTPStatus, OpenAPITag
from models import HealthResponse

router = APIRouter(tags=[OpenAPITag.OPS])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=HTTPStatus.OK,
    summary="Liveness check",
    description="Returns 200 OK when the service is up. No authentication required.",
)
def health() -> HealthResponse:
    return HealthResponse()
