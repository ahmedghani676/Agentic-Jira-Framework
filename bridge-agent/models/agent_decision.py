"""
models/agent_decision.py
------------------------
Internal agent-layer model.

DecisionItem represents the agent's full decision for a single Teams message.
It is created during the dry-run phase and mutated (submitted=True) after
the submit phase executes the action against Jira and Teams.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from models.types import ActionType


class DecisionItem(BaseModel):
    """
    One agent decision — maps 1-to-1 with a Teams channel message.

    Lifecycle
    ---------
    1. Created by ToolDispatcher during process() (dry-run).
    2. Reviewed by the admin via the UI.
    3. Mutated by submit() — submitted=True, submitted_jira_key set.
    """

    # ── Source message ──────────────────────────────────────────────────────
    message_id: str = Field(
        ...,
        description="Unique Teams message ID",
    )
    sender: str = Field(
        ...,
        description="Display name of the Teams message author",
    )
    message_text: str = Field(
        ...,
        description="Raw text body of the Teams message",
    )

    # ── Extracted entities ──────────────────────────────────────────────────
    client_name: str = Field(
        ...,
        description="Company name extracted from the message by the agent",
    )
    core_request: str = Field(
        default="",
        description="One-line summary of what the client requested",
    )
    arr: int | None = Field(
        default=None,
        description="Annual Recurring Revenue in USD, sourced from HubSpot CRM",
    )

    # ── Decision ────────────────────────────────────────────────────────────
    action: ActionType = Field(
        ...,
        description="CREATE a new Jira ticket, UPDATE an existing one, or SKIP",
    )

    # UPDATE-specific fields
    jira_key: str | None = Field(
        default=None,
        description="Key of the existing Jira issue targeted by an UPDATE action",
    )
    draft_comment: str | None = Field(
        default=None,
        description="Comment text to add to the existing ticket (UPDATE only)",
    )

    # CREATE-specific fields
    draft_summary: str | None = Field(
        default=None,
        description="Proposed Jira ticket title (CREATE only)",
    )
    draft_description: str | None = Field(
        default=None,
        description="Proposed Jira ticket description body (CREATE only)",
    )
    draft_labels: list[str] = Field(
        default_factory=list,
        description="Labels to attach to the new ticket (CREATE only)",
    )

    # Shared Teams response
    teams_feedback: str | None = Field(
        default=None,
        description="Confirmation message to post back in the Teams channel",
    )

    # ── Submit state ─────────────────────────────────────────────────────────
    submitted: bool = Field(
        default=False,
        description="True once the action has been executed against the live APIs",
    )
    submitted_jira_key: str | None = Field(
        default=None,
        description=(
            "Jira key after submission: "
            "newly assigned key for CREATE, same key for UPDATE"
        ),
    )
