"""Jira Cloud REST API v3 client (mock-compatible).

All public functions return typed Pydantic models defined in models.py.
Token is fetched automatically from the mock server on first use and cached
in process memory — no manual token management required.
"""

import base64
import logging
from typing import Any

import httpx

from config import settings
from models import JiraComment, JiraIssue, JiraIssueRef

logger = logging.getLogger(__name__)

_TOKEN_URL = f"{settings.mock_base_url}/auth/tokens/jira"
_BASE = f"{settings.mock_base_url}/jira/rest/api/3"

# Shared HTTP client — connection pooling, no auth baked in (fetched lazily).
_client = httpx.Client(
    headers={"Content-Type": "application/json"},
    timeout=15,
)

# In-process token cache — populated on first API call, lives for the process lifetime.
_auth_cache: dict[str, str] = {}


def _get_auth_header(force_refresh: bool = False) -> str:
    """
    Return the Basic auth header value, fetching a fresh token from the mock
    server if the cache is empty or a refresh is forced (e.g. after a 401).

    The mock server returns: {"auth_header": "Authorization: Basic <b64>", ...}
    We store and return just the value part: "Basic <b64>".
    """
    if not _auth_cache.get("header") or force_refresh:
        logger.info("Fetching Jira token from mock server")
        resp = _client.post(_TOKEN_URL, json={"email": settings.jira_email})
        resp.raise_for_status()
        data = resp.json()
        # "Authorization: Basic xxx" → "Basic xxx"
        _auth_cache["header"] = data["auth_header"].split(": ", 1)[1]
        logger.info("Jira token acquired and cached")
    return _auth_cache["header"]


def _request_with_retry(method: str, url: str, **kwargs) -> httpx.Response:
    """Make a request, retrying once with a fresh token on 401."""
    resp = _client.request(method, url, headers={"Authorization": _get_auth_header()}, **kwargs)
    if resp.status_code == 401:
        logger.warning("Jira 401 — refreshing token and retrying")
        resp = _client.request(method, url, headers={"Authorization": _get_auth_header(force_refresh=True)}, **kwargs)
    resp.raise_for_status()
    return resp




# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

def search_issues(jql: str = "", max_results: int = 50) -> list[JiraIssue]:
    """
    Return all issues from the Jira backlog.

    Args:
        jql:         JQL query string (mock returns full backlog regardless).
        max_results: Maximum number of issues to return.

    Returns:
        List of JiraIssue objects.
    """
    resp = _request_with_retry("GET", f"{_BASE}/search", params={"jql": jql, "maxResults": max_results})

    return [
        JiraIssue(
            key=i.get("key", ""),
            summary=i.get("fields", {}).get("summary", ""),
            status=i.get("fields", {}).get("status", {}).get("name", "Unknown"),
            description_text=_adf_to_text(i.get("fields", {}).get("description")),
        )
        for i in resp.json().get("issues", [])
    ]


def get_issue(issue_key: str) -> JiraIssue:
    """
    Return a typed JiraIssue for a given key or ID.

    Args:
        issue_key: Jira issue key (e.g. "JIRA-1042") or numeric ID.

    Returns:
        JiraIssue populated from the API response.
    """
    resp = _request_with_retry("GET", f"{_BASE}/issue/{issue_key}")
    i = resp.json()
    return JiraIssue(
        key=i.get("key", ""),
        summary=i.get("fields", {}).get("summary", ""),
        status=i.get("fields", {}).get("status", {}).get("name", "Unknown"),
        description_text=_adf_to_text(i.get("fields", {}).get("description")),
    )


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------

def create_issue(
    summary: str,
    description: str,
    labels: list[str] | None = None,
) -> JiraIssueRef:
    """
    Create a new Jira Story ticket.

    Args:
        summary:     Short ticket title (max ~80 chars).
        description: Full ticket body as plain text (converted to ADF internally).
        labels:      Optional list of label strings.

    Returns:
        JiraIssueRef with the new issue id, key, and self URL.
    """
    payload: dict[str, Any] = {
        "fields": {
            "project": {"key": "JIRA"},
            "issuetype": {"name": "Story"},
            "summary": summary,
            "description": _text_to_adf(description),
            "labels": labels or [],
        }
    }
    resp = _request_with_retry("POST", f"{_BASE}/issue", json=payload)

    data = resp.json()
    logger.info("Created Jira issue %s", data.get("key"))
    return JiraIssueRef.model_validate(data)


def add_comment(issue_key: str, comment_text: str) -> JiraComment:
    """
    Add a plain-text comment to an existing Jira issue.

    Args:
        issue_key:    Jira issue key (e.g. "JIRA-1042").
        comment_text: Comment body as plain text (converted to ADF internally).

    Returns:
        JiraComment with the comment ID and issue key.
    """
    payload = {"body": _text_to_adf(comment_text)}
    resp = _request_with_retry("POST", f"{_BASE}/issue/{issue_key}/comment", json=payload)

    data = resp.json()
    logger.info("Added comment %s to %s", data.get("id"), issue_key)
    return JiraComment(id=data.get("id", ""), issue_key=issue_key)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _text_to_adf(text: str) -> dict[str, Any]:
    """Convert a plain-text string to Atlassian Document Format (ADF)."""
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    return {
        "version": 1,
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": p}],
            }
            for p in (paragraphs or [""])
        ],
    }


def _adf_to_text(adf: dict | None) -> str:
    """Extract plain text from Atlassian Document Format (ADF)."""
    if not adf or not isinstance(adf, dict):
        return ""
    texts: list[str] = []
    for node in adf.get("content", []):
        for inline in node.get("content", []):
            if inline.get("type") == "text":
                texts.append(inline.get("text", ""))
    return " ".join(texts)
