"""
models/integrations/jira.py
----------------------------
Pydantic models for data returned by the Jira Cloud REST API client.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class JiraIssue(BaseModel):
    """
    Lightweight Jira issue used for duplicate detection.
    Contains only the fields needed for semantic comparison against Teams messages.
    """

    key: str = Field(..., description="Jira issue key, e.g. 'JIRA-1042'")
    summary: str = Field(..., description="Issue title line")
    status: str = Field(..., description="Workflow status, e.g. 'To Do', 'In Progress'")
    description_text: str = Field(
        default="",
        description="Plain-text description (Atlassian Document Format stripped)",
    )


class JiraIssueRef(BaseModel):
    """
    Minimal reference returned after creating a new Jira issue.
    Contains only the identifiers needed to link back to the ticket.
    """

    id: str = Field(..., description="Jira internal numeric issue ID")
    key: str = Field(..., description="Human-readable issue key, e.g. 'JIRA-1200'")
    self_url: str = Field(
        ...,
        alias="self",
        description="REST URL of the created issue",
    )

    model_config = {"populate_by_name": True}


class JiraComment(BaseModel):
    """A comment successfully added to a Jira issue."""

    id: str = Field(..., description="Unique comment ID")
    issue_key: str = Field(
        ...,
        description="Key of the issue the comment was added to",
    )
