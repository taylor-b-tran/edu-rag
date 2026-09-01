"""Follow-up history has to survive landing on either worker (T8-18).

T8-18 shipped reading history straight from `state.sessions`, the per-worker
dictionary that PR #90 had just replaced for exactly this reason. The two
merged in the wrong order, so the fix existed and the new code did not use it.

What that looked like on the host — the same two-turn conversation, three
times, identical input:

    run 1   is_fallback False   1 source   "...all-MiniLM-L6-v2 produces 384-dimensional vectors [S1]"
    run 2   is_fallback False   1 source   "...all-MiniLM-L6-v2 produces 384-dimensional vectors [S1]"
    run 3   is_fallback True    0 sources  "The question of how many dimensions a particular model..."

Two right, one wrong, because gunicorn round-robins between two workers and
only one of them held the session. With no history the pronoun rewrite never
runs, so retrieval searches for the literal word "it", finds nothing, and the
model answers from general knowledge — which reads to a student as the
assistant ignoring the question and repeating itself.

The same gap skipped the ownership check. A lecturer posting into a student's
session was refused by the worker that had the session and served by the one
that did not: six of eight cross-user posts were appended into the student's
conversation, so the student's own history showed questions they never asked.

These tests go in through POST /api/query with the session present only in
Postgres — the state the other worker is always in.
"""
from __future__ import annotations

import pytest

from src.api.app import create_app


STUDENT = {"user_id": "stu-1", "email": "student@uow.edu.au", "role": "student",
           "enrolled_courses": ["CSIT321"]}
LECTURER = {"user_id": "lect-1", "email": "lecturer@uow.edu.au", "role": "lecturer",
            "enrolled_courses": ["CSIT321"]}
AUTH = {"Authorization": "Bearer stub"}

# Written by the other worker. This one has never seen it.
REMOTE_SESSION = {
    "session_id": "sess-remote",
    "user_id": STUDENT["user_id"],
    "course_id": "CSIT321",
    "archived": False,
    "created_at": None,
    "updated_at": None,
    "messages": [
        {"message_id": "m1", "question": "What embedding model does the system use?",
         "answer": "all-MiniLM-L6-v2.", "sources": [], "created_at": None},
    ],
}


class _Recorder:
    def __init__(self):
        self.calls: list[dict] = []
        self.recorded: list[str] = []

    def generate(self, query, **kwargs):
        self.calls.append(kwargs)
        from src.document_processor.rag_pipeline import GeneratedResponse
        return GeneratedResponse(
            answer="stub", source_refs=[], is_fallback=False, model_used="stub",
            top_chunks=[], confidence="high", confidence_score=0.9,
            response_style="detailed",
        )

    @property
    def last(self) -> dict:
        assert self.calls, "generate() was never called"
        return self.calls[-1]


@pytest.fixture
def generator():
    return _Recorder()


@pytest.fixture
def current():
    return {"user": STUDENT}


@pytest.fixture
def client(monkeypatch, generator, current):
    from src.api.routes import query as query_mod
    query_mod._RATE_STORE.clear()

    app = create_app()
    app.config.update(TESTING=True)
    state = app.config["EDURAG_API_STATE"]

    monkeypatch.setattr(type(state), "db_available", property(lambda self: True))
    monkeypatch.setattr(state, "_db_available", True)
    monkeypatch.setattr(type(state), "validate_bearer",
                        lambda self, authorization: current["user"])
    monkeypatch.setattr(type(state), "is_enrolled", lambda self, user, cid: True)
    monkeypatch.setattr(type(state), "get_generator", lambda self: generator)

    written: list[dict] = []
    monkeypatch.setattr(type(state), "record_session_message",
                        lambda self, **kw: (written.append(kw),
                                            kw.get("session_id") or "sess-new")[1])

    # The whole point: this worker's dictionary is empty.
    state.sessions.clear()

    from src.api import db
    monkeypatch.setattr(db, "get_settings", lambda scope: {})
    monkeypatch.setattr(
        db, "get_chat_session",
        lambda session_id, message_limit=None:
        REMOTE_SESSION if session_id == REMOTE_SESSION["session_id"] else None)

    c = app.test_client()
    c.state = state
    c.written = written
    return c


def _ask(client, **body):
    payload = {"query": "How many dimensions does it produce?", "course_id": "CSIT321"}
    payload.update(body)
    return client.post("/api/query", json=payload, headers=AUTH)


# --- the follow-up itself ---------------------------------------------

def test_history_arrives_when_the_session_is_only_in_postgres(client, generator):
    """run 3 in the docstring above: this worker never created the session, so
    the local lookup returned nothing and the follow-up lost its context."""
    assert _ask(client, session_id="sess-remote").status_code == 200
    history = generator.last["history"]
    assert [t["question"] for t in history] == [
        "What embedding model does the system use?"]


def test_the_same_request_behaves_the_same_every_time(client, generator):
    """Non-determinism was the actual complaint — it worked, then it didn't,
    from identical input."""
    for _ in range(5):
        _ask(client, session_id="sess-remote")
    assert all(len(call["history"]) == 1 for call in generator.calls)


def test_a_first_turn_still_has_no_history(client, generator):
    assert _ask(client).status_code == 200
    assert not generator.last["history"]


def test_an_unknown_session_id_is_not_an_error(client, generator):
    """A client may send an id for a session that no longer exists."""
    assert _ask(client, session_id="no-such-session").status_code == 200
    assert not generator.last["history"]


def test_only_the_last_three_turns_are_sent(client, generator, monkeypatch):
    from src.api import db
    long_session = dict(REMOTE_SESSION, messages=[
        {"message_id": f"m{i}", "question": f"q{i}", "answer": f"a{i}"}
        for i in range(8)
    ])
    monkeypatch.setattr(db, "get_chat_session",
                        lambda session_id, message_limit=None: long_session)
    _ask(client, session_id="sess-remote")
    assert [t["question"] for t in generator.last["history"]] == ["q5", "q6", "q7"]


def test_a_database_failure_costs_the_context_not_the_answer(client, generator, monkeypatch):
    from src.api import db

    def boom(session_id, message_limit=None):
        raise RuntimeError("postgres is away")

    monkeypatch.setattr(db, "get_chat_session", boom)
    assert _ask(client, session_id="sess-remote").status_code == 200


# --- one user's questions must not land in another's conversation -----

def test_another_user_cannot_post_into_this_session(client, current):
    """Measured before the fix: six of eight lecturer posts were appended into
    the student's session, because the worker without the session skipped the
    check entirely."""
    current["user"] = LECTURER
    assert _ask(client, session_id="sess-remote").status_code == 403


def test_a_refused_post_is_not_recorded(client, current):
    """The 403 has to happen before record_session_message, or the message
    lands in the other user's history anyway."""
    current["user"] = LECTURER
    _ask(client, session_id="sess-remote")
    assert client.written == []


def test_a_refused_post_never_reaches_the_model(client, current, generator):
    current["user"] = LECTURER
    _ask(client, session_id="sess-remote")
    assert generator.calls == []


def test_the_refusal_is_consistent_across_repeats(client, current):
    """It was 403 twice and 200 six times over eight identical requests."""
    current["user"] = LECTURER
    codes = {_ask(client, session_id="sess-remote").status_code for _ in range(6)}
    assert codes == {403}


def test_the_owner_is_still_allowed(client):
    assert _ask(client, session_id="sess-remote").status_code == 200
