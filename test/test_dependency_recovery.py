from concurrent.futures import ThreadPoolExecutor
import logging
import time
from unittest.mock import Mock

import pytest

from src.api import warmup
from src.api.app import create_app
from src.api.state import APIState
from src.document_processor import ingest_corpus, rag_pipeline


@pytest.fixture
def state(monkeypatch):
    monkeypatch.setenv("EDURAG_OLLAMA_WARMUP", "false")
    monkeypatch.setenv("EDURAG_RETRIEVAL_WARMUP", "false")
    monkeypatch.setenv("PAEDIA_USE_FIXTURES", "false")
    return APIState()


def client_for(monkeypatch, state):
    app = create_app()
    app.config.update(TESTING=True, EDURAG_API_STATE=state)
    monkeypatch.setattr(state, "validate_bearer", lambda _: {"user_id": "retry-user"})
    monkeypatch.setattr(state, "is_enrolled", lambda *args: True)
    monkeypatch.setattr(state, "resolve_course", lambda _: ("course", "CSIT321"))
    return app.test_client()


def test_first_failure_returns_503_then_retries(monkeypatch, state):
    client = client_for(monkeypatch, state)
    retriever = Mock(side_effect=[RuntimeError("vector store unavailable"), Mock()])
    monkeypatch.setattr(rag_pipeline, "VectorRetriever", retriever)
    result = rag_pipeline.GeneratedResponse(answer="A decision tree.", source_refs=[],
        is_fallback=False, model_used="test", top_chunks=[], confidence="Low",
        confidence_score=0.0, response_style="concise")
    monkeypatch.setattr(rag_pipeline, "LLMResponseGeneration", Mock(return_value=Mock(generate=Mock(return_value=result))))
    failed = client.post("/api/query", json={"query": "What is a decision tree?"})
    assert failed.status_code == 503
    assert state._generator is None and state.backend_mode != "fixture"
    assert state.sessions == {}
    assert client.post("/api/query", json={"query": "What is a decision tree?"}).status_code == 200
    assert retriever.call_count == 2 and state.backend_mode == "chromadb"


def test_failure_body_is_neutral_and_logs_traceback(monkeypatch, state, caplog):
    client = client_for(monkeypatch, state)
    monkeypatch.setattr(state, "get_generator", Mock(side_effect=RuntimeError("private failure")))
    with caplog.at_level(logging.ERROR):
        response = client.post("/api/query", json={"query": "Explain decision trees"})
    assert response.status_code == 503
    assert "detail" not in response.json
    assert "ollama" not in response.get_data(as_text=True).lower()
    assert "private failure" not in response.get_data(as_text=True)
    assert any(r.exc_info for r in caplog.records)


def test_explicit_fixture_mode_still_works(monkeypatch, state):
    monkeypatch.setenv("PAEDIA_USE_FIXTURES", "true")
    monkeypatch.setattr(rag_pipeline, "VectorRetriever", Mock(side_effect=RuntimeError()))
    assert state.get_generator() is not None
    assert state.backend_mode == "fixture"


def test_concurrent_requests_build_one_pipeline(monkeypatch, state):
    def slow_retriever():
        time.sleep(0.05)
        return Mock()
    factory = Mock(side_effect=slow_retriever)
    monkeypatch.setattr(rag_pipeline, "VectorRetriever", factory)
    monkeypatch.setattr(rag_pipeline, "LLMResponseGeneration", lambda **kw: object())
    with ThreadPoolExecutor(max_workers=4) as pool:
        generators = list(pool.map(lambda _: state.get_generator(), range(4)))
    assert factory.call_count == 1
    assert all(gen is generators[0] for gen in generators)


@pytest.mark.parametrize("healthy", [False, True])
def test_worker_warmup_encodes_before_heartbeat_and_build(monkeypatch, state, healthy):
    events = []
    embedder = Mock()
    embedder.encode.side_effect = lambda *a, **kw: events.append("encode")
    monkeypatch.setattr(ingest_corpus, "_load_embedder", lambda: (embedder, "test", 384))
    def heartbeat():
        events.append("heartbeat")
        if not healthy:
            raise ConnectionError("unavailable")
    monkeypatch.setattr(ingest_corpus, "get_chroma_client", lambda: Mock(heartbeat=heartbeat))
    monkeypatch.setattr(state, "get_generator", lambda: events.append("pipeline"))
    warmup.warmup_retrieval(state)
    assert events == (["encode", "heartbeat", "pipeline"] if healthy else ["encode", "heartbeat"])


def test_worker_start_runs_retrieval_warmup(monkeypatch, state):
    monkeypatch.setenv("EDURAG_RETRIEVAL_WARMUP", "true")
    warm = Mock()
    monkeypatch.setattr(warmup, "warmup_retrieval", warm, raising=False)
    created = APIState()
    warm.assert_called_once_with(created)


def test_application_log_output_has_error_level(monkeypatch, state, capsys):
    create_app()
    logging.getLogger("src.api").error("format check")
    assert "ERROR" in capsys.readouterr().err
