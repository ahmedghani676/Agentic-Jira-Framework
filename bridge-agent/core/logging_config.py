"""
core/logging_config.py
-----------------------
Structured JSON logging for the Bridge Agent.

Every log record is emitted as a single-line JSON object so that log
aggregators (Datadog, CloudWatch, Loki) can index and query fields
without regex parsing.

Standard fields on every line:
  timestamp  — ISO-8601 UTC
  level      — DEBUG / INFO / WARNING / ERROR / CRITICAL
  logger     — dotted module name, e.g. "routes.agent"
  message    — the log message string

Request-scoped fields (present when a request_id is active):
  request_id — UUID injected by RequestLoggingMiddleware per HTTP request

Usage
-----
    import logging
    logger = logging.getLogger(__name__)
    logger.info("something happened", extra={"ticket_key": "JIRA-1042"})
"""

import json
import logging
import traceback
from contextvars import ContextVar
from datetime import datetime, timezone

# Holds the current request's UUID; empty string when outside a request
request_id_var: ContextVar[str] = ContextVar("request_id", default="")


class _JSONFormatter(logging.Formatter):
    """Emit each log record as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        rid = request_id_var.get("")
        if rid:
            payload["request_id"] = rid

        # Merge any extra fields passed via logger.info(..., extra={...})
        for key, value in record.__dict__.items():
            if key not in _STDLIB_LOG_ATTRS and not key.startswith("_"):
                payload[key] = value

        if record.exc_info:
            payload["exception"] = traceback.format_exception(*record.exc_info)

        return json.dumps(payload, default=str)


# Standard LogRecord attributes — excluded from extra field merging
_STDLIB_LOG_ATTRS = frozenset({
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName",
    "processName", "process", "message", "taskName",
})


def configure_logging() -> None:
    """
    Replace the root handler with a JSON formatter.

    Safe to call multiple times — only reconfigures if no handlers exist yet.
    """
    root = logging.getLogger()
    if root.handlers:
        return

    handler = logging.StreamHandler()
    handler.setFormatter(_JSONFormatter())
    root.addHandler(handler)
    root.setLevel(logging.INFO)

    # Suppress noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
