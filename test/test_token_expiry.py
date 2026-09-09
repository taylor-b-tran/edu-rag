"""Tests for token lifetime and refresh handling (T8-22).

`expires_in: 3600` was reported to every client but never enforced —
`validate_bearer` did a plain dictionary lookup, so every token ever issued
stayed valid for the life of the process, and rotating a password did not
invalidate anything already handed out.

The tokens are deliberately opaque and held server-side rather than JWTs, which
is what makes logout and expiry take effect immediately. `api_spec.yaml` used
to advertise JWT and has been corrected to match.
"""
from __future__ import annotations

import time

import pytest

from src.api import state as state_mod
from src.api.app import create_app
from src.api.state import APIState


@pytest.fixture
def client():
    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client()


@pytest.fixture
def api_state():
    return APIState()


USER = {"user_id": "u-1", "email": "someone@uow.edu.au", "role": "student",
        "enrolled_courses": ["CSIT321"]}


def _bearer(token: str) -> str:
    return f"Bearer {token}"


# ─── access tokens ────────────────────────────────────────────────────

def test_a_fresh_token_is_accepted(api_state):
    tokens = api_state.issue_tokens(USER)
    assert api_state.validate_bearer(_bearer(tokens["access_token"])) is not None


def test_an_expired_token_is_rejected(api_state):
    tokens = api_state.issue_tokens(USER)
    token = tokens["access_token"]
    # Move the expiry into the past rather than sleeping for an hour.
    api_state.access_tokens[token]["expires_at"] = time.time() - 1

    assert api_state.validate_bearer(_bearer(token)) is None


def test_expired_access_remains_a_logout_handle_but_cannot_authenticate(api_state):
    """Expiry denies access without losing the link needed to revoke refresh."""
    tokens = api_state.issue_tokens(USER)
    token = tokens["access_token"]
    api_state.access_tokens[token]["expires_at"] = time.time() - 1

    api_state.validate_bearer(_bearer(token))

    assert token in api_state.access_tokens
    api_state.revoke_login(token)
    assert token not in api_state.access_tokens
    assert tokens["refresh_token"] not in api_state.refresh_tokens


def test_expires_in_matches_the_configured_lifetime(api_state):
    """The number reported to clients has to be the one actually enforced."""
    tokens = api_state.issue_tokens(USER)
    assert tokens["expires_in"] == state_mod.ACCESS_TOKEN_TTL_SECONDS

    issued = api_state.access_tokens[tokens["access_token"]]["expires_at"]
    assert abs(issued - (time.time() + state_mod.ACCESS_TOKEN_TTL_SECONDS)) < 5


def test_unknown_and_malformed_tokens_are_rejected(api_state):
    assert api_state.validate_bearer(_bearer("not-a-real-token")) is None
    assert api_state.validate_bearer("Basic abc") is None
    assert api_state.validate_bearer("Bearer") is None
    assert api_state.validate_bearer(None) is None


# ─── refresh tokens ───────────────────────────────────────────────────

def test_refresh_token_can_only_be_used_once(api_state):
    """A captured refresh token should be useless once the real holder spends it."""
    tokens = api_state.issue_tokens(USER)
    rt = tokens["refresh_token"]

    assert api_state.consume_refresh_token(rt) is not None
    assert api_state.consume_refresh_token(rt) is None


def test_expired_refresh_token_is_rejected(api_state):
    tokens = api_state.issue_tokens(USER)
    rt = tokens["refresh_token"]
    api_state.refresh_tokens[rt]["expires_at"] = time.time() - 1

    assert api_state.consume_refresh_token(rt) is None


def test_refresh_tokens_outlive_access_tokens(api_state):
    assert state_mod.REFRESH_TOKEN_TTL_SECONDS > state_mod.ACCESS_TOKEN_TTL_SECONDS


# ─── through the HTTP layer ───────────────────────────────────────────

def test_refresh_endpoint_rejects_a_reused_token(client):
    login = client.post("/api/auth/login",
                        json={"email": "student@uow.edu.au", "password": "student123"})
    assert login.status_code == 200
    rt = login.get_json()["refresh_token"]

    first = client.post("/api/auth/refresh", json={"refresh_token": rt})
    assert first.status_code == 200

    second = client.post("/api/auth/refresh", json={"refresh_token": rt})
    assert second.status_code == 401


def test_logout_still_revokes_immediately(client):
    """The reason for holding tokens server-side in the first place."""
    login = client.post("/api/auth/login",
                        json={"email": "student@uow.edu.au", "password": "student123"})
    token = login.get_json()["access_token"]
    headers = {"Authorization": _bearer(token)}

    assert client.get("/api/sessions", headers=headers).status_code == 200
    client.post("/api/auth/logout", headers=headers)
    assert client.get("/api/sessions", headers=headers).status_code == 401
