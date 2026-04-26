"""Unit tests for services/agent_service.py — AgentService."""

from unittest.mock import MagicMock, patch

import pytest

from agent.exceptions import AgentLoopError, AgentTimeoutError
from services.agent_service import (
    AgentService,
    RunAlreadySubmittedError,
    RunNotFoundError,
)


@pytest.fixture
def service() -> AgentService:
    return AgentService()


# ---------------------------------------------------------------------------
# process_messages — happy path
# ---------------------------------------------------------------------------

def test_process_messages_returns_process_response(service, sample_decision):
    with patch("services.agent_service.process", return_value=[sample_decision]), \
         patch("services.agent_service.session_store"):
        result = service.process_messages()

    assert result.total == 1
    assert result.run_id != ""
    assert len(result.decisions) == 1


def test_process_messages_generates_run_id(service, sample_decision):
    with patch("services.agent_service.process", return_value=[sample_decision]), \
         patch("services.agent_service.session_store"):
        result = service.process_messages()

    assert len(result.run_id) == 36  # UUID4 format


def test_process_messages_saves_to_session_store(service, sample_decision):
    mock_store = MagicMock()
    with patch("services.agent_service.process", return_value=[sample_decision]), \
         patch("services.agent_service.session_store", mock_store):
        result = service.process_messages()

    mock_store.save.assert_called_once_with(result.run_id, [sample_decision])


def test_process_messages_generates_unique_run_ids(service, sample_decision):
    with patch("services.agent_service.process", return_value=[sample_decision]), \
         patch("services.agent_service.session_store"):
        r1 = service.process_messages()
        r2 = service.process_messages()

    assert r1.run_id != r2.run_id


def test_process_messages_empty_decisions(service):
    with patch("services.agent_service.process", return_value=[]), \
         patch("services.agent_service.session_store"):
        result = service.process_messages()

    assert result.total == 0
    assert result.decisions == []


# ---------------------------------------------------------------------------
# process_messages — agent exceptions propagate
# ---------------------------------------------------------------------------

def test_process_messages_propagates_agent_timeout_error(service):
    with patch("services.agent_service.process", side_effect=AgentTimeoutError()):
        with pytest.raises(AgentTimeoutError):
            service.process_messages()


def test_process_messages_propagates_agent_loop_error(service):
    with patch("services.agent_service.process", side_effect=AgentLoopError(50)):
        with pytest.raises(AgentLoopError):
            service.process_messages()


# ---------------------------------------------------------------------------
# submit_decisions — happy path
# ---------------------------------------------------------------------------

def test_submit_decisions_returns_submit_response(service, sample_decision):
    mock_store = MagicMock()
    mock_store.get.return_value = [sample_decision]

    with patch("services.agent_service.session_store", mock_store), \
         patch("services.agent_service.submit", return_value=[sample_decision]):
        result = service.submit_decisions("run-123")

    assert result.run_id == "run-123"


def test_submit_decisions_counts_submitted(service, sample_decision, submitted_decision):
    mock_store = MagicMock()
    mock_store.get.return_value = [sample_decision]

    with patch("services.agent_service.session_store", mock_store), \
         patch("services.agent_service.submit", return_value=[submitted_decision]):
        result = service.submit_decisions("run-123")

    assert result.submitted == 1


def test_submit_decisions_all_skip_returns_zero_count(service, skip_decision):
    mock_store = MagicMock()
    mock_store.get.return_value = [skip_decision]

    with patch("services.agent_service.session_store", mock_store), \
         patch("services.agent_service.submit", return_value=[skip_decision]):
        result = service.submit_decisions("run-123")

    assert result.submitted == 0


# ---------------------------------------------------------------------------
# submit_decisions — error cases
# ---------------------------------------------------------------------------

def test_submit_decisions_raises_run_not_found(service):
    mock_store = MagicMock()
    mock_store.get.return_value = None

    with patch("services.agent_service.session_store", mock_store):
        with pytest.raises(RunNotFoundError) as exc_info:
            service.submit_decisions("ghost-run")

    assert exc_info.value.run_id == "ghost-run"


def test_submit_decisions_raises_already_submitted(service, submitted_decision):
    mock_store = MagicMock()
    mock_store.get.return_value = [submitted_decision]

    with patch("services.agent_service.session_store", mock_store):
        with pytest.raises(RunAlreadySubmittedError) as exc_info:
            service.submit_decisions("run-123")

    assert exc_info.value.run_id == "run-123"


def test_submit_decisions_raises_already_submitted_if_any_submitted(
    service, sample_decision, submitted_decision
):
    mock_store = MagicMock()
    mock_store.get.return_value = [sample_decision, submitted_decision]

    with patch("services.agent_service.session_store", mock_store):
        with pytest.raises(RunAlreadySubmittedError):
            service.submit_decisions("run-123")


# ---------------------------------------------------------------------------
# get_run — happy path and error cases
# ---------------------------------------------------------------------------

def test_get_run_returns_run_response(service, sample_decision):
    mock_store = MagicMock()
    mock_store.get.return_value = [sample_decision]

    with patch("services.agent_service.session_store", mock_store):
        result = service.get_run("run-123")

    assert result.run_id == "run-123"
    assert result.total == 1
    assert len(result.decisions) == 1


def test_get_run_raises_run_not_found(service):
    mock_store = MagicMock()
    mock_store.get.return_value = None

    with patch("services.agent_service.session_store", mock_store):
        with pytest.raises(RunNotFoundError) as exc_info:
            service.get_run("ghost-run")

    assert exc_info.value.run_id == "ghost-run"
