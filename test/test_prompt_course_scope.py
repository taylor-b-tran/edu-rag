"""What the system prompt says the assistant is, and how long answers are.

Two defaults that were wrong in ways no test could see, because both produce a
perfectly valid response — just not a useful one.

F3. Both prompts opened with "for CSIT321 at UOW" regardless of the course
asked about. Retrieval was already scoped correctly by `course_id`, so a
CSCI203 student got CSCI203 chunks underneath a first line telling the model it
assists a subject they are not enrolled in. With the corpus now spanning four
subjects that is a live contradiction in every prompt, and the same string
reached students directly in the ambiguous-query message.

F2. `DEFAULT_RESPONSE_STYLE` was "concise", which instructs the model to answer
in a few sentences. All five styles work; only the default was wrong, and it is
the one nearly every student gets.
"""
from __future__ import annotations

import pytest

from src.document_processor import rag_pipeline as rp
from src.document_processor.rag_pipeline import LLMResponseGeneration, _course_label


@pytest.fixture
def builder():
    """The prompt builders touch no I/O, so no retriever is needed."""
    return LLMResponseGeneration.__new__(LLMResponseGeneration)


STRATEGIES = ("baseline", "evidence_cited", "few_shot_cited")


# --- F3: the prompt names the course being asked about ----------------

@pytest.mark.parametrize("strategy", STRATEGIES)
def test_the_prompt_names_the_course_that_was_asked_about(builder, strategy):
    builder.strategy = strategy
    prompt = builder._build_prompt("q", [], course_id="CSCI203")
    assert "CSCI203" in prompt


@pytest.mark.parametrize("strategy", STRATEGIES)
def test_no_prompt_mentions_csit321_for_another_course(builder, strategy):
    """The regression, stated directly."""
    builder.strategy = strategy
    prompt = builder._build_prompt("q", [], course_id="CSCI203")
    assert "CSIT321" not in prompt


def test_a_missing_course_falls_back_to_generic_wording():
    """Naming the wrong course is worse than naming none."""
    assert _course_label(None) == "your course"
    assert _course_label("") == "your course"
    assert _course_label("   ") == "your course"


def test_a_course_code_is_used_as_given():
    assert _course_label("MATH202") == "MATH202"


def test_csit321_is_still_named_when_it_is_the_course(builder):
    """The fix is scoping, not removal."""
    builder.strategy = "evidence_cited"
    assert "CSIT321" in builder._build_prompt("q", [], course_id="CSIT321")


def test_generate_passes_the_course_into_the_prompt(monkeypatch, builder):
    """The plumbing, not just the builder — `generate` is where course_id is
    known and where it previously stopped."""
    seen = {}

    class _Retriever:
        def search(self, query, course_id=None, top_k=None):
            return []

    builder.strategy = "evidence_cited"
    builder._retriever = _Retriever()
    monkeypatch.setattr(LLMResponseGeneration, "_call_ollama",
                        lambda self, prompt, chunks=None, **kwargs: (seen.setdefault("prompt", prompt), True))

    builder.generate("q", course_id="MATH202")
    assert "MATH202" in seen["prompt"]


# --- the ambiguous-query message reaches students directly ------------

def test_the_ambiguous_message_names_the_students_own_course(monkeypatch):
    from src.api.app import create_app
    from src.api.routes import query as query_mod

    query_mod._RATE_STORE.clear()

    app = create_app()
    app.config.update(TESTING=True)
    state = app.config["EDURAG_API_STATE"]
    user = {"user_id": "u1", "email": "s@uow.edu.au", "role": "student",
            "enrolled_courses": ["CSCI203"]}
    # Via monkeypatch, not by assigning to the class: `state` is a shared
    # singleton, so a bare assignment outlives the test and silently breaks
    # every later one that expects real token validation.
    monkeypatch.setattr(type(state), "validate_bearer",
                        lambda self, authorization: user)

    resp = app.test_client().post(
        "/api/query",
        json={"query": "tell me everything", "course_id": "CSCI203"},
        headers={"Authorization": "Bearer stub"},
    )
    assert resp.status_code == 422
    message = resp.get_json()["message"]
    assert "CSCI203" in message
    assert "CSIT321" not in message


# --- F2: the default students actually get ----------------------------

def test_the_default_response_style_is_detailed():
    assert rp.DEFAULT_RESPONSE_STYLE == "detailed"


def test_the_default_is_a_style_that_exists():
    assert rp.DEFAULT_RESPONSE_STYLE in rp.RESPONSE_STYLES


def test_concise_is_still_available_to_anyone_who_wants_it():
    """Changing the default must not remove the option."""
    assert rp.resolve_response_style("concise") == "concise"


def test_an_unknown_style_falls_back_to_the_new_default():
    assert rp.resolve_response_style("shouty") == "detailed"
    assert rp.resolve_response_style(None) == "detailed"
