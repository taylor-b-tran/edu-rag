from unittest.mock import Mock

import pytest
import requests

from src.api.app import create_app
from src.document_processor import rag_pipeline as rp


def generator():
    chunk = rp.RetrievedChunk("one", "Decision trees split on features.", "lecture.pdf", 1, "Trees", "1", 0.2)
    other = rp.RetrievedChunk("two", "Leaves predict a target.", "tutorial.pdf", 2, "Trees", "1", 0.1)
    return rp.LLMResponseGeneration(retriever=Mock(search=Mock(return_value=[chunk, other])))


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
    assert any(r.name == "src.document_processor.rag_pipeline" and r.exc_info for r in caplog.records)


@pytest.mark.parametrize("answer, covered", [
    ("This cannot be verified from the available course materials.", False),
    ("THIS CANNOT BE VERIFIED FROM THE AVAILABLE COURSE MATERIALS.", False),
    ("This cannot be verified\nfrom the available  course materials.", False),
    ("The course materials do not contain an explanation of stride.", False),
    ("The COURSE MATERIALS\nDO NOT CONTAIN an explanation of stride.", False),
    ("A decision tree splits on features.", True),
    ("The claim cannot be verified from the available course materials [S1].", True),
    ("Decision trees split on feature values. The course materials do not contain a worked pruning example.", True),
    ("Decision trees split on feature values [S1]. The course materials do not contain a worked pruning example.", True),
])
def test_only_uncited_refusal_clears_sources(monkeypatch, answer, covered):
    gen = generator()
    monkeypatch.setattr(gen, "_call_ollama", lambda *a, **kw: (answer, True))
    result = gen.generate("Explain decision trees")
    if covered:
        assert len(result.source_refs) == (1 if "[S1]" in answer else 2)
        assert not result.is_fallback
        assert not result.answer.startswith(rp.FALLBACK_LABEL)
    else:
        assert result.source_refs == []
        assert (result.confidence, result.confidence_score) == ("Low", 0.0)
        assert result.is_fallback
        assert " ".join(answer.split()) in " ".join(result.answer.split())


@pytest.mark.parametrize("payload", [{"response": ""}, {"response": " \n "}, {},
    {"error": "model unavailable"}, {"error": "model unavailable", "response": "partial answer"}])
def test_empty_or_error_success_response_is_not_persisted(monkeypatch, caplog, payload):
    monkeypatch.setenv("EDURAG_OLLAMA_WARMUP", "false")
    app = create_app()
    state = app.config["EDURAG_API_STATE"]
    monkeypatch.setattr(state, "validate_bearer", lambda _: {"user_id": "empty-model-test"})
    monkeypatch.setattr(state, "is_enrolled", lambda *a: True)
    monkeypatch.setattr(state, "resolve_course", lambda _: ("course", "CSIT321"))
    monkeypatch.setattr(state, "get_generator", generator)
    record = Mock()
    monkeypatch.setattr(state, "record_session_message", record)
    monkeypatch.setattr(rp.requests, "post", Mock(return_value=Mock(json=lambda: payload)))
    response = app.test_client().post("/api/query", json={"query": "What is a decision tree?"})
    assert response.status_code == 503
    record.assert_not_called()
    assert "detail" not in response.json
    assert any(r.name == "src.document_processor.rag_pipeline" and r.levelname == "ERROR" for r in caplog.records)


@pytest.mark.parametrize("answer", ["[S9]", "Sources: S9", "[S1]", "[S1]\nSources: S1"])
def test_marker_only_response_is_unavailable(monkeypatch, answer):
    gen = generator()
    monkeypatch.setattr(gen, "_call_ollama", lambda *a, **kw: (answer, True))
    with pytest.raises(rp.GenerationUnavailable):
        gen.generate("Explain decision trees")


def test_ollama_error_text_is_logged_once_at_pipeline_level(monkeypatch, caplog):
    gen = generator()
    response = Mock(json=lambda: {"error": "the model rejected the request"})
    monkeypatch.setattr(rp.requests, "post", Mock(return_value=response))
    with pytest.raises(rp.GenerationUnavailable):
        gen.generate("Explain decision trees")
    pipeline_errors = [r for r in caplog.records if r.name == "src.document_processor.rag_pipeline"
                       and r.levelname == "ERROR"]
    assert len(pipeline_errors) == 1
    assert "the model rejected the request" in pipeline_errors[0].getMessage()


def test_outage_logs_once_at_pipeline_level(monkeypatch, caplog):
    gen = generator()
    monkeypatch.setattr(rp.requests, "post", Mock(side_effect=requests.ConnectionError("offline")))
    with pytest.raises(rp.GenerationUnavailable):
        gen.generate("Explain decision trees")
    pipeline_errors = [r for r in caplog.records if r.name == "src.document_processor.rag_pipeline"
                       and r.levelname == "ERROR"]
    assert len(pipeline_errors) == 1


@pytest.mark.parametrize("strategy", ["baseline", "evidence_cited", "few_shot_cited"])
def test_prompt_and_refusal_detector_share_the_sentence(monkeypatch, strategy):
    monkeypatch.setattr(rp, "REFUSAL_SENTENCE", "cannot verify this subject from course sources")
    gen = generator()
    gen.strategy = strategy
    chunks = gen._retriever.search("decision trees")
    assert rp.REFUSAL_SENTENCE in gen._build_prompt("Explain trees", chunks, course_id="CSIT321")
    monkeypatch.setattr(gen, "_call_ollama", lambda *a, **kw: (rp.REFUSAL_SENTENCE, True))
    response = gen.generate("Explain trees")
    assert response.source_refs == [] and response.is_fallback
