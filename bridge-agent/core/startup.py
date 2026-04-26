"""
core/startup.py
---------------
Startup configuration validation.

validate_config() is called inside the FastAPI lifespan before the server
starts accepting traffic. Any misconfigured or missing value raises
RuntimeError with a precise message — the server refuses to start rather
than failing mid-request with a cryptic error.

Rules
-----
- Hard failures (raise RuntimeError): the application cannot function at all.
- Warnings (log only):               the application works but a production
                                      best-practice is violated.
"""

import logging

from config import settings

logger = logging.getLogger(__name__)


def validate_config() -> None:
    """
    Validate all required settings at startup.

    Raises
    ------
    RuntimeError: Any required setting is missing or obviously wrong.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # ── Anthropic ────────────────────────────────────────────────────────────
    if not settings.anthropic_api_key:
        errors.append("ANTHROPIC_API_KEY is not set.")
    elif not settings.anthropic_api_key.startswith("sk-ant-"):
        errors.append(
            f"ANTHROPIC_API_KEY looks invalid (got '{settings.anthropic_api_key[:12]}…'). "
            "Expected format: sk-ant-..."
        )

    if not settings.claude_model:
        errors.append("CLAUDE_MODEL is not set.")

    # ── Jira / HubSpot / Teams ───────────────────────────────────────────────
    # Tokens are fetched automatically from the mock server at runtime.
    # Only the Jira email (Basic-auth username) and Teams client_id are needed.
    if not settings.jira_email or "@" not in settings.jira_email:
        errors.append(f"JIRA_EMAIL '{settings.jira_email}' does not look like an email address.")

    if not settings.teams_client_id:
        errors.append("TEAMS_CLIENT_ID is not set.")

    # ── Mock server ──────────────────────────────────────────────────────────
    if not settings.mock_base_url:
        errors.append("MOCK_BASE_URL is not set.")
    elif not settings.mock_base_url.startswith(("http://", "https://")):
        errors.append(
            f"MOCK_BASE_URL '{settings.mock_base_url}' must start with http:// or https://."
        )

    # ── Agent safety limits ──────────────────────────────────────────────────
    if settings.agent_max_iterations < 1:
        errors.append(
            f"AGENT_MAX_ITERATIONS must be at least 1, got {settings.agent_max_iterations}."
        )

    if settings.agent_timeout_seconds <= 0:
        errors.append(
            f"AGENT_TIMEOUT_SECONDS must be positive, got {settings.agent_timeout_seconds}."
        )

    # ── Auth — warning only ──────────────────────────────────────────────────
    if not settings.api_key:
        warnings.append(
            "API_KEY is not set — all /api/* endpoints are publicly accessible. "
            "Set API_KEY in production."
        )

    # ── Emit warnings ────────────────────────────────────────────────────────
    for warning in warnings:
        logger.warning("config warning: %s", warning)

    # ── Fail fast on errors ──────────────────────────────────────────────────
    if errors:
        error_list = "\n  ".join(f"• {e}" for e in errors)
        raise RuntimeError(
            f"Bridge Agent failed to start — {len(errors)} configuration error(s):\n"
            f"  {error_list}\n"
            "Fix the above in your .env file and restart."
        )

    logger.info(
        "config validated",
        extra={
            "claude_model": settings.claude_model,
            "mock_base_url": settings.mock_base_url,
            "agent_max_iterations": settings.agent_max_iterations,
            "agent_timeout_seconds": settings.agent_timeout_seconds,
            "auth_enabled": bool(settings.api_key),
        },
    )
