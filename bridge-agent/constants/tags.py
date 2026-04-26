"""
constants/tags.py
-----------------
OpenAPI tag strings used to group endpoints in Swagger UI and ReDoc.

Importing from here instead of writing raw strings in every router
ensures all tags stay consistent and refactoring is a one-line change.
"""


class OpenAPITag:
    """OpenAPI grouping tags for FastAPI router declarations."""

    AGENT = "Agent"
    OPS = "Ops"
