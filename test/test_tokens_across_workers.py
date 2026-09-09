"""Token handling once there is more than one worker (T8-22 / T8-23 / T8-24).

Three faults appeared only where those three tasks meet. Each is correct on its
own; the seam between them was not.

gunicorn runs `--workers=2`. Each worker is a separate process with its own
APIState, and `APIState.__post_init__` loads the token tables from Postgres
once, at startup. Validation was a plain dictionary lookup, so:

  * a token issued by worker A was simply absent from worker B, and roughly
    half of all requests came back 401 with a perfectly good token. Six
    concurrent queries against the live host produced four failures;
  * logout popped only the local dictionary, leaving the row in Postgres and
    the token valid on every other worker;
  * `_load_all_tokens` never selected `expires_at`, so every token reloaded
    after a restart had no expiry at all and lived forever - which quietly
    undid T8-22.

Postgres is now the source of truth whenever it is reachable. The dictionary
is still used when there is no database, which is how this suite runs, so the
tests below drive the seam directly rather than through HTTP.
"""
from __future__ import annotations

import time

import pytest

from src.api import db as db_mod
from src.api.state import APIState


USER = {"user_id": "u-1", "email": "someone@uow.edu.au", "role": "student",
        "enrolled_courses": ["CSIT321"]}


class FakeTokenStore:
    """The rows two workers would share, standing in for Postgres."""

    def __init__(self):
        self.rows: dict[tuple[str, str], dict] = {}
        self.lookups = 0

    def get_token(self, table, token):
        self.lookups += 1
        row = self.rows.get((table, token))
        return dict(row) if row is not None else None

    def delete_token(self, table, token):
        self.rows.pop((table, token), None)

    def insert(self, table, token, payload):
        self.rows[(table, token)] = dict(payload)

    def consume_refresh_token(self, token):
        row = self.rows.pop(("refresh_tokens", token), None)
        return row if row and row["expires_at"] > time.time() else None


@pytest.fixture
def shared(monkeypatch):
    store = FakeTokenStore()
    monkeypatch.setattr(db_mod, "get_token", store.get_token)
    monkeypatch.setattr(db_mod, "delete_token", store.delete_token)
    monkeypatch.setattr(db_mod, "consume_refresh_token", store.consume_refresh_token)
    return store


def _worker(shared, tokens=None):
    """A worker whose in-memory dictionaries hold only what it was given -
    exactly the situation after gunicorn forks."""
    state = APIState()
    state._db_available = True
    state.access_tokens = dict(tokens or {})
    state.refresh_tokens = {}
    return state


def _issue(shared, token="tok-1", ttl=3600, table="access_tokens"):
    payload = {**USER, "expires_at": time.time() + ttl}
    shared.insert(table, token, payload)
    return payload


# --- a token issued elsewhere ----------------------------------------

def test_a_token_this_worker_never_saw_is_accepted(shared):
    """Worker B has an empty dictionary; the row exists because worker A
    issued it. This is the 401 that broke concurrent use."""
    _issue(shared)
    worker_b = _worker(shared)

    assert worker_b.validate_bearer("Bearer tok-1") is not None


def test_the_payload_comes_back_intact(shared):
    _issue(shared)
    payload = _worker(shared).validate_bearer("Bearer tok-1")

    assert payload["user_id"] == "u-1"
    assert payload["enrolled_courses"] == ["CSIT321"]


# --- logout has to reach every worker --------------------------------

def test_logout_revokes_on_a_worker_that_still_has_it_cached(shared):
    """The worker that did not handle the logout still holds a copy. Falling
    back to that copy would hand the session straight back."""
    payload = _issue(shared)
    worker_a = _worker(shared, {"tok-1": payload})
    worker_b = _worker(shared, {"tok-1": payload})

    worker_a.revoke_access_token("tok-1")

    assert worker_b.validate_bearer("Bearer tok-1") is None


def test_revoking_clears_the_local_copy_too(shared):
    payload = _issue(shared)
    worker = _worker(shared, {"tok-1": payload})

    worker.revoke_access_token("tok-1")

    assert "tok-1" not in worker.access_tokens


def test_an_unknown_token_is_rejected_without_a_cache_fallback(shared):
    worker = _worker(shared, {"ghost": {**USER, "expires_at": time.time() + 3600}})

    assert worker.validate_bearer("Bearer ghost") is None, \
        "no row in Postgres means retired; the local copy must not rescue it"


# --- expiry survives a restart ---------------------------------------

def test_an_expired_row_is_rejected(shared):
    _issue(shared, ttl=-1)

    assert _worker(shared).validate_bearer("Bearer tok-1") is None


def test_expired_access_is_retained_only_as_a_logout_family_handle(shared):
    _issue(shared, ttl=-1)
    assert _worker(shared).validate_bearer("Bearer tok-1") is None
    assert shared.rows.get(("access_tokens", "tok-1")) is not None


def test_loaded_rows_carry_an_expiry(shared):
    """`_load_all_tokens` omitted expires_at, so anything reloaded after a
    restart was treated as immortal."""
    import inspect
    source = inspect.getsource(db_mod._load_all_tokens)
    assert "expires_at" in source


# --- refresh tokens are single use across workers --------------------

def test_a_refresh_token_cannot_be_replayed_on_another_worker(shared):
    payload = _issue(shared, token="ref-1", table="refresh_tokens")
    worker_a = _worker(shared)
    worker_b = _worker(shared, {})
    worker_b.refresh_tokens = {"ref-1": payload}

    assert worker_a.consume_refresh_token("ref-1") is not None
    assert worker_b.consume_refresh_token("ref-1") is None, \
        "spending it on one worker must retire it on all of them"


# --- the no-database path still works --------------------------------

def test_without_a_database_the_dictionary_is_still_used(shared):
    state = APIState()
    state._db_available = False
    tokens = state.issue_tokens(USER)

    assert state.validate_bearer("Bearer " + tokens["access_token"]) is not None
    assert shared.lookups == 0, "Postgres must not be consulted when it is absent"


def test_a_database_error_cannot_resurrect_a_cached_credential(monkeypatch, shared):
    """Revocation on another worker must survive a later DB outage."""
    payload = _issue(shared)
    worker = _worker(shared, {"tok-1": payload})

    def boom(table, token):
        raise RuntimeError("postgres is away")

    monkeypatch.setattr(db_mod, "get_token", boom)

    assert worker.validate_bearer("Bearer tok-1") is None
