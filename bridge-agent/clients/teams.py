"""Microsoft Graph API (Teams) client (mock-compatible).

All public functions return typed Pydantic models defined in models.py.
Uses OAuth 2.0 client-credentials flow with an in-process token cache.
"""

import logging
import time

import httpx

from config import settings
from models import TeamsMessage, TeamsSentMessage

logger = logging.getLogger(__name__)

_TEAM_ID = "a1b2c3d4-e5f6-7890-abcd-ef0123456789"
_CHANNEL_ID = "19:feature-requests@thread.tacv2"

_SECRET_URL = f"{settings.mock_base_url}/auth/tokens/teams"
_TOKEN_URL = f"{settings.mock_base_url}/auth/teams/token"
_GRAPH_BASE = f"{settings.mock_base_url}/graph/v1.0"

# In-process secret cache — client_secret fetched once from mock server.
_secret_cache: dict[str, str] = {}

# In-process access token cache — refreshed when expired.
_token_cache: dict[str, float | str] = {}

_client = httpx.Client(timeout=15)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def _get_client_secret(force_refresh: bool = False) -> str:
    """
    Return the Teams client secret, fetching it from the mock server on first
    call or when a refresh is forced (e.g. after the mock server restarts).
    """
    if not _secret_cache.get("secret") or force_refresh:
        logger.info("Fetching Teams client secret from mock server")
        resp = _client.post(_SECRET_URL)
        resp.raise_for_status()
        _secret_cache["secret"] = resp.json()["token"]
        logger.info("Teams client secret acquired and cached")
    return _secret_cache["secret"]


def _get_access_token(force_refresh: bool = False) -> str:
    """
    Return a valid OAuth2 access token, refreshing it if expired or forced.
    On 401 from Graph API, call with force_refresh=True to re-fetch secret + token.

    Uses the client-credentials flow against the mock token endpoint.
    Token lifetime is respected with a 60-second safety buffer.
    """
    if not force_refresh and _token_cache.get("token") and time.time() < float(_token_cache.get("expires_at", 0)):
        return str(_token_cache["token"])

    resp = _client.post(
        _TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": settings.teams_client_id,
            "client_secret": _get_client_secret(force_refresh=force_refresh),
            "scope": "https://graph.microsoft.com/.default",
        },
    )
    resp.raise_for_status()

    data = resp.json()
    _token_cache["token"] = data["access_token"]
    _token_cache["expires_at"] = time.time() + data.get("expires_in", 3600) - 60
    return str(_token_cache["token"])


def _auth_headers(force_refresh: bool = False) -> dict[str, str]:
    return {"Authorization": f"Bearer {_get_access_token(force_refresh=force_refresh)}"}


def _request_with_retry(method: str, url: str, **kwargs) -> httpx.Response:
    """Make a request, retrying once with refreshed credentials on 401."""
    resp = _client.request(method, url, headers=_auth_headers(), **kwargs)
    if resp.status_code == 401:
        logger.warning("Teams 401 — refreshing secret + token and retrying")
        resp = _client.request(method, url, headers=_auth_headers(force_refresh=True), **kwargs)
    resp.raise_for_status()
    return resp


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

def get_messages(limit: int = 50) -> list[TeamsMessage]:
    """
    Fetch recent messages from the #feature-requests channel.

    Follows @odata.nextLink pagination until `limit` messages are collected
    or no more pages are available.

    Args:
        limit: Maximum number of messages to return.

    Returns:
        List of TeamsMessage objects.
    """
    messages: list[TeamsMessage] = []
    url = (
        f"{_GRAPH_BASE}/teams/{_TEAM_ID}/channels/{_CHANNEL_ID}/messages"
        f"?$top={min(limit, 50)}"
    )

    while url and len(messages) < limit:
        resp = _request_with_retry("GET", url)
        data = resp.json()

        for m in data.get("value", []):
            messages.append(
                TeamsMessage(
                    id=m.get("id", ""),
                    sender=m.get("from", {}).get("user", {}).get("displayName", "Unknown"),
                    text=m.get("body", {}).get("content", ""),
                    created=m.get("createdDateTime", ""),
                )
            )

        url = data.get("@odata.nextLink")

    return messages[:limit]


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------

def send_message(text: str) -> TeamsSentMessage:
    """
    Post a new message to the #feature-requests channel.

    Args:
        text: Plain-text message body.

    Returns:
        TeamsSentMessage with the new message ID and posted text.
    """
    url = f"{_GRAPH_BASE}/teams/{_TEAM_ID}/channels/{_CHANNEL_ID}/messages"
    payload = {"body": {"contentType": "text", "content": text}}

    resp = _request_with_retry("POST", url, json=payload)
    data = resp.json()
    logger.info("Sent Teams message id=%s", data.get("id"))
    return TeamsSentMessage(id=data.get("id", ""), message=text)


def reply_to_message(message_id: str, text: str) -> TeamsSentMessage:
    """
    Reply directly to an existing message thread.

    Args:
        message_id: ID of the parent message to reply to.
        text:       Plain-text reply body.

    Returns:
        TeamsSentMessage with the new reply ID and posted text.
    """
    url = (
        f"{_GRAPH_BASE}/teams/{_TEAM_ID}/channels/{_CHANNEL_ID}"
        f"/messages/{message_id}/replies"
    )
    payload = {"body": {"contentType": "text", "content": text}}

    resp = _request_with_retry("POST", url, json=payload)
    data = resp.json()
    logger.info("Sent Teams reply id=%s to message=%s", data.get("id"), message_id)
    return TeamsSentMessage(id=data.get("id", ""), message=text)
