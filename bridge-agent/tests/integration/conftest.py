"""Integration test fixtures — shared app client with mocked service."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from config import settings
from core.app import create_app
from services.dependencies import get_agent_service
from tests.conftest import TEST_API_KEY


@pytest.fixture
def mock_service() -> MagicMock:
    return MagicMock()


@pytest.fixture
def client(mock_service, monkeypatch) -> TestClient:
    monkeypatch.setattr(settings, "api_key", TEST_API_KEY)
    app = create_app()
    app.dependency_overrides[get_agent_service] = lambda: mock_service
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture
def auth_headers() -> dict:
    return {"X-API-Key": TEST_API_KEY}
