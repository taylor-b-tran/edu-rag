from __future__ import annotations

import pytest

from src.api.app import create_app


USER = {"user_id": "u1", "email": "s@uow.edu.au", "role": "student",
        "enrolled_courses": ["CSIT321"]}
OTHER_USER = {"user_id": "u2", "email": "other@uow.edu.au", "role": "student",
              "enrolled_courses": ["CSIT321"]}
AUTH = {"Authorization": "Bearer stub"}

SESSION = {
    "session_id": "sess-1",
    "user_id": USER["user_id"],
    "course_id": "CSIT321",
    "archived": False,
    "created_at": "2026-09-11T01:00:00Z",
    "updated_at": "2026-09-11T01:00:00Z",
    "messages": [
        {"message_id": "m1", "question": "What embedding model is used?",
         "answer": "all-MiniLM-L6-v2.", "sources": [], "created_at": None},
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

    monkeypatch.setattr(type(state), "validate_bearer",
                        lambda self, authorization: current["user"])
    state.sessions.clear()
    state.message_feedback.clear()
    state.sessions[SESSION["session_id"]] = dict(SESSION, messages=list(SESSION["messages"]))

    c = app.test_client()
    c.state = state
    return c


FEEDBACK_URL = f"/api/sessions/{SESSION['session_id']}/messages/m1/feedback"
SESSION_FEEDBACK_URL = f"/api/sessions/{SESSION['session_id']}/feedback"


# no database: the in-memory path (how the rest of the suite runs)

def test_voting_up_is_recorded(client):
    resp = client.put(FEEDBACK_URL, json={"rating": "up"}, headers=AUTH)
    assert resp.status_code == 200
    assert resp.get_json() == {"message_id": "m1", "rating": "up"}
    assert client.state.message_feedback["m1"][USER["user_id"]] == "up"


def test_changing_your_vote_overwrites_it(client):
    client.put(FEEDBACK_URL, json={"rating": "up"}, headers=AUTH)
    client.put(FEEDBACK_URL, json={"rating": "down"}, headers=AUTH)
    assert client.state.message_feedback["m1"][USER["user_id"]] == "down"


def test_clearing_a_vote_removes_it(client):
    client.put(FEEDBACK_URL, json={"rating": "up"}, headers=AUTH)
    resp = client.delete(FEEDBACK_URL, headers=AUTH)
    assert resp.status_code == 200
    assert USER["user_id"] not in client.state.message_feedback.get("m1", {})


def test_clearing_a_vote_that_was_never_cast_is_not_an_error(client):
    assert client.delete(FEEDBACK_URL, headers=AUTH).status_code == 200


def test_an_invalid_rating_is_rejected(client):
    resp = client.put(FEEDBACK_URL, json={"rating": "sideways"}, headers=AUTH)
    assert resp.status_code == 400
    assert "m1" not in client.state.message_feedback


def test_a_missing_rating_is_rejected(client):
    assert client.put(FEEDBACK_URL, json={}, headers=AUTH).status_code == 400


def test_voting_on_someone_elses_session_is_denied(client, current):
    current["user"] = OTHER_USER
    resp = client.put(FEEDBACK_URL, json={"rating": "up"}, headers=AUTH)
    assert resp.status_code == 403
    assert "m1" not in client.state.message_feedback


def test_voting_on_a_missing_session_is_404(client):
    url = "/api/sessions/nope/messages/m1/feedback"
    assert client.put(url, json={"rating": "up"}, headers=AUTH).status_code == 404


def test_voting_on_a_message_not_in_the_session_is_404(client):
    url = f"/api/sessions/{SESSION['session_id']}/messages/does-not-exist/feedback"
    assert client.put(url, json={"rating": "up"}, headers=AUTH).status_code == 404


def test_anonymous_callers_are_rejected(client, current):
    current["user"] = None
    assert client.put(FEEDBACK_URL, json={"rating": "up"}, headers=AUTH).status_code == 401
    assert client.delete(FEEDBACK_URL, headers=AUTH).status_code == 401
    assert client.get(SESSION_FEEDBACK_URL, headers=AUTH).status_code == 401


# reading a session's votes back 

def test_session_feedback_reflects_a_recorded_vote(client):
    client.put(FEEDBACK_URL, json={"rating": "up"}, headers=AUTH)
    resp = client.get(SESSION_FEEDBACK_URL, headers=AUTH)
    assert resp.status_code == 200
    assert resp.get_json() == {"feedback": {"m1": "up"}}


def test_session_feedback_is_scoped_to_the_caller(client, current):
    client.put(FEEDBACK_URL, json={"rating": "up"}, headers=AUTH)
    current["user"] = OTHER_USER
    # OTHER_USER doesn't own the session at all, so this is a 403, not an
    # empty map - reading someone else's votes isn't allowed either.
    assert client.get(SESSION_FEEDBACK_URL, headers=AUTH).status_code == 403


def test_session_feedback_for_a_missing_session_is_404(client):
    assert client.get("/api/sessions/nope/feedback", headers=AUTH).status_code == 404

def test_a_vote_is_written_through_to_postgres_when_available(client, monkeypatch):
    from src.api import db

    written = {}
    monkeypatch.setattr(type(client.state), "db_available", property(lambda self: True))
    monkeypatch.setattr(client.state, "_db_available", True)
    monkeypatch.setattr(
        db, "upsert_message_feedback",
        lambda message_id, user_id, rating: written.update(
            message_id=message_id, user_id=user_id, rating=rating))

    resp = client.put(FEEDBACK_URL, json={"rating": "down"}, headers=AUTH)
    assert resp.status_code == 200
    assert written == {"message_id": "m1", "user_id": USER["user_id"], "rating": "down"}


def test_a_failed_write_still_returns_success_from_the_in_memory_copy(client, monkeypatch):
    """Same best-effort-persistence choice as record_session_message: a
    Postgres hiccup costs the next restart's copy of this one vote, not the
    click the student just made."""
    from src.api import db

    monkeypatch.setattr(type(client.state), "db_available", property(lambda self: True))
    monkeypatch.setattr(client.state, "_db_available", True)

    def boom(message_id, user_id, rating):
        raise RuntimeError("postgres is away")

    monkeypatch.setattr(db, "upsert_message_feedback", boom)
    resp = client.put(FEEDBACK_URL, json={"rating": "up"}, headers=AUTH)
    assert resp.status_code == 200
    assert client.state.message_feedback["m1"][USER["user_id"]] == "up"


def test_session_feedback_read_prefers_postgres(client, monkeypatch):
    from src.api import db

    monkeypatch.setattr(type(client.state), "db_available", property(lambda self: True))
    monkeypatch.setattr(client.state, "_db_available", True)
    # This worker's own dictionary disagrees with Postgres - Postgres wins,
    # same rule as get_live_session for sessions themselves.
    client.state.message_feedback["m1"] = {USER["user_id"]: "up"}
    monkeypatch.setattr(db, "get_chat_session",
                        lambda session_id, message_limit=None:
                        SESSION if session_id == SESSION["session_id"] else None)
    monkeypatch.setattr(db, "get_session_feedback",
                        lambda session_id, user_id: {"m1": "down"})

    resp = client.get(SESSION_FEEDBACK_URL, headers=AUTH)
    assert resp.get_json() == {"feedback": {"m1": "down"}}


def test_session_feedback_read_falls_back_on_postgres_failure(client, monkeypatch):
    from src.api import db

    monkeypatch.setattr(type(client.state), "db_available", property(lambda self: True))
    monkeypatch.setattr(client.state, "_db_available", True)
    client.state.message_feedback["m1"] = {USER["user_id"]: "up"}
    monkeypatch.setattr(db, "get_chat_session",
                        lambda session_id, message_limit=None:
                        SESSION if session_id == SESSION["session_id"] else None)

    def boom(session_id, user_id):
        raise RuntimeError("postgres is away")

    monkeypatch.setattr(db, "get_session_feedback", boom)
    resp = client.get(SESSION_FEEDBACK_URL, headers=AUTH)
    assert resp.get_json() == {"feedback": {"m1": "up"}}