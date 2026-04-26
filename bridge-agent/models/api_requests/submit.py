"""
models/api_requests/submit.py
------------------------------
Request body for POST /api/submit (decision execution).
"""

from pydantic import BaseModel, Field


class SubmitRequest(BaseModel):
    """
    Sent by the admin UI to trigger execution of a dry-run.

    The run_id is returned by POST /api/process and identifies the
    pending decisions stored in the server-side session.
    """

    run_id: str = Field(
        ...,
        description=(
            "Unique run identifier returned by POST /api/process. "
            "Used to look up the pending decisions and execute them."
        ),
        examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
    )
