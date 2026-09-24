"""A new login clears credentials that can no longer be used, and never fails over it.

The pruning rule itself runs against a real PostgreSQL schema in
test_token_transactions_postgres.py; these tests cover when it is called.
"""
from __future__ import annotations

from src.api import db
from src.api import state as state_module

USER = {"user_id": "u-1", "email": "student@uow.edu.au", "role": "student",
        "enrolled_courses": []}


def _state(monkeypatch, prune):
    state = state_module.APIState(fixtures={})
    monkeypatch.setattr(state, "_db_available", True)
    monkeypatch.setattr(db, "insert_token_pair", lambda *args, **kwargs: None)
    monkeypatch.setattr(db, "prune_expired_tokens", prune)
    return state


def test_a_new_login_prunes_expired_credentials(monkeypatch):
    calls = []
    state = _state(monkeypatch, lambda: calls.append(1) or 0)
    tokens = state.issue_tokens(USER)
    assert tokens and tokens.get("access_token")
    assert calls == [1]


def test_a_pruning_failure_does_not_fail_the_login(monkeypatch):
    def broken():
        raise RuntimeError("database went away")
    state = _state(monkeypatch, broken)
    tokens = state.issue_tokens(USER)
    assert tokens and tokens.get("access_token") and tokens.get("refresh_token")
