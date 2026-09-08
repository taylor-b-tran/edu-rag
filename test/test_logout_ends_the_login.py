"""Logging out has to end the login, not just the credential you presented.

`/auth/logout` retired the access token and nothing else. Before this change:

    before logout, /auth/me         -> 200
    logout                          -> 200
    old access token, /auth/me      -> 401   correct
    refresh token after logout      -> issues a new access token
    new token, /auth/me             -> 200

So logout reported success, the screen returned to the login form, and the
session could be rebuilt in full from a credential logout was supposed to have
ended. It read as working because the half anyone checks — the access token —
really was revoked.

The pair issued by one login now share a `family_id`, and logout sweeps the
family. That matters more than passing the refresh token to the logout call,
which the UI already did and the server ignored: after a page reload the
browser holds only the access token, because the refresh token is deliberately
not put in a cookie. A fix that depended on the client sending it would work
in the tab you signed in on and fail in the one you came back to.

Rotation stays inside the family, so a session that has refreshed ten times is
still one logout away from over.
"""
from __future__ import annotations

import time

import pytest

from src.api import db as db_mod
from src.api.app import create_app
from src.api.state import APIState


STUDENT = ("student@uow.edu.au", "student123")
LECTURER = ("lecturer@uow.edu.au", "lecturer123")


@pytest.fixture
def client():
    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client()


def _login(client, who=STUDENT) -> dict:
    email, password = who
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.get_json()
    return resp.get_json()


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _me(client, token: str) -> int:
    return client.get("/api/auth/me", headers=_auth(token)).status_code


def _refresh(client, token: str):
    return client.post("/api/auth/refresh", json={"refresh_token": token})


# --- the fault itself --------------------------------------------------

def test_the_refresh_token_dies_with_the_login(client):
    """The exact failing sequence, as one test."""
    session = _login(client)
    assert _me(client, session["access_token"]) == 200

    client.post("/api/auth/logout", headers=_auth(session["access_token"]))

    assert _refresh(client, session["refresh_token"]).status_code == 401


def test_the_access_token_is_still_rejected_after_logout(client):
    """The half that already worked. It has to keep working."""
    session = _login(client)
    client.post("/api/auth/logout", headers=_auth(session["access_token"]))

    assert _me(client, session["access_token"]) == 401


def test_logout_leaves_nothing_that_can_rebuild_the_session(client):
    """End to end, the way an attacker holding the refresh token would try it."""
    session = _login(client)
    client.post("/api/auth/logout", headers=_auth(session["access_token"]))

    revived = _refresh(client, session["refresh_token"])
    assert revived.status_code == 401
    assert "access_token" not in (revived.get_json() or {})


# --- rotation must not escape the family -------------------------------

def test_a_login_that_has_refreshed_can_still_be_logged_out(client):
    """/auth/refresh mints a new pair. If that pair started a new family, the
    session would drift out of reach of logout after the first renewal — which
    is precisely when a long-lived session needs revoking."""
    session = _login(client)
    rotated = _refresh(client, session["refresh_token"]).get_json()

    client.post("/api/auth/logout", headers=_auth(rotated["access_token"]))

    assert _me(client, rotated["access_token"]) == 401
    assert _refresh(client, rotated["refresh_token"]).status_code == 401


def test_the_spent_refresh_token_stays_spent(client):
    """Rotation retires the old one; the family sweep must not resurrect it."""
    session = _login(client)
    _refresh(client, session["refresh_token"])

    assert _refresh(client, session["refresh_token"]).status_code == 401


# --- one login ends, the others do not ---------------------------------

def test_another_login_by_the_same_person_survives(client):
    """Signing out of the lab machine must not sign you out of your laptop.

    This is the line between ending a session and ending an account's access.
    The family is per login for that reason; logout-everywhere would be a
    different feature with a different button.
    """
    laptop = _login(client)
    lab = _login(client)

    client.post("/api/auth/logout", headers=_auth(lab["access_token"]))

    assert _me(client, laptop["access_token"]) == 200
    assert _refresh(client, laptop["refresh_token"]).status_code == 200


def test_another_user_is_unaffected(client):
    student = _login(client, STUDENT)
    lecturer = _login(client, LECTURER)

    client.post("/api/auth/logout", headers=_auth(student["access_token"]))

    assert _me(client, lecturer["access_token"]) == 200
    assert _refresh(client, lecturer["refresh_token"]).status_code == 200


# --- the edges of the endpoint -----------------------------------------

def test_logout_with_no_credentials_is_harmless(client):
    resp = client.post("/api/auth/logout")
    assert resp.status_code == 200


def test_logout_with_only_a_refresh_token_still_ends_it(client):
    """The client has the access token in a cookie and the refresh token in
    memory; a reload leaves it holding only one of them. Either one on its own
    has to be enough to end the login."""
    session = _login(client)

    client.post("/api/auth/logout", json={"refresh_token": session["refresh_token"]})

    assert _refresh(client, session["refresh_token"]).status_code == 401


def test_a_malformed_logout_body_does_not_break_logout(client):
    session = _login(client)
    resp = client.post("/api/auth/logout", headers=_auth(session["access_token"]),
                       data="not json", content_type="application/json")

    assert resp.status_code == 200
    assert _me(client, session["access_token"]) == 401


# --- the family, at the level it is built ------------------------------

USER = {"user_id": "u-1", "email": "someone@uow.edu.au", "role": "student",
        "enrolled_courses": ["CSIT321"]}


def test_the_pair_issued_together_share_a_family():
    state = APIState()
    tokens = state.issue_tokens(USER)

    access = state.access_tokens[tokens["access_token"]]
    refresh = state.refresh_tokens[tokens["refresh_token"]]
    assert access["family_id"] == refresh["family_id"]
    assert access["family_id"]


def test_two_logins_get_different_families():
    state = APIState()
    first = state.issue_tokens(USER)
    second = state.issue_tokens(USER)

    assert (state.access_tokens[first["access_token"]]["family_id"]
            != state.access_tokens[second["access_token"]]["family_id"])


def test_reissuing_inside_a_family_keeps_it():
    state = APIState()
    first = state.issue_tokens(USER)
    family = state.access_tokens[first["access_token"]]["family_id"]

    second = state.issue_tokens(USER, family_id=family)

    assert state.access_tokens[second["access_token"]]["family_id"] == family
    assert state.refresh_tokens[second["refresh_token"]]["family_id"] == family


def test_a_credential_issued_before_families_can_still_be_logged_out():
    """Rows written before this change carry no family_id, and the column is
    nullable so they keep working rather than being invalidated wholesale. For
    those, the refresh token passed in the body is the only handle there is."""
    state = APIState()
    tokens = state.issue_tokens(USER)
    for store, key in ((state.access_tokens, "access_token"),
                       (state.refresh_tokens, "refresh_token")):
        store[tokens[key]].pop("family_id", None)

    state.revoke_login(tokens["access_token"], tokens["refresh_token"])

    assert tokens["access_token"] not in state.access_tokens
    assert tokens["refresh_token"] not in state.refresh_tokens


# --- and across workers, which is where revocation usually leaks --------

class FakeTokenStore:
    """The rows two workers would share, standing in for Postgres."""

    def __init__(self):
        self.rows: dict[tuple[str, str], dict] = {}

    def get_token(self, table, token):
        row = self.rows.get((table, token))
        return dict(row) if row is not None else None

    def delete_token(self, table, token):
        self.rows.pop((table, token), None)

    def delete_token_family(self, family_id):
        doomed = [key for key, row in self.rows.items()
                  if row.get("family_id") == family_id]
        for key in doomed:
            del self.rows[key]
        return len(doomed)

    def insert(self, table, token, payload):
        self.rows[(table, token)] = dict(payload)


@pytest.fixture
def shared(monkeypatch):
    store = FakeTokenStore()
    monkeypatch.setattr(db_mod, "get_token", store.get_token)
    monkeypatch.setattr(db_mod, "delete_token", store.delete_token)
    monkeypatch.setattr(db_mod, "delete_token_family", store.delete_token_family)
    return store


def _worker(access=None, refresh=None):
    state = APIState()
    state._db_available = True
    state.access_tokens = dict(access or {})
    state.refresh_tokens = dict(refresh or {})
    return state


def test_logout_on_one_worker_kills_the_refresh_token_on_the_other(shared):
    """gunicorn runs two workers with separate memory. Sweeping only this
    worker's dictionaries would leave the other one refreshing happily —
    the same shape as the logout bug T8-22 fixed for access tokens."""
    payload = {**USER, "family_id": "fam-1", "expires_at": time.time() + 3600}
    shared.insert("access_tokens", "acc-1", payload)
    shared.insert("refresh_tokens", "ref-1", payload)

    worker_a = _worker({"acc-1": payload}, {"ref-1": payload})
    worker_b = _worker({"acc-1": payload}, {"ref-1": payload})

    worker_a.revoke_login("acc-1")

    assert worker_b.validate_bearer("Bearer acc-1") is None
    assert worker_b.consume_refresh_token("ref-1") is None


def test_the_sweep_clears_this_workers_copies_too(shared):
    payload = {**USER, "family_id": "fam-1", "expires_at": time.time() + 3600}
    shared.insert("access_tokens", "acc-1", payload)
    shared.insert("refresh_tokens", "ref-1", payload)
    worker = _worker({"acc-1": payload}, {"ref-1": payload})

    worker.revoke_login("acc-1")

    assert "acc-1" not in worker.access_tokens
    assert "ref-1" not in worker.refresh_tokens


def test_a_different_familys_tokens_are_left_alone(shared):
    mine = {**USER, "family_id": "fam-1", "expires_at": time.time() + 3600}
    theirs = {**USER, "family_id": "fam-2", "expires_at": time.time() + 3600}
    shared.insert("access_tokens", "acc-1", mine)
    shared.insert("refresh_tokens", "ref-1", mine)
    shared.insert("access_tokens", "acc-2", theirs)
    shared.insert("refresh_tokens", "ref-2", theirs)

    worker = _worker({"acc-1": mine, "acc-2": theirs},
                     {"ref-1": mine, "ref-2": theirs})
    worker.revoke_login("acc-1")

    assert worker.validate_bearer("Bearer acc-2") is not None
    assert worker.consume_refresh_token("ref-2") is not None
