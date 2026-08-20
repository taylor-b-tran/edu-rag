"""Regression tests for the fixture authentication fallback (T8-27).

The API used to consult fixtures/sample_responses.json whenever Postgres
rejected a password. Because that file is committed, its demo passwords worked
as a permanent admin login that no password rotation could revoke. These tests
pin the three behaviours that close it.
"""
from __future__ import annotations

import os

import pytest

from src.api.state import APIState


DEMO_EMAIL = "admin@uow.edu.au"
DEMO_PASSWORD = "admin123"


@pytest.fixture
def state() -> APIState:
    return APIState()


def test_postgres_rejection_is_final(state, monkeypatch):
    """A wrong password against Postgres must not fall through to fixtures."""
    state._db_available = True
    monkeypatch.setattr(state, "_authenticate_via_postgres", lambda email, password: None)

    assert state.authenticate_user(DEMO_EMAIL, DEMO_PASSWORD) is None


def test_postgres_error_refuses_rather_than_falling_back(state, monkeypatch):
    """If the credential store errors we refuse, rather than reaching for the
    committed demo passwords - otherwise disrupting Postgres would be a way in."""
    def boom(email, password):
        raise RuntimeError("connection refused")

    state._db_available = True
    monkeypatch.setattr(state, "_authenticate_via_postgres", boom)

    assert state.authenticate_user(DEMO_EMAIL, DEMO_PASSWORD) is None


def test_postgres_still_authenticates_a_correct_password(state, monkeypatch):
    """The fix must not break the path that is supposed to work."""
    expected = {"user_id": "u1", "email": DEMO_EMAIL, "role": "admin"}
    state._db_available = True
    monkeypatch.setattr(state, "_authenticate_via_postgres", lambda email, password: expected)

    assert state.authenticate_user(DEMO_EMAIL, DEMO_PASSWORD) == expected


def test_fixture_auth_requires_the_env_gate(state, monkeypatch):
    """With no database, fixtures are only usable when explicitly enabled."""
    state._db_available = False
    monkeypatch.delenv("PAEDIA_ALLOW_FIXTURE_AUTH", raising=False)

    assert state.authenticate_user(DEMO_EMAIL, DEMO_PASSWORD) is None

    monkeypatch.setenv("PAEDIA_ALLOW_FIXTURE_AUTH", "1")
    assert state.authenticate_user(DEMO_EMAIL, DEMO_PASSWORD) is not None


def test_fixture_user_without_a_password_is_rejected(state, monkeypatch):
    """The comparison used to be skipped when the stored password was empty,
    so such an account authenticated against anything at all."""
    state._db_available = False
    monkeypatch.setenv("PAEDIA_ALLOW_FIXTURE_AUTH", "1")
    monkeypatch.setattr(
        state, "find_demo_user",
        lambda email: {"user_id": "u9", "email": email, "role": "admin", "password": ""},
    )

    assert state.authenticate_user("ghost@uow.edu.au", "anything at all") is None


def test_wrong_fixture_password_is_rejected(state, monkeypatch):
    state._db_available = False
    monkeypatch.setenv("PAEDIA_ALLOW_FIXTURE_AUTH", "1")

    assert state.authenticate_user(DEMO_EMAIL, "not-the-password") is None
