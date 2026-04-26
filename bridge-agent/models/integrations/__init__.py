"""
models/integrations/__init__.py
--------------------------------
Re-exports all external service integration models.

File breakdown
--------------
  jira.py     — JiraIssue, JiraIssueRef, JiraComment
  hubspot.py  — HubSpotCompany
  teams.py    — TeamsMessage, TeamsSentMessage
"""

from models.integrations.jira import JiraComment, JiraIssue, JiraIssueRef
from models.integrations.hubspot import HubSpotCompany
from models.integrations.teams import TeamsMessage, TeamsSentMessage

__all__ = [
    "JiraIssue",
    "JiraIssueRef",
    "JiraComment",
    "HubSpotCompany",
    "TeamsMessage",
    "TeamsSentMessage",
]
