"""Two authentication defects.

Demo accounts: a deployment that did not set the demo passwords seeded admin123, lecturer123 and
student123 — passwords printed on the old login screen and README, the admin included.

Token-store outage: during a database outage every authenticated route answered 401, which the
interface reads as "signed out", so a brief outage ended real sessions. It must be a 503.
"""
from __future__ import annotations

import inspect
import logging

import pytest

from src.api import db
from src.api.app import create_app

LITERALS = ("admin123", "lecturer123", "student123")
ENV_KEYS = ("PAEDIA_DEMO_ADMIN_PASSWORD", "PAEDIA_DEMO_LECTURER_PASSWORD",
            "PAEDIA_DEMO_STUDENT_PASSWORD")


# --- demo account passwords ----------------------------------------------------

def test_no_demo_password_is_written_in_the_source():
    source = inspect.getsource(db)
    for literal in LITERALS:
        assert literal not in source, literal


def test_an_unset_variable_gives_a_random_password(monkeypatch):
    monkeypatch.delenv("PAEDIA_DEMO_ADMIN_PASSWORD", raising=False)
    first, from_env = db._demo_password("PAEDIA_DEMO_ADMIN_PASSWORD")
    second, _ = db._demo_password("PAEDIA_DEMO_ADMIN_PASSWORD")
    assert from_env is False
    assert first != second
    assert len(first) >= 32
    assert first not in LITERALS


def test_a_set_variable_is_used(monkeypatch):
    monkeypatch.setenv("PAEDIA_DEMO_STUDENT_PASSWORD", "  chosen-by-the-operator  ")
    assert db._demo_password("PAEDIA_DEMO_STUDENT_PASSWORD") == ("chosen-by-the-operator", True)


def test_seed_rows_carry_no_known_password(monkeypatch):
    import bcrypt
    for key in ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    for _user, _email, _role, password_hash, from_env, _key in db._demo_seed_rows():
        assert from_env is False
        for literal in LITERALS:
            assert not bcrypt.checkpw(literal.encode(), password_hash.encode())


class _Cursor:
    """Records statements; fetchone answers as INSERT ... RETURNING would."""

    def __init__(self, inserted: bool):
        self.inserted = inserted
        self.last = ""

    def execute(self, sql, params=None):
        self.last = sql

    def fetchone(self):
        return {"email": "x"} if self.inserted and "RETURNING" in self.last else None


@pytest.mark.parametrize("inserted, from_env, warned", [
    (True, False, True),    # new account, no variable: nobody can sign in, say so
    (False, False, False),  # account already there: left alone, nothing to say
    (True, True, False),    # variable set: a real password, nothing to warn about
])
def test_seeding_warns_only_when_it_creates_an_account_nobody_can_use(
        caplog, inserted, from_env, warned):
    rows = [("admin_demo", "admin@uow.edu.au", "admin", "hash", from_env,
             "PAEDIA_DEMO_ADMIN_PASSWORD")]
    with caplog.at_level(logging.WARNING, logger="src.api.db"):
        db._seed_demo_auth_data(_Cursor(inserted), rows)
    hit = [r for r in caplog.records if "PAEDIA_DEMO_ADMIN_PASSWORD" in r.getMessage()]
    assert bool(hit) is warned


# --- token-store outage ----------------------------------------------------------

AUTH = {"Authorization": "Bearer some-token"}


@pytest.fixture
def app_with_store(monkeypatch):
    def _make(get_token):
        from src.api.routes import query as query_mod
        query_mod._RATE_STORE.clear()
        app = create_app()
        app.config.update(TESTING=True)
        state = app.config["EDURAG_API_STATE"]
        monkeypatch.setattr(state, "_db_available", True)
        monkeypatch.setattr(db, "get_token", get_token)
        return app.test_client()
    return _make


def _store_down(table, token):
    raise RuntimeError("could not connect to server")


@pytest.mark.parametrize("method, path, body", [
    ("get", "/api/documents", None),
    ("get", "/api/courses", None),
    ("get", "/api/sessions", None),
    ("get", "/api/settings", None),
    ("post", "/api/query", {"query": "What is chunking?", "course_id": "CSIT321"}),
])
def test_an_unreadable_token_store_is_a_503_not_a_401(app_with_store, method, path, body):
    client = app_with_store(_store_down)
    response = getattr(client, method)(path, headers=AUTH, json=body)
    assert response.status_code == 503, (path, response.get_json())
    assert "retry" in response.get_json()["message"].lower()


def test_a_token_the_store_does_not_have_is_still_a_401(app_with_store):
    client = app_with_store(lambda table, token: None)
    assert client.get("/api/documents", headers=AUTH).status_code == 401


def test_no_token_at_all_is_still_a_401(app_with_store):
    client = app_with_store(_store_down)
    assert client.get("/api/documents").status_code == 401


def test_restoring_a_session_during_an_outage_is_still_a_503(app_with_store):
    client = app_with_store(_store_down)
    assert client.get("/api/auth/me", headers=AUTH).status_code == 503


def test_a_caller_can_still_opt_out_of_the_error(monkeypatch):
    app = create_app()
    state = app.config["EDURAG_API_STATE"]
    monkeypatch.setattr(state, "_db_available", True)
    monkeypatch.setattr(db, "get_token", _store_down)
    assert state.validate_bearer("Bearer t", report_store_error=False) is None
