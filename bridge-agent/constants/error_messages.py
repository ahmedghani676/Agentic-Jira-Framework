"""
constants/error_messages.py
----------------------------
Error detail strings returned in HTTPException responses.

Centralising these strings ensures:
  - Consistent wording across all endpoints.
  - A single place to update copy without hunting through route files.
  - Easy unit testing of error conditions by importing the expected string.

Usage
-----
    from constants.error_messages import ErrorMessages

    raise HTTPException(
        status_code=HTTPStatus.NOT_FOUND,
        detail=ErrorMessages.RUN_NOT_FOUND.format(run_id=body.run_id),
    )
"""


class ErrorMessages:
    """Human-readable error detail strings for HTTPException responses."""

    # 404 — Not Found
    RUN_NOT_FOUND = (
        "run_id '{run_id}' not found. Call POST /api/process first to create a run."
    )

    # 409 — Conflict
    RUN_ALREADY_SUBMITTED = (
        "This run has already been submitted. "
        "Start a fresh run by calling POST /api/process again."
    )

    # 401 — Unauthorised
    UNAUTHORIZED = "Missing or invalid API key. Set the X-API-Key request header."

    # 500 — Internal Server Error
    PROCESS_FAILED = "Agent process run failed unexpectedly. Check server logs for details."
    SUBMIT_FAILED = "Agent submit failed unexpectedly. Check server logs for details."
