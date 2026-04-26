"""
routes/ui.py
------------
Admin UI endpoint.

GET / — serves the single-page HTML admin console (static/index.html).
Excluded from the OpenAPI schema so it does not appear in Swagger docs.
"""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

STATIC_DIR = Path(__file__).parent.parent / "static"

router = APIRouter(include_in_schema=False)


@router.get("/")
def serve_admin_ui() -> FileResponse:
    """Serve the Bridge Agent admin console."""
    return FileResponse(str(STATIC_DIR / "index.html"))
