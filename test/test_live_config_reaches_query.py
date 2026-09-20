"""Live config has to arrive at the query path, not just at the settings table.

T8-08 shipped in PR 87 and was silently switched off in PR 88, which replaced
the resolved values with literals:

    response_style=response_style_raw,
    top_k=None,
    similarity_threshold=None,

Every test stayed green. `test_live_config.py` proves the endpoint stores a
setting and that `effective_settings` resolves the tiers correctly, and both
things were still true — the query path simply stopped asking. So the API went
on accepting a threshold, saving it, and echoing it back under "effective",
while answering as if it had never been set. A lecturer tuning their course
would have seen every confirmation the UI can give and no change at all.

That is worse than the feature being absent, and nothing in the suite could
tell. These tests close the gap: they go in through `POST /api/query` and
assert on the arguments `generate()` was actually called with. Deleting the
wiring again turns them red.

The generator is a recorder rather than the real pipeline — the point is which
values reach it, not what the model says.
"""
from __future__ import annotations

import pytest

from src.api.app import create_app


LECTURER = {"user_id": "lect-1", "email": "lecturer@uow.edu.au", "role": "lecturer",
            "enrolled_courses": ["OWNED101"]}
OWNED = {"course_code": "OWNED101", "course_name": "Owned", "owner_id": LECTURER["user_id"]}

AUTH = {"Authorization": "Bearer stub"}


class _Recorder:
    """Stands in for the RAG pipeline and keeps the last call's kwargs."""

    def __init__(self):
        self.calls: list[dict] = []

    def generate(self, query, **kwargs):
        self.calls.append(kwargs)
        from src.document_processor.rag_pipeline import GeneratedResponse
        return GeneratedResponse(
            answer="stub", source_refs=[], is_fallback=False,
            model_used="stub", top_chunks=[], confidence="high",
            confidence_score=0.9, response_style=kwargs.get("response_style") or "concise",
        )

    @property
    def last(self) -> dict:
        assert self.calls, "generate() was never called"
        return self.calls[-1]


@pytest.fixture
def store():
    return {}


@pytest.fixture
def generator():
    return _Recorder()


@pytest.fixture
def client(monkeypatch, store, generator):
    # Every test here asks as the same user, and the rate store is module-level
    # with a limit of 10 a minute, so without this the later tests 429.
    from src.api.routes import query as query_mod
    query_mod._RATE_STORE.clear()

    app = create_app()
    app.config.update(TESTING=True)
    state = app.config["EDURAG_API_STATE"]

    monkeypatch.setattr(type(state), "db_available", property(lambda self: True))
    monkeypatch.setattr(state, "_db_available", True)
    monkeypatch.setattr(type(state), "validate_bearer",
                        lambda self, authorization: LECTURER)
    monkeypatch.setattr(type(state), "is_enrolled",
                        lambda self, user, cid: cid in (user.get("enrolled_courses") or []))
    monkeypatch.setattr(type(state), "get_generator", lambda self: generator)
    monkeypatch.setattr(type(state), "record_session_message",
                        lambda self, **kw: "sess-1")

    from src.api import db
    monkeypatch.setattr(db, "get_course_by_ref", lambda ref:
                        {**OWNED, "id": "owned-course-id"}
                        if ref in ("OWNED101", "owned-course-id") else None)
    monkeypatch.setattr(db, "get_course_by_code", lambda code: OWNED)
    monkeypatch.setattr(db, "get_settings",
                        lambda scope: {k[1]: v for k, v in store.items() if k[0] == scope})
    monkeypatch.setattr(db, "set_setting",
                        lambda scope, key, value, updated_by=None:
                        store.__setitem__((scope, key), value))
    monkeypatch.setattr(db, "delete_setting",
                        lambda scope, key: store.pop((scope, key), None))

    return app.test_client()


def _ask(client, **body):
    payload = {"query": "What is chunking?", "course_id": "OWNED101"}
    payload.update(body)
    return client.post("/api/query", json=payload, headers=AUTH)


# --- the regression itself --------------------------------------------

def test_a_course_threshold_reaches_the_generator(client, store, generator):
    """The exact case that was broken: set it, then ask, then check it arrived."""
    store[("OWNED101", "similarity_threshold")] = 0.99
    assert _ask(client).status_code == 200
    assert generator.last["similarity_threshold"] == 0.99


def test_a_course_top_k_reaches_the_generator(client, store, generator):
    store[("OWNED101", "top_k")] = 9
    _ask(client)
    assert generator.last["top_k"] == 9


def test_a_course_response_style_reaches_the_generator(client, store, generator):
    store[("OWNED101", "response_style")] = "exam_prep"
    _ask(client)
    assert generator.last["response_style"] == "exam_prep"


def test_settings_written_through_the_api_take_effect_without_a_restart(client, generator):
    """End to end through both routes, which is the actual promise of T8-08."""
    before = client.patch("/api/courses/OWNED101/settings",
                          json={"top_k": 3}, headers=AUTH)
    assert before.status_code == 200

    _ask(client)
    assert generator.last["top_k"] == 3

    client.patch("/api/courses/OWNED101/settings", json={"top_k": 11}, headers=AUTH)
    _ask(client)
    assert generator.last["top_k"] == 11, "the second change was ignored"


# --- the tiers, seen from the query path ------------------------------

def test_a_global_setting_reaches_a_course_that_has_no_override(client, store, generator):
    store[("global", "top_k")] = 6
    _ask(client)
    assert generator.last["top_k"] == 6


def test_a_course_override_beats_the_global_one(client, store, generator):
    store[("global", "top_k")] = 6
    store[("OWNED101", "top_k")] = 9
    _ask(client)
    assert generator.last["top_k"] == 9


def test_with_nothing_stored_the_environment_defaults_arrive(client, generator):
    """Not None — the pipeline should be handed real values, so that what the
    settings endpoint reports as effective is what the query actually used."""
    from src.document_processor import rag_pipeline as rp
    _ask(client)
    assert generator.last["top_k"] == rp.TOP_K
    assert generator.last["similarity_threshold"] == rp.SIMILARITY_THRESHOLD


# --- precedence against the request body ------------------------------

def test_an_explicit_style_in_the_body_beats_the_course_setting(client, store, generator):
    """The student's own choice for one question wins over the course default."""
    store[("OWNED101", "response_style")] = "exam_prep"
    _ask(client, response_style="simple")
    assert generator.last["response_style"] == "simple"


def test_a_global_only_key_cannot_be_smuggled_in_through_a_course_row(client, store, generator):
    """Course scope must not move weights in and out of shared VRAM.

    Asserts on `model`, the argument generate() actually takes. It used to
    check `ollama_model`, a key that was never a parameter at all -- so the
    test passed whatever the code did, including while the global tier was
    being ignored entirely.
    """
    store[("OWNED101", "ollama_model")] = "sneaky"
    _ask(client)
    assert generator.last.get("model") != "sneaky"
    assert generator.last.get("ollama_model") is None, "not a parameter of generate()"


# --- it must not become a new way for queries to fail -----------------

def test_a_settings_read_failure_does_not_break_answering(client, monkeypatch, generator):
    """Resolution is best-effort. Postgres being away should cost the tuning,
    not the answer."""
    from src.api import db

    def boom(scope):
        raise RuntimeError("postgres is away")

    monkeypatch.setattr(db, "get_settings", boom)
    from src.document_processor import rag_pipeline as rp

    assert _ask(client).status_code == 200
    assert generator.last["top_k"] == rp.TOP_K


# --- the global tier reaches the model too ----------------------------
#
# top_k, similarity_threshold and response_style were wired up and guarded
# above. The other three settings the API accepts -- ollama_model, temperature
# and num_predict -- were not: _call_ollama read them from module constants
# fixed at import, so an admin could raise the answer length, watch the
# endpoint confirm it and report it under "effective", and get an identically
# truncated answer. Measured on the host before the fix: the same question
# returned byte-identical output at num_predict 220, 400, 600 and 900.
#
# That mattered beyond the setting itself. F2 made "detailed" the default
# response style without raising the 220-token budget sized for "concise", so
# answers were being cut mid-sentence and never reached the "Sources:" line the
# prompt asks for -- and the one control that could have fixed it did nothing.


def test_a_global_num_predict_reaches_the_model(client, store, generator):
    store[("global", "num_predict")] = 900
    _ask(client)
    assert generator.last["num_predict"] == 900


def test_a_global_temperature_reaches_the_model(client, store, generator):
    store[("global", "temperature")] = 0.7
    _ask(client)
    assert generator.last["temperature"] == 0.7


def test_a_global_model_choice_reaches_the_model(client, store, generator):
    store[("global", "ollama_model")] = "llama3.2"
    _ask(client)
    assert generator.last["model"] == "llama3.2"


def test_with_nothing_stored_the_environment_generation_defaults_arrive(client, generator):
    from src.document_processor import rag_pipeline as rp
    _ask(client)
    assert generator.last["num_predict"] == rp.OLLAMA_NUM_PREDICT
    assert generator.last["temperature"] == rp.OLLAMA_TEMPERATURE
    assert generator.last["model"] == rp.OLLAMA_MODEL


def test_the_token_budget_is_big_enough_for_the_default_style():
    """A guard on the pairing, not on either number alone.

    "detailed" asks the model for multiple paragraphs. 220 tokens is roughly
    165 words, which truncated real answers mid-sentence on the host. If the
    default style is ever moved back to a verbose one, or the budget cut, this
    should fail rather than quietly shipping guillotined answers again.
    """
    from src.document_processor import rag_pipeline as rp
    if rp.DEFAULT_RESPONSE_STYLE in ("detailed", "exam_prep"):
        assert rp.OLLAMA_NUM_PREDICT >= 600, (
            f"{rp.DEFAULT_RESPONSE_STYLE!r} answers need room; "
            f"num_predict is {rp.OLLAMA_NUM_PREDICT}"
        )
