"""
models/api_responses/decision.py
---------------------------------
HTTP view of a single agent decision, returned inside every agent response.

DecisionResponse is a read-only serialisation of the internal DecisionItem.
It mirrors all DecisionItem fields and adds arr_formatted — a display-only
string computed from the raw ARR integer — so the UI never has to format it.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from models.agent_decision import DecisionItem
from models.types import ActionType, format_arr


class DecisionResponse(BaseModel):
    """
    Serialised view of one agent decision sent to the admin UI.

    One DecisionResponse is produced per Teams message that was evaluated.
    The action field tells the UI whether a ticket will be created, an
    existing one updated, or the message skipped entirely.
    """

    # ── Source message ──────────────────────────────────────────────────────
    message_id: str = Field(..., description="Teams message ID")
    sender: str = Field(..., description="Display name of the Teams message author")
    message_text: str = Field(..., description="Raw text body of the Teams message")

    # ── Extracted entities ───────────────────────────────────────────────────
    client_name: str = Field(..., description="Company name extracted by the agent")
    core_request: str = Field(..., description="One-line summary of the feature request")
    arr: int | None = Field(default=None, description="Annual Recurring Revenue in USD")
    arr_formatted: str = Field(
        ...,
        description="Human-readable ARR, e.g. '$520k ARR' or 'Unknown ARR'",
    )

    # ── Decision ────────────────────────────────────────────────────────────
    action: ActionType = Field(..., description="CREATE, UPDATE, or SKIP")

    jira_key: str | None = Field(
        default=None,
        description="Existing Jira issue key targeted by an UPDATE action",
    )
    draft_summary: str | None = Field(
        default=None,
        description="Proposed Jira ticket title (CREATE only)",
    )
    draft_description: str | None = Field(
        default=None,
        description="Proposed Jira ticket body (CREATE only)",
    )
    draft_comment: str | None = Field(
        default=None,
        description="Comment text to add to the existing ticket (UPDATE only)",
    )
    draft_labels: list[str] = Field(
        default_factory=list,
        description="Labels to attach to the new ticket (CREATE only)",
    )
    teams_feedback: str | None = Field(
        default=None,
        description="Confirmation message that will be posted back in Teams",
    )

    # ── Submit state ─────────────────────────────────────────────────────────
    submitted: bool = Field(
        default=False,
        description="True once the action has been executed against the live APIs",
    )
    submitted_jira_key: str | None = Field(
        default=None,
        description="Jira key after submission (new key for CREATE, same key for UPDATE)",
    )

    @classmethod
    def from_decision(cls, d: DecisionItem) -> "DecisionResponse":
        """Build a DecisionResponse from an internal DecisionItem."""
        return cls(
            message_id=d.message_id,
            sender=d.sender,
            message_text=d.message_text,
            client_name=d.client_name,
            core_request=d.core_request,
            arr=d.arr,
            arr_formatted=format_arr(d.arr),
            action=d.action,
            jira_key=d.jira_key,
            draft_summary=d.draft_summary,
            draft_description=d.draft_description,
            draft_comment=d.draft_comment,
            draft_labels=d.draft_labels,
            teams_feedback=d.teams_feedback,
            submitted=d.submitted,
            submitted_jira_key=d.submitted_jira_key,
        )
