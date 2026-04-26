"""
models/api_responses/error.py
------------------------------
Standardised error response body returned on all non-2xx HTTP responses.

Using a typed model instead of a raw string ensures the OpenAPI schema
accurately documents what callers receive when an error occurs, and gives
clients a consistent shape to parse.
"""

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """
    Returned by the API on any 4xx or 5xx response.

    FastAPI wraps HTTPException.detail in this shape automatically when
    the model is declared in the route's responses={} parameter.
    """

    detail: str = Field(
        ...,
        description="Human-readable description of what went wrong",
        examples=["run_id 'abc-123' not found. Call /api/process first."],
    )
