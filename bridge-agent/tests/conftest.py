"""
Root conftest — sets required environment variables before any app module
is imported. pydantic-settings reads os.environ at Settings() instantiation
time, so these must be in place before the first import of config.py.
"""

import os

# Provide test values for all required settings fields.
# Real env vars (from .env or shell) take precedence via setdefault.
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test")
os.environ.setdefault("JIRA_EMAIL", "test@workflex.com")
os.environ.setdefault("JIRA_API_TOKEN", "jira-token-test")
os.environ.setdefault("HUBSPOT_API_TOKEN", "hs-pat-test")
os.environ.setdefault("TEAMS_CLIENT_SECRET", "teams-secret-test")
os.environ.setdefault("MOCK_BASE_URL", "http://localhost:8080")
os.environ.setdefault("API_KEY", "")

import pytest
from models import DecisionItem


@pytest.fixture
def sample_decision() -> DecisionItem:
    return DecisionItem(
        message_id="msg-001",
        sender="Lisa Brandt",
        message_text="Hooli wants SSO via SAML",
        client_name="Hooli Inc.",
        core_request="SSO via SAML",
        arr=520000,
        action="CREATE",
        draft_summary="Implement SAML-based SSO",
        draft_description="Hooli needs SAML SSO for their security team.",
        draft_labels=["feature-request", "enterprise"],
        teams_feedback="Got it! Created #JIRA-??? for Hooli Inc. ($520k ARR)",
    )


@pytest.fixture
def submitted_decision(sample_decision) -> DecisionItem:
    sample_decision.submitted = True
    sample_decision.submitted_jira_key = "JIRA-1200"
    return sample_decision


@pytest.fixture
def skip_decision() -> DecisionItem:
    return DecisionItem(
        message_id="msg-061",
        sender="Lisa Brandt",
        message_text="Does anyone have the wifi password?",
        client_name="Unknown",
        core_request="",
        action="SKIP",
    )


TEST_API_KEY = "test-key-abc123"
