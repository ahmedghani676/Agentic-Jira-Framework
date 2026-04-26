"""HubSpot CRM API v3 client (mock-compatible).

All public functions return typed Pydantic models defined in models.py.
Token is fetched automatically from the mock server on first use and cached
in process memory — no manual token management required.
"""

import logging

import httpx

from config import settings
from models import HubSpotCompany

logger = logging.getLogger(__name__)

_TOKEN_URL = f"{settings.mock_base_url}/auth/tokens/hubspot"
_BASE = f"{settings.mock_base_url}/hubspot/crm/v3/objects/companies"

# Shared HTTP client — connection pooling, no auth baked in (fetched lazily).
_client = httpx.Client(
    headers={"Content-Type": "application/json"},
    timeout=15,
)

# In-process token cache — populated on first API call, lives for the process lifetime.
_auth_cache: dict[str, str] = {}


def _get_auth_header(force_refresh: bool = False) -> str:
    """
    Return the Bearer auth header value, fetching a fresh token from the mock
    server if the cache is empty or a refresh is forced (e.g. after a 401).

    The mock server returns: {"auth_header": "Authorization: Bearer <token>", ...}
    We store and return just the value part: "Bearer <token>".
    """
    if not _auth_cache.get("header") or force_refresh:
        logger.info("Fetching HubSpot token from mock server")
        resp = _client.post(_TOKEN_URL)
        resp.raise_for_status()
        data = resp.json()
        # "Authorization: Bearer xxx" → "Bearer xxx"
        _auth_cache["header"] = data["auth_header"].split(": ", 1)[1]
        logger.info("HubSpot token acquired and cached")
    return _auth_cache["header"]


def _request_with_retry(method: str, url: str, **kwargs) -> httpx.Response:
    """Make a request, retrying once with a fresh token on 401."""
    resp = _client.request(method, url, headers={"Authorization": _get_auth_header()}, **kwargs)
    if resp.status_code == 401:
        logger.warning("HubSpot 401 — refreshing token and retrying")
        resp = _client.request(method, url, headers={"Authorization": _get_auth_header(force_refresh=True)}, **kwargs)
    resp.raise_for_status()
    return resp


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

def search_company(name: str) -> HubSpotCompany | None:
    """
    Full-text search for a company by name.

    Args:
        name: Company name to search for (partial matches are supported).

    Returns:
        HubSpotCompany with the matched company name and ARR,
        or None if no company was found.
    """
    payload = {
        "query": name,
        "properties": ["name", "annual_recurring_revenue", "annualrevenue"],
        "limit": 5,
    }
    resp = _request_with_retry("POST", f"{_BASE}/search", json=payload)

    results = resp.json().get("results", [])
    if not results:
        logger.warning("No HubSpot company found for query=%r", name)
        return None

    # Prefer exact name match; fall back to first result
    query_lower = name.lower()
    best = next(
        (r for r in results if r.get("properties", {}).get("name", "").lower() == query_lower),
        results[0],
    )

    arr = _extract_arr(best.get("properties", {}))
    return HubSpotCompany(
        company_name=best.get("properties", {}).get("name", name),
        arr=arr,
    )


def get_arr(name: str) -> int | None:
    """
    Convenience wrapper — return only the ARR for a company name.

    Args:
        name: Company name to look up.

    Returns:
        ARR as an integer (USD) or None if the company was not found.
    """
    result = search_company(name)
    return result.arr if result else None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_arr(properties: dict) -> int | None:
    """Parse ARR from HubSpot property bag (two possible field names)."""
    raw = properties.get("annual_recurring_revenue") or properties.get("annualrevenue")
    if not raw:
        return None
    try:
        return int(float(raw))
    except (ValueError, TypeError):
        logger.warning("Could not parse ARR value: %r", raw)
        return None
