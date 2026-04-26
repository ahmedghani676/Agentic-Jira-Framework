"""
models/api_responses/health.py
-------------------------------
Response model for the GET /health liveness endpoint.
"""

from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Returned by GET /health to confirm the service is running."""

    status: Literal["ok"] = Field(
        default="ok",
        description="Always 'ok' when the service is up",
    )
