"""Unit tests for agent/bridge.py — ToolDispatcher."""

import json
from unittest.mock import patch

import pytest

from agent.bridge import ToolDispatcher
from models import TeamsMessage, JiraIssue


@pytest.fixture
def dispatcher() -> ToolDispatcher:
    return ToolDispatcher()


@pytest.fixture
def dispatcher_with_message(dispatcher) -> ToolDispatcher:
    dispatcher.set_current_message({
        "id": "msg-001",
        "sender": "Lisa Brandt",
        "text": "Hooli wants SSO via SAML",
    })
    return dispatcher


# ---------------------------------------------------------------------------
# dispatch — routing
# ---------------------------------------------------------------------------

def test_dispatch_unknown_tool_returns_error_json(dispatcher):
    result = json.loads(dispatcher.dispatch("nonexistent_tool", {}))
    assert "error" in result
    assert "nonexistent_tool" in result["error"]


def test_dispatch_tool_exception_returns_error_json(dispatcher):
    # create_jira_ticket without set_current_message — still returns error JSON,
    # doesn't raise
    with patch("clients.jira.search_issues", return_value=[]):
        result = json.loads(dispatcher.dispatch("create_jira_ticket", {
            "summary": "SSO",
            "description": "desc",
        }))
    # Should produce a decision (not crash), not an error
    assert "planned_action" in result or "error" not in result


# ---------------------------------------------------------------------------
# get_teams_messages — caching
# ---------------------------------------------------------------------------

def test_get_teams_messages_calls_client_once(dispatcher):
    messages = [TeamsMessage(id="1", sender="Alice", text="test", created="")]
    with patch("clients.teams.get_messages", return_value=messages) as mock_get:
        dispatcher.dispatch("get_teams_messages", {"limit": 10})
        dispatcher.dispatch("get_teams_messages", {"limit": 10})

    mock_get.assert_called_once()


def test_get_teams_messages_returns_serialisable_list(dispatcher):
    messages = [TeamsMessage(id="1", sender="Alice", text="SSO request", created="2026-01-01")]
    with patch("clients.teams.get_messages", return_value=messages):
        raw = dispatcher.dispatch("get_teams_messages", {})

    data = json.loads(raw)
    assert isinstance(data, list)
    assert data[0]["id"] == "1"
    assert data[0]["sender"] == "Alice"


# ---------------------------------------------------------------------------
# get_jira_backlog — caching
# ---------------------------------------------------------------------------

def test_get_jira_backlog_calls_client_once(dispatcher):
    issues = [JiraIssue(key="JIRA-1042", summary="SSO", status="To Do", description_text="")]
    with patch("clients.jira.search_issues", return_value=issues) as mock_get:
        dispatcher.dispatch("get_jira_backlog", {})
        dispatcher.dispatch("get_jira_backlog", {})

    mock_get.assert_called_once()


def test_get_jira_backlog_returns_serialisable_list(dispatcher):
    issues = [JiraIssue(key="JIRA-1042", summary="SSO", status="To Do", description_text="SAML")]
    with patch("clients.jira.search_issues", return_value=issues):
        raw = dispatcher.dispatch("get_jira_backlog", {})

    data = json.loads(raw)
    assert data[0]["key"] == "JIRA-1042"
    assert data[0]["summary"] == "SSO"


# ---------------------------------------------------------------------------
# search_hubspot_company — context tracking
# ---------------------------------------------------------------------------

def test_search_hubspot_sets_current_client_and_arr(dispatcher):
    with patch("clients.hubspot.get_arr", return_value=520000):
        dispatcher.dispatch("search_hubspot_company", {"company_name": "Hooli"})

    assert dispatcher._current_client == "Hooli"
    assert dispatcher._current_arr == 520000


def test_search_hubspot_unknown_company_sets_none_arr(dispatcher):
    with patch("clients.hubspot.get_arr", return_value=None):
        dispatcher.dispatch("search_hubspot_company", {"company_name": "Unknown Corp"})

    assert dispatcher._current_arr is None


# ---------------------------------------------------------------------------
# create_jira_ticket — decision recording
# ---------------------------------------------------------------------------

def test_create_jira_ticket_records_create_decision(dispatcher_with_message):
    result = json.loads(dispatcher_with_message.dispatch("create_jira_ticket", {
        "summary": "Implement SSO",
        "description": "SAML 2.0 required",
        "labels": ["enterprise"],
    }))

    assert result["planned_action"] == "CREATE"
    assert result["dry_run"] is True
    assert len(dispatcher_with_message.decisions) == 1

    d = dispatcher_with_message.decisions[0]
    assert d.action == "CREATE"
    assert d.draft_summary == "Implement SSO"
    assert d.draft_description == "SAML 2.0 required"
    assert d.draft_labels == ["enterprise"]


def test_create_jira_ticket_defaults_labels_to_empty(dispatcher_with_message):
    dispatcher_with_message.dispatch("create_jira_ticket", {
        "summary": "SSO",
        "description": "desc",
    })
    assert dispatcher_with_message.decisions[0].draft_labels == []


# ---------------------------------------------------------------------------
# add_jira_comment — decision recording
# ---------------------------------------------------------------------------

def test_add_jira_comment_records_update_decision(dispatcher_with_message):
    result = json.loads(dispatcher_with_message.dispatch("add_jira_comment", {
        "issue_key": "JIRA-1042",
        "comment": "New context from Hooli.",
    }))

    assert result["planned_action"] == "UPDATE"
    assert result["issue_key"] == "JIRA-1042"

    d = dispatcher_with_message.decisions[0]
    assert d.action == "UPDATE"
    assert d.jira_key == "JIRA-1042"
    assert d.draft_comment == "New context from Hooli."


# ---------------------------------------------------------------------------
# send_teams_feedback — sets feedback on decision
# ---------------------------------------------------------------------------

def test_send_teams_feedback_sets_teams_feedback(dispatcher_with_message):
    dispatcher_with_message.dispatch("create_jira_ticket", {
        "summary": "SSO", "description": "desc",
    })
    dispatcher_with_message.dispatch("send_teams_feedback", {
        "message": "Got it! Created #JIRA-??? for Hooli.",
    })

    assert dispatcher_with_message.decisions[0].teams_feedback == "Got it! Created #JIRA-??? for Hooli."


# ---------------------------------------------------------------------------
# _get_or_create_decision — action priority logic
# ---------------------------------------------------------------------------

def test_action_upgrades_from_skip_to_create(dispatcher_with_message):
    # feedback first → creates SKIP decision
    dispatcher_with_message.dispatch("send_teams_feedback", {"message": "feedback"})
    assert dispatcher_with_message.decisions[0].action == "SKIP"

    # CREATE call upgrades it
    dispatcher_with_message.dispatch("create_jira_ticket", {
        "summary": "SSO", "description": "desc",
    })
    assert dispatcher_with_message.decisions[0].action == "CREATE"
    assert len(dispatcher_with_message.decisions) == 1  # still one decision


def test_action_does_not_downgrade_create_to_skip(dispatcher_with_message):
    dispatcher_with_message.dispatch("create_jira_ticket", {
        "summary": "SSO", "description": "desc",
    })
    dispatcher_with_message.dispatch("send_teams_feedback", {"message": "feedback"})

    assert dispatcher_with_message.decisions[0].action == "CREATE"


def test_same_message_id_returns_same_decision(dispatcher_with_message):
    dispatcher_with_message.dispatch("create_jira_ticket", {
        "summary": "SSO", "description": "desc",
    })
    dispatcher_with_message.dispatch("send_teams_feedback", {"message": "feedback"})

    assert len(dispatcher_with_message.decisions) == 1


def test_different_message_ids_create_separate_decisions(dispatcher):
    dispatcher.set_current_message({"id": "msg-001", "sender": "A", "text": "SSO"})
    dispatcher.dispatch("create_jira_ticket", {"summary": "SSO", "description": "desc"})

    dispatcher.set_current_message({"id": "msg-002", "sender": "B", "text": "RBAC"})
    dispatcher.dispatch("add_jira_comment", {"issue_key": "JIRA-1057", "comment": "context"})

    assert len(dispatcher.decisions) == 2
    assert dispatcher.decisions[0].message_id == "msg-001"
    assert dispatcher.decisions[1].message_id == "msg-002"


def test_no_current_message_uses_unknown_id(dispatcher):
    dispatcher.dispatch("create_jira_ticket", {"summary": "SSO", "description": "desc"})
    assert dispatcher.decisions[0].message_id == "unknown"
