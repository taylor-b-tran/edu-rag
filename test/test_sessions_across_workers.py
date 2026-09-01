"""Chat sessions have to be readable from any worker, not just the one that
created them (T8-18, step 0).

`APIState.sessions` is hydrated once from Postgres at start-up and only ever
mutated locally afterwards. Writes do reach Postgres (T8-24), but nothing ever
reads a single session back, so with `--workers=2` a conversation started on
one worker is simply absent from the other's dictionary.

Measured on the host before this change — one session created, then fetched ten
times:

    200 404 404 404 200 404 404 404 200 200

Five hits, five misses, because requests round-robin between two workers. The
session existed the whole time.

That is bad on its own — the sidebar loses half a student's conversations, and
`GET /api/sessions/<id>` denies one that exists. It matters more as groundwork:
T8-18 passes the last few turns into the prompt so follow-up questions work, and
history read from a per-worker dictionary would make that feature correct about
half the time, non-deterministically. A feature that passes a demo and fails in
front of a marker is worse than one that is plainly missing.

Same shape, and same fix, as `test_tokens_across_workers.py`: read the row,
treat Postgres as authoritative when it answers, keep the dictionary as the
source of truth only when there is no database.
"""
from __future__ import annotations

import pytest

from src.api.app import create_app


USER = {"user_id": "u1", "email": "s@uow.edu.au", "role": "student",
        "enrolled_courses": ["CSIT321"]}
OTHER_USER = {"user_id": "u2", "email": "other@uow.edu.au", "role": "student",
              "enrolled_courses": ["CSIT321"]}
AUTH = {"Authorization": "Bearer stub"}

# What another worker wrote to Postgres. This worker has never seen it.
REMOTE_SESSION = {
    "session_id": "sess-remote",
    "user_id": USER["user_id"],
    "course_id": "CSIT321",
    "archived": False,
    "created_at": "2026-08-30T01:00:00Z",
    "updated_at": "2026-08-30T01:00:00Z",
    "messages": [
        {"message_id": "m1", "question": "What embedding model is used?",
         "answer": "all-MiniLM-L6-v2.", "sources": [], "created_at": None},
        {"message_id": "m2", "question": "Who wrote it?",
         "answer": "sentence-transformers.", "sources": [], "created_at": None},
    ],
}


@pytest.fixture
def current():
    return {"user": USER}


@pytest.fixture
def client(monkeypatch, current):
    app = create_app()
    app.config.update(TESTING=True)
    state = app.config["EDURAG_API_STATE"]

    monkeypatch.setattr(type(state), "db_available", property(lambda self: True))
    monkeypatch.setattr(state, "_db_available", True)
    monkeypatch.setattr(type(state), "validate_bearer",
                        lambda self, authorization: current["user"])

    # The point of these tests: this worker's own dictionary is empty.
    state.sessions.clear()

    from src.api import db
    monkeypatch.setattr(
        db, "get_chat_session",
        lambda session_id, message_limit=None:
        REMOTE_SESSION if session_id == REMOTE_SESSION["session_id"] else None)
    monkeypatch.setattr(
        db, "load_all_sessions",
        lambda: {REMOTE_SESSION["session_id"]: REMOTE_SESSION})

    c = app.test_client()
    c.state = state
    return c


# --- reading one session ----------------------------------------------

def test_a_session_created_on_another_worker_is_found(client):
    """The 404s in the measurement above."""
    resp = client.get("/api/sessions/sess-remote", headers=AUTH)
    assert resp.status_code == 200
    assert len(resp.get_json()["messages"]) == 2


def test_a_genuinely_missing_session_is_still_404(client):
    assert client.get("/api/sessions/nope", headers=AUTH).status_code == 404


def test_postgres_is_authoritative_over_a_stale_local_copy(client):
    """A session deleted elsewhere must not come back to life because this
    worker still holds a copy — the same reasoning that makes logout work
    across workers in test_tokens_across_workers."""
    client.state.sessions["ghost"] = dict(REMOTE_SESSION, session_id="ghost")
    assert client.get("/api/sessions/ghost", headers=AUTH).status_code == 404
    assert "ghost" not in client.state.sessions, "the stale copy should be dropped"


def test_another_users_session_is_still_denied(client, current):
    """Reading across workers must not read across accounts."""
    current["user"] = OTHER_USER
    assert client.get("/api/sessions/sess-remote", headers=AUTH).status_code == 403


def test_anonymous_callers_are_rejected(client, current):
    current["user"] = None
    assert client.get("/api/sessions/sess-remote", headers=AUTH).status_code == 401


# --- listing -----------------------------------------------------------

def test_the_list_includes_sessions_from_other_workers(client):
    """The sidebar was showing whichever half of a student's conversations
    happened to land on the worker serving the page."""
    body = client.get("/api/sessions", headers=AUTH).get_json()
    assert [s["session_id"] for s in body["sessions"]] == ["sess-remote"]


def test_the_list_is_still_scoped_to_the_caller(client, current):
    current["user"] = OTHER_USER
    assert client.get("/api/sessions", headers=AUTH).get_json()["sessions"] == []


# --- degrading, not failing -------------------------------------------

def test_a_read_failure_falls_back_to_this_workers_copy(client, monkeypatch):
    """Postgres being away should cost the cross-worker view, not the endpoint.
    Unlike a token, a stale session is not a security problem."""
    from src.api import db

    def boom(session_id, message_limit=None):
        raise RuntimeError("postgres is away")

    monkeypatch.setattr(db, "get_chat_session", boom)
    client.state.sessions["local"] = dict(REMOTE_SESSION, session_id="local")
    assert client.get("/api/sessions/local", headers=AUTH).status_code == 200


def test_a_list_failure_falls_back_to_this_workers_copy(client, monkeypatch):
    from src.api import db

    def boom():
        raise RuntimeError("postgres is away")

    monkeypatch.setattr(db, "load_all_sessions", boom)
    client.state.sessions["local"] = dict(REMOTE_SESSION, session_id="local")
    body = client.get("/api/sessions", headers=AUTH).get_json()
    assert [s["session_id"] for s in body["sessions"]] == ["local"]


def test_without_a_database_the_dictionary_is_used(client, monkeypatch):
    """How the rest of the suite runs, and how a Postgres-less dev box runs."""
    monkeypatch.setattr(type(client.state), "db_available", property(lambda self: False))
    monkeypatch.setattr(client.state, "_db_available", False)
    client.state.sessions["local"] = dict(REMOTE_SESSION, session_id="local")
    assert client.get("/api/sessions/local", headers=AUTH).status_code == 200
    assert client.get("/api/sessions/sess-remote", headers=AUTH).status_code == 404


# --- the state helper directly ----------------------------------------

def test_get_live_session_caches_what_it_read(client):
    """So the next read on this worker is local if Postgres goes away."""
    assert "sess-remote" not in client.state.sessions
    client.state.get_live_session("sess-remote")
    assert "sess-remote" in client.state.sessions


def test_a_limited_read_is_not_cached_as_the_whole_session(client):
    """`message_limit` returns a truncated session — storing that as the
    session would silently lose the earlier turns. T8-18's history read will
    use this parameter; it must not corrupt the cache."""
    client.state.get_live_session("sess-remote", message_limit=1)
    assert "sess-remote" not in client.state.sessions


def test_an_empty_session_id_is_not_looked_up(client):
    assert client.state.get_live_session("") is None
    assert client.state.get_live_session(None) is None
