"""
models/integrations/teams.py
-----------------------------
Pydantic models for data returned by the Microsoft Teams Graph API client.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class TeamsMessage(BaseModel):
    """A single message fetched from the Teams #feature-requests channel."""

    id: str = Field(..., description="Teams message ID")
    sender: str = Field(..., description="Sender display name")
    text: str = Field(..., description="Plain-text message body")
    created: str = Field(default="", description="ISO-8601 creation timestamp")


class TeamsSentMessage(BaseModel):
    """Confirmation returned after successfully posting a message to Teams."""

    id: str = Field(..., description="ID of the newly created Teams message")
    message: str = Field(..., description="The text that was posted")
