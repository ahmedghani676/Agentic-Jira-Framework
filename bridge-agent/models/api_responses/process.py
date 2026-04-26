"""
models/api_responses/process.py
--------------------------------
Response model for POST /api/process (dry-run agent pass).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from models.api_responses.decision import DecisionResponse


class ProcessResponse(BaseModel):
    """
    Returned after a successful dry-run agent pass.

    Contains a run_id the admin must pass to POST /api/submit,
    plus the full list of proposed decisions for review.
    """

    run_id: str = Field(
        ...,
        description="Unique run identifier — pass this to POST /api/submit to execute",
    )
    total: int = Field(
        ...,
        description="Total number of Teams messages evaluated in this run",
    )
    decisions: list[DecisionResponse] = Field(
        ...,
        description="One DecisionResponse per Teams message that was evaluated",
    )
