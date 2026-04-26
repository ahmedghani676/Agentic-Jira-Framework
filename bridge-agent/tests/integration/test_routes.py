"""Integration tests for all HTTP routes — happy paths, edge cases, and auth."""

import pytest
from unittest.mock import MagicMock

from constants import ErrorMessages, HTTPStatus
from models import ProcessResponse, RunResponse, SubmitResponse, DecisionResponse
from services.agent_service import RunAlreadySubmittedError, RunNotFoundError
from tests.conftest import TEST_API_KEY


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _process_response(run_id: str = "run-abc") -> ProcessResponse:
    return ProcessResponse(run_id=run_id, total=0, decisions=[])


def _submit_response(run_id: str = "run-abc") -> SubmitResponse:
    return SubmitResponse(run_id=run_id, submitted=1, decisions=[])


def _run_response(run_id: str = "run-abc") -> RunResponse:
    return RunResponse(run_id=run_id, total=0, decisions=[])


# ---------------------------------------------------------------------------
# GET /health — no auth required
# ---------------------------------------------------------------------------

def test_health_returns_200(client):
    resp = client.get("/health")
    assert resp.status_code == HTTPStatus.OK
    assert resp.json()["status"] == "ok"


def test_health_requires_no_api_key(client):
    resp = client.get("/health")
    assert resp.status_code == HTTPStatus.OK


# ---------------------------------------------------------------------------
# GET / — UI, no auth required
# ---------------------------------------------------------------------------

def test_root_returns_200(client):
    resp = client.get("/")
    assert resp.status_code == HTTPStatus.OK


# ---------------------------------------------------------------------------
# POST /api/process
# ---------------------------------------------------------------------------

def test_process_happy_path(client, mock_service, auth_headers):
    mock_service.process_messages.return_value = _process_response("run-abc")

    resp = client.post("/api/process", headers=auth_headers)

    assert resp.status_code == HTTPStatus.OK
    assert resp.json()["run_id"] == "run-abc"
    mock_service.process_messages.assert_called_once()


def test_process_service_exception_returns_500(client, mock_service, auth_headers):
    mock_service.process_messages.side_effect = RuntimeError("upstream failure")

    resp = client.post("/api/process", headers=auth_headers)

    assert resp.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert resp.json()["detail"] == ErrorMessages.PROCESS_FAILED


def test_process_returns_total_and_decisions(client, mock_service, auth_headers):
    d = DecisionResponse(
        message_id="msg-001",
        sender="Alice",
        message_text="SSO request",
        client_name="Hooli",
        action="CREATE",
        submitted=False,
    )
    mock_service.process_messages.return_value = ProcessResponse(
        run_id="run-abc", total=1, decisions=[d]
    )

    resp = client.post("/api/process", headers=auth_headers)

    body = resp.json()
    assert body["total"] == 1
    assert len(body["decisions"]) == 1
    assert body["decisions"][0]["action"] == "CREATE"


# ---------------------------------------------------------------------------
# POST /api/submit
# ---------------------------------------------------------------------------

def test_submit_happy_path(client, mock_service, auth_headers):
    mock_service.submit_decisions.return_value = _submit_response("run-abc")

    resp = client.post("/api/submit", json={"run_id": "run-abc"}, headers=auth_headers)

    assert resp.status_code == HTTPStatus.OK
    assert resp.json()["submitted"] == 1
    mock_service.submit_decisions.assert_called_once_with("run-abc")


def test_submit_run_not_found_returns_404(client, mock_service, auth_headers):
    mock_service.submit_decisions.side_effect = RunNotFoundError("ghost-run")

    resp = client.post("/api/submit", json={"run_id": "ghost-run"}, headers=auth_headers)

    assert resp.status_code == HTTPStatus.NOT_FOUND
    assert "ghost-run" in resp.json()["detail"]


def test_submit_already_submitted_returns_409(client, mock_service, auth_headers):
    mock_service.submit_decisions.side_effect = RunAlreadySubmittedError("run-abc")

    resp = client.post("/api/submit", json={"run_id": "run-abc"}, headers=auth_headers)

    assert resp.status_code == HTTPStatus.CONFLICT
    assert resp.json()["detail"] == ErrorMessages.RUN_ALREADY_SUBMITTED


def test_submit_service_exception_returns_500(client, mock_service, auth_headers):
    mock_service.submit_decisions.side_effect = RuntimeError("boom")

    resp = client.post("/api/submit", json={"run_id": "run-abc"}, headers=auth_headers)

    assert resp.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert resp.json()["detail"] == ErrorMessages.SUBMIT_FAILED


def test_submit_missing_body_returns_422(client, auth_headers):
    resp = client.post("/api/submit", headers=auth_headers)
    assert resp.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_submit_missing_run_id_field_returns_422(client, auth_headers):
    resp = client.post("/api/submit", json={}, headers=auth_headers)
    assert resp.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


# ---------------------------------------------------------------------------
# GET /api/runs/{run_id}
# ---------------------------------------------------------------------------

def test_get_run_happy_path(client, mock_service, auth_headers):
    mock_service.get_run.return_value = _run_response("run-abc")

    resp = client.get("/api/runs/run-abc", headers=auth_headers)

    assert resp.status_code == HTTPStatus.OK
    assert resp.json()["run_id"] == "run-abc"
    mock_service.get_run.assert_called_once_with("run-abc")


def test_get_run_not_found_returns_404(client, mock_service, auth_headers):
    mock_service.get_run.side_effect = RunNotFoundError("ghost-run")

    resp = client.get("/api/runs/ghost-run", headers=auth_headers)

    assert resp.status_code == HTTPStatus.NOT_FOUND
    assert "ghost-run" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Auth middleware
# ---------------------------------------------------------------------------

def test_missing_api_key_returns_401(client):
    resp = client.post("/api/process")
    assert resp.status_code == HTTPStatus.UNAUTHORIZED
    assert resp.json()["detail"] == ErrorMessages.UNAUTHORIZED


def test_wrong_api_key_returns_401(client):
    resp = client.post("/api/process", headers={"X-API-Key": "wrong-key"})
    assert resp.status_code == HTTPStatus.UNAUTHORIZED


def test_correct_api_key_passes_through(client, mock_service, auth_headers):
    mock_service.process_messages.return_value = _process_response()
    resp = client.post("/api/process", headers=auth_headers)
    assert resp.status_code == HTTPStatus.OK


def test_health_bypasses_auth(client):
    # No API key — health must still return 200
    resp = client.get("/health")
    assert resp.status_code == HTTPStatus.OK


def test_root_bypasses_auth(client):
    resp = client.get("/")
    assert resp.status_code == HTTPStatus.OK


def test_auth_disabled_when_api_key_not_configured(mock_service, monkeypatch):
    from config import settings
    from core.app import create_app
    from services.dependencies import get_agent_service

    monkeypatch.setattr(settings, "api_key", "")
    app = create_app()
    app.dependency_overrides[get_agent_service] = lambda: mock_service
    mock_service.process_messages.return_value = _process_response()

    with TestClient(app) as c:
        # No X-API-Key header — should pass when api_key is empty
        resp = c.post("/api/process")

    assert resp.status_code == HTTPStatus.OK


# ---------------------------------------------------------------------------
# Import needed for the last test
# ---------------------------------------------------------------------------

from fastapi.testclient import TestClient
