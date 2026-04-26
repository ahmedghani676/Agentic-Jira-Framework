"""
models/api_responses/submit.py
-------------------------------
Response model for POST /api/submit (decision execution).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from models.api_responses.decision import DecisionResponse


class SubmitResponse(BaseModel):
    """
    Returned after all approved decisions have been executed.

    The submitted count reflects how many CREATE/UPDATE actions were
    successfully written to Jira and Teams. SKIP decisions are excluded.
    """

    run_id: str = Field(
        ...,
        description="The run_id that was submitted",
    )
    submitted: int = Field(
        ...,
        description="Number of CREATE/UPDATE actions successfully executed",
    )
    decisions: list[DecisionResponse] = Field(
        ...,
        description="Updated decisions reflecting the post-submission state",
    )
