"""
models/__init__.py
------------------
Public re-export surface for the entire models package.

Import from here everywhere in the application:

    from models import DecisionItem, ProcessResponse, SubmitRequest ...

Package layout
--------------
  types.py                   — ActionType literal + format_arr() utility
  agent_decision.py          — DecisionItem (internal agent state per Teams message)
  integrations/
    jira.py                  — JiraIssue, JiraIssueRef, JiraComment
    hubspot.py               — HubSpotCompany
    teams.py                 — TeamsMessage, TeamsSentMessage
  api_requests/
    submit.py                — SubmitRequest   (POST /api/submit)
  api_responses/
    health.py                — HealthResponse  (GET /health)
    decision.py              — DecisionResponse (embedded in all agent responses)
    process.py               — ProcessResponse (POST /api/process)
    submit.py                — SubmitResponse  (POST /api/submit)
    run.py                   — RunResponse     (GET /api/runs/{run_id})
"""

from models.types import ActionType, format_arr
from models.agent_decision import DecisionItem
from models.integrations import (
    HubSpotCompany,
    JiraComment,
    JiraIssue,
    JiraIssueRef,
    TeamsMessage,
    TeamsSentMessage,
)
from models.api_requests import SubmitRequest
from models.api_responses import (
    DecisionResponse,
    ErrorResponse,
    HealthResponse,
    ProcessResponse,
    RunResponse,
    SubmitResponse,
)

__all__ = [
    # types
    "ActionType",
    "format_arr",
    # agent
    "DecisionItem",
    # integrations
    "TeamsMessage",
    "TeamsSentMessage",
    "HubSpotCompany",
    "JiraIssue",
    "JiraIssueRef",
    "JiraComment",
    # api_requests
    "SubmitRequest",
    # api_responses
    "ErrorResponse",
    "HealthResponse",
    "DecisionResponse",
    "ProcessResponse",
    "SubmitResponse",
    "RunResponse",
]
