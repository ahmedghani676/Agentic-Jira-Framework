"""
main.py
-------
Application entry point.

Responsibilities of this file:
  1. Create the FastAPI application via the factory in core/app.py.
  2. Expose the `app` object for uvicorn (both CLI and programmatic use).

Everything else — logging, middleware, routes, session store — lives in its
own module. This file intentionally contains as little logic as possible.
"""

import uvicorn

from core.app import create_app

app = create_app()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
