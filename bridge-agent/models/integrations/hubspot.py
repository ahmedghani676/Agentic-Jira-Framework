"""
models/integrations/hubspot.py
-------------------------------
Pydantic models for data returned by the HubSpot CRM API client.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class HubSpotCompany(BaseModel):
    """A company record retrieved from HubSpot CRM."""

    company_name: str = Field(
        ...,
        description="Canonical company name as stored in HubSpot",
    )
    arr: int | None = Field(
        default=None,
        description="Annual Recurring Revenue in USD, or None if unavailable",
    )
