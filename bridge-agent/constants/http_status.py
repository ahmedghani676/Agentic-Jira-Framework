"""
constants/http_status.py
------------------------
HTTP status code integers used across route controllers.

Using named constants instead of bare integers makes intent obvious
and prevents silent bugs from typos (e.g. 404 vs 405).
"""


class HTTPStatus:
    """Standard HTTP status codes referenced by this application."""

    # 2xx — Success
    OK = 200
    CREATED = 201

    # 4xx — Client errors
    UNAUTHORIZED = 401
    NOT_FOUND = 404
    CONFLICT = 409
    UNPROCESSABLE_ENTITY = 422

    # 5xx — Server errors
    INTERNAL_SERVER_ERROR = 500
