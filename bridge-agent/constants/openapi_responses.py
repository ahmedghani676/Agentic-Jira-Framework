"""
constants/openapi_responses.py
-------------------------------
Reusable OpenAPI response dicts for the `responses={}` parameter in
FastAPI route decorators.

Declaring all possible HTTP responses per endpoint makes the generated
OpenAPI schema complete — Swagger UI and client generators will show
callers exactly what to expect on both success and error paths.

Usage
-----
    from constants.openapi_responses import OpenAPIResponses

    @router.post(
        "/submit",
        response_model=SubmitResponse,
        responses={
            **OpenAPIResponses.NOT_FOUND,
            **OpenAPIResponses.CONFLICT,
            **OpenAPIResponses.INTERNAL_SERVER_ERROR,
        },
    )
"""

from models.api_responses.error import ErrorResponse

_error_content = {"model": ErrorResponse}


class OpenAPIResponses:
    """
    Pre-built response dicts for use in FastAPI decorator responses={} args.

    Each constant is a single-key dict so they can be merged cleanly with
    the ** unpacking operator when a route returns multiple error codes.
    """

    UNAUTHORIZED: dict = {
        401: {
            "description": "Missing or invalid X-API-Key header.",
            "content": {"application/json": _error_content},
        }
    }

    NOT_FOUND: dict = {
        404: {
            "description": "The requested resource was not found.",
            "content": {"application/json": _error_content},
        }
    }

    CONFLICT: dict = {
        409: {
            "description": "Conflict — the resource has already been processed.",
            "content": {"application/json": _error_content},
        }
    }

    INTERNAL_SERVER_ERROR: dict = {
        500: {
            "description": "Internal server error — agent or downstream API call failed.",
            "content": {"application/json": _error_content},
        }
    }
