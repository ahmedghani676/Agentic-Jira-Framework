"""
models/api_responses/run.py
----------------------------
Response model for GET /api/runs/{run_id} (run retrieval).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from models.api_responses.decision import DecisionResponse


class RunResponse(BaseModel):
    """
    Returned when fetching an existing agent run by its ID.

    Useful for polling run state or re-displaying a past dry-run
    without re-running the agent.
    """

    run_id: str = Field(..., description="The requested run identifier")
    total: int = Field(..., description="Total number of decisions in this run")
    decisions: list[DecisionResponse] = Field(
        ...,
        description="All decisions recorded for this run",
    )
