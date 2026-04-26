"""Unit tests for store/session.py — SessionStore."""

import pytest
from store.session import SessionStore
from models import DecisionItem


@pytest.fixture
def store() -> SessionStore:
    return SessionStore()


@pytest.fixture
def decision() -> DecisionItem:
    return DecisionItem(
        message_id="msg-001",
        sender="Alice",
        message_text="SSO request",
        client_name="Hooli",
        action="CREATE",
    )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_save_and_get_returns_decisions(store, decision):
    store.save("run-1", [decision])
    result = store.get("run-1")
    assert result == [decision]


def test_exists_returns_true_after_save(store, decision):
    store.save("run-1", [decision])
    assert store.exists("run-1") is True


def test_save_empty_list(store):
    store.save("run-empty", [])
    assert store.get("run-empty") == []


def test_get_returns_same_object_reference(store, decision):
    store.save("run-1", [decision])
    result = store.get("run-1")
    assert result is store.get("run-1")


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_get_unknown_run_id_returns_none(store):
    assert store.get("does-not-exist") is None


def test_exists_returns_false_before_save(store):
    assert store.exists("does-not-exist") is False


def test_save_overwrites_existing_run_id(store, decision):
    store.save("run-1", [decision])

    new_decision = DecisionItem(
        message_id="msg-002",
        sender="Bob",
        message_text="RBAC request",
        client_name="Initech",
        action="UPDATE",
    )
    store.save("run-1", [new_decision])

    result = store.get("run-1")
    assert len(result) == 1
    assert result[0].message_id == "msg-002"


def test_multiple_run_ids_are_independent(store, decision):
    d2 = DecisionItem(
        message_id="msg-002",
        sender="Bob",
        message_text="RBAC request",
        client_name="Initech",
        action="SKIP",
    )
    store.save("run-A", [decision])
    store.save("run-B", [d2])

    assert store.get("run-A")[0].message_id == "msg-001"
    assert store.get("run-B")[0].message_id == "msg-002"


def test_fresh_store_is_empty(store):
    assert store.get("any-id") is None
    assert store.exists("any-id") is False
