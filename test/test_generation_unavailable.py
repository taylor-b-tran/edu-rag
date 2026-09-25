from unittest.mock import Mock

import pytest
import requests

from src.api.app import create_app
from src.document_processor import rag_pipeline as rp


def generator():
    chunk = rp.RetrievedChunk("one", "Decision trees split on features.", "lecture.pdf", 1, "Trees", "1", 0.2)
    return rp.LLMResponseGeneration(retriever=Mock(search=Mock(return_value=[chunk])))


@pytest.mark.parametrize("error", [requests.ConnectionError, requests.Timeout, requests.HTTPError])
def test_model_outage_is_503_without_persisting(monkeypatch, caplog, error):
    monkeypatch.setenv("EDURAG_OLLAMA_WARMUP", "false")
    app = create_app()
    state = app.config["EDURAG_API_STATE"]
    monkeypatch.setattr(state, "validate_bearer", lambda _: {"user_id": "outage-test"})
    monkeypatch.setattr(state, "is_enrolled", lambda *a: True)
    monkeypatch.setattr(state, "resolve_course", lambda _: ("course", "CSIT321"))
    monkeypatch.setattr(state, "get_generator", generator)
    record = Mock()
    monkeypatch.setattr(state, "record_session_message", record)
    monkeypatch.setattr(rp.requests, "post", Mock(side_effect=error("model unavailable")))
    response = app.test_client().post("/api/query", json={"query": "What is a decision tree?"})
    assert response.status_code == 503
    record.assert_not_called()
    assert state.sessions == {}
    body = response.get_data(as_text=True).lower()
    assert "ollama serve" not in body and "llama3.2" not in body
    assert any(r.exc_info for r in caplog.records)


@pytest.mark.parametrize("answer, covered", [
    ("This cannot be verified from the available course materials.", False),
    ("THIS CANNOT BE VERIFIED FROM THE AVAILABLE COURSE MATERIALS.", False),
    ("A decision tree splits on features.", True),
    ("The claim cannot be verified from the available course materials [S1].", True),
])
def test_only_uncited_refusal_clears_sources(monkeypatch, answer, covered):
    gen = generator()
    monkeypatch.setattr(gen, "_call_ollama", lambda *a, **kw: (answer, True))
    result = gen.generate("Explain decision trees")
    if covered:
        assert len(result.source_refs) == 1
        assert not result.is_fallback
    else:
        assert result.source_refs == []
        assert (result.confidence, result.confidence_score) == ("Low", 0.0)
        assert result.is_fallback
        assert "cannot be verified" in result.answer.lower()
