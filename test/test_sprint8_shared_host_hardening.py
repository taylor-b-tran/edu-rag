from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.document_processor.rag_pipeline import (
    LLMResponseGeneration,
    RESPONSE_STYLES,
    DEFAULT_RESPONSE_STYLE,
    resolve_response_style,
    RetrievedChunk,
)


class _StubRetriever:
    def search(self, *a, **kw):
        return []


@pytest.fixture
def sample_chunks():
    return [
        RetrievedChunk(
            chunk_id="c1", text="RAG retrieves relevant chunks before generation.",
            source_file="Week1_RAG_Introduction.pdf", page_number=2,
            topic="RAG Fundamentals", week="1", distance=0.2,
        ),
    ]

# T8-10 — five response-style presets

def test_exactly_five_response_styles_defined():
    assert len(RESPONSE_STYLES) == 5


def test_default_style_is_a_valid_style():
    assert DEFAULT_RESPONSE_STYLE in RESPONSE_STYLES


def test_resolve_response_style_falls_back_on_unknown():
    assert resolve_response_style("not_a_real_style") == DEFAULT_RESPONSE_STYLE
    assert resolve_response_style(None) == DEFAULT_RESPONSE_STYLE
    assert resolve_response_style("exam_prep") == "exam_prep"


def test_each_style_changes_the_prompt(sample_chunks):
    gen = LLMResponseGeneration(retriever=_StubRetriever())
    prompts = {
        style: gen._build_prompt("What is RAG?", sample_chunks, style=style)
        for style in RESPONSE_STYLES
    }
    # Every style must actually produce a different prompt — otherwise the
    # "preset" would be cosmetic only, and the LLM would never see it.
    seen = set()
    for style, prompt in prompts.items():
        assert prompt not in seen, f"style {style!r} produced a prompt identical to another style"
        seen.add(prompt)


def test_exam_prep_style_asks_for_bullets_not_sentences(sample_chunks):
    gen = LLMResponseGeneration(retriever=_StubRetriever())
    prompt = gen._build_prompt("What is RAG?", sample_chunks, style="exam_prep")
    assert "bullet points" in prompt
    assert "Takeaway" in prompt
    assert "3-5 concise sentences" not in prompt


def test_socratic_style_asks_for_guiding_questions(sample_chunks):
    gen = LLMResponseGeneration(retriever=_StubRetriever())
    prompt = gen._build_prompt("What is RAG?", sample_chunks, style="socratic")
    assert "guiding questions" in prompt or "Do not give the full answer" in prompt


def test_generate_echoes_requested_style_on_response(monkeypatch, sample_chunks):
    gen = LLMResponseGeneration(retriever=_StubRetriever())
    monkeypatch.setattr(gen, "_call_ollama", lambda prompt, chunks=None: ("answer", True))
    result = gen.generate("What is RAG?", response_style="detailed")
    assert result.response_style == "detailed"


def test_generate_defaults_style_when_not_given(monkeypatch, sample_chunks):
    gen = LLMResponseGeneration(retriever=_StubRetriever())
    monkeypatch.setattr(gen, "_call_ollama", lambda prompt, chunks=None: ("answer", True))
    result = gen.generate("What is RAG?")
    assert result.response_style == DEFAULT_RESPONSE_STYLE

# T8-10 — /api/query validates + echoes response_style, /api/response-styles

def _login(client, email="student@uow.edu.au", password="student123"):
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.get_json()
    return resp.get_json()["access_token"]


def test_response_styles_endpoint_lists_five_styles():
    from src.api.app import create_app
    client = create_app().test_client()
    resp = client.get("/api/response-styles")
    assert resp.status_code == 200
    body = resp.get_json()
    assert len(body["styles"]) == 5
    assert body["default"] == DEFAULT_RESPONSE_STYLE
    assert {s["id"] for s in body["styles"]} == set(RESPONSE_STYLES)


def test_query_rejects_unknown_response_style(monkeypatch):
    from src.api.app import create_app
    from src.api.routes import query as query_routes
    query_routes._RATE_STORE.clear()
    client = create_app().test_client()
    token = _login(client)
    resp = client.post(
        "/api/query",
        json={"query": "what is RAG?", "course_id": "CSIT321", "response_style": "not_real"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert "response_style" in resp.get_json().get("message", "") + resp.get_json().get("error", "")

# T8-31 — embedder singleton reuse

def test_load_embedder_returns_same_instance_across_calls(monkeypatch):
    monkeypatch.setenv("EDURAG_OFFLINE_EMBEDDER", "1")
    import importlib
    import src.document_processor.ingest_corpus as ic
    importlib.reload(ic)
    ic.reset_embedder_cache_for_tests()

    model1, name1, dim1 = ic._load_embedder()
    model2, name2, dim2 = ic._load_embedder()

    assert model1 is model2
    assert name1 == name2
    assert dim1 == dim2


def test_reset_embedder_cache_forces_new_instance(monkeypatch):
    monkeypatch.setenv("EDURAG_OFFLINE_EMBEDDER", "1")
    import importlib
    import src.document_processor.ingest_corpus as ic
    importlib.reload(ic)
    ic.reset_embedder_cache_for_tests()

    model1, _, _ = ic._load_embedder()
    ic.reset_embedder_cache_for_tests()
    model2, _, _ = ic._load_embedder()

    assert model1 is not model2

# T8-31 — capped upload thread pool exists and is bounded

def test_upload_executor_has_a_bounded_worker_count():
    from src.api.routes import documents as documents_routes
    assert documents_routes._upload_executor._max_workers == documents_routes._UPLOAD_THREAD_LIMIT
    assert documents_routes._UPLOAD_THREAD_LIMIT > 0
    assert documents_routes._UPLOAD_THREAD_LIMIT < 50


def test_upload_no_longer_imports_raw_threading_module():
    """Regression guard: T8-31 replaced the raw threading.Thread-per-upload
    with a bounded ThreadPoolExecutor. This just checks the module doesn't
    still import `threading` directly for that purpose."""
    import inspect
    from src.api.routes import documents as documents_routes
    source = inspect.getsource(documents_routes)
    assert "ThreadPoolExecutor" in source
    assert "threading.Thread(" not in source

# T8-23 — gunicorn wired in as the WSGI entrypoint
def test_wsgi_module_exposes_flask_app():
    from src.api.wsgi import app
    from src.api.app import app as direct_app
    assert app is direct_app


def test_docker_compose_uses_gunicorn_not_dev_server():
    repo_root = os.path.join(os.path.dirname(__file__), "..")
    compose_path = os.path.join(repo_root, "docker-compose.yml")
    with open(compose_path, "r", encoding="utf-8") as f:
        content = f.read()
    # The actual api service `command:` block should invoke gunicorn — not
    # just check the word appears anywhere (it's also mentioned in a comment
    # explaining apps/integration/backend/api.py is kept for local/non-Docker use).
    api_block = content.split("command:", 1)[1].split("environment:", 1)[0]
    assert "gunicorn" in api_block
    assert "apps/integration/backend/api.py" not in api_block


def test_gunicorn_and_psycopg_pool_are_pinned_in_requirements():
    repo_root = os.path.join(os.path.dirname(__file__), "..")
    req_path = os.path.join(repo_root, "requirements.txt")
    with open(req_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "gunicorn" in content
    assert "psycopg-pool" in content or "psycopg_pool" in content

# T8-24 — tokens/sessions/rate-limits persisted to Postgres (schema-level;
# skipped without a live Postgres, matching the rest of this test suite)
def _postgres_available() -> bool:
    try:
        import psycopg  # noqa: F401
        from src.api import db
        with db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return True
    except Exception:
        return False


@pytest.mark.skipif(not _postgres_available(), reason="No live Postgres in this environment")
def test_token_round_trips_through_postgres():
    from src.api import db
    db.init_schema()
    payload = {"user_id": "u-test-1", "email": "t@uow.edu.au", "role": "student",
               "enrolled_courses": ["CSIT321"]}
    db.insert_access_token("tok-test-1", payload)
    loaded = db.load_all_access_tokens()
    assert "tok-test-1" in loaded
    assert loaded["tok-test-1"]["email"] == "t@uow.edu.au"


@pytest.mark.skipif(not _postgres_available(), reason="No live Postgres in this environment")
def test_chat_session_and_message_round_trip_through_postgres():
    from src.api import db
    db.init_schema()
    db.upsert_chat_session("sess-test-1", "u-test-1", "CSIT321")
    db.insert_chat_message("sess-test-1", {
        "message_id": "msg-test-1", "question": "hi", "answer": "hello", "sources": [],
    })
    sessions = db.load_all_sessions()
    assert "sess-test-1" in sessions
    assert sessions["sess-test-1"]["messages"][0]["question"] == "hi"


@pytest.mark.skipif(not _postgres_available(), reason="No live Postgres in this environment")
def test_rate_limit_allows_up_to_max_then_blocks():
    from src.api import db
    db.init_schema()
    key = "rate-test-user"
    with db.connect() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM rate_limit_hits WHERE rate_key = %s", (key,))
    allowed = [db.check_and_record_rate(key, window_seconds=60, max_hits=3) for _ in range(4)]
    assert allowed == [True, True, True, False]


def test_query_check_rate_falls_back_to_in_memory_without_db():
    """Without a db/state (or with _db_available False), _check_rate must
    still work exactly as it did before T8-24 — this is what today's CI
    and the rest of the test suite actually exercises."""
    from src.api.routes import query as query_routes
    query_routes._RATE_STORE.clear()
    key = "in-memory-fallback-user"
    results = [query_routes._check_rate(key, state=None) for _ in range(query_routes._RATE_MAX + 1)]
    assert results == [True] * query_routes._RATE_MAX + [False]
