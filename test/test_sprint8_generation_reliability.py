import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.document_processor.rag_pipeline import LLMResponseGeneration
from src.api import warmup


class _StubRetriever:
    def search(self, *a, **kw):
        return []


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload

def test_call_ollama_sends_think_false(monkeypatch):
    monkeypatch.setenv("OLLAMA_THINK", "false")
    captured = {}

    def fake_post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json
        return _FakeResponse({"response": "answer text"})

    monkeypatch.setattr("src.document_processor.rag_pipeline.requests.post", fake_post)

    # Reload module-level constants that read the env var at import time.
    import importlib
    import src.document_processor.rag_pipeline as rp
    importlib.reload(rp)
    monkeypatch.setattr(rp.requests, "post", fake_post)

    gen = rp.LLMResponseGeneration(retriever=_StubRetriever())
    raw, ok = gen._call_ollama("some prompt")

    assert ok is True
    assert raw == "answer text"

    assert captured["json"]["think"] is False
    assert "think" not in captured["json"]["options"]


def test_call_ollama_think_defaults_off_when_unset(monkeypatch):
    monkeypatch.delenv("OLLAMA_THINK", raising=False)
    import importlib
    import src.document_processor.rag_pipeline as rp
    importlib.reload(rp)

    assert rp.OLLAMA_THINK is False

def test_call_ollama_sends_keep_alive(monkeypatch):
    monkeypatch.setenv("OLLAMA_KEEP_ALIVE", "30m")
    import importlib
    import src.document_processor.rag_pipeline as rp
    importlib.reload(rp)

    captured = {}

    def fake_post(url, json, timeout):
        captured["json"] = json
        return _FakeResponse({"response": "ok"})

    monkeypatch.setattr(rp.requests, "post", fake_post)
    gen = rp.LLMResponseGeneration(retriever=_StubRetriever())
    gen._call_ollama("prompt")

    assert captured["json"]["keep_alive"] == "30m"


def test_warmup_sends_think_and_keep_alive(monkeypatch):
    monkeypatch.setenv("OLLAMA_THINK", "false")
    monkeypatch.setenv("OLLAMA_KEEP_ALIVE", "30m")

    calls = []

    def fake_get(url, timeout):
        class R:
            def raise_for_status(self):
                pass

            def json(self):
                return {"models": [{"name": "qwen3:14b"}]}

        return R()

    def fake_post(url, json=None, timeout=None):
        calls.append((url, json))

        class R:
            def raise_for_status(self):
                pass

            def json(self):
                return {"response": "pong"}

        return R()

    monkeypatch.setattr(warmup.requests, "get", fake_get)
    monkeypatch.setattr(warmup.requests, "post", fake_post)

    result = warmup.warmup_ollama(host="http://fake:11434", model="qwen3:14b")

    assert result["generated"] is True
    gen_call = [c for c in calls if c[0].endswith("/api/generate")][0]
    assert gen_call[1]["think"] is False
    assert gen_call[1]["keep_alive"] == "30m"

def test_embedder_status_reports_offline_fallback(monkeypatch):
    """When EDURAG_OFFLINE_EMBEDDER is set, embedder_status() should say so
    (this is the same path CI/tests already use, so no network needed)."""
    monkeypatch.setenv("EDURAG_OFFLINE_EMBEDDER", "1")
    import importlib
    import src.document_processor.ingest_corpus as ic
    importlib.reload(ic)

    model, name, dim = ic._load_embedder()
    status = ic.embedder_status()

    assert status["status"] == "offline_fallback"
    assert status["model_name"] == name
    assert status["cached"] is False


def test_embedder_cache_dir_is_configurable(monkeypatch, tmp_path):
    monkeypatch.setenv("EMBEDDER_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.delenv("EDURAG_OFFLINE_EMBEDDER", raising=False)
    import importlib
    import src.document_processor.ingest_corpus as ic
    importlib.reload(ic)

    assert ic.EMBEDDER_CACHE_DIR == str(tmp_path / "cache")
    assert ic._embedder_already_cached() is False


def test_health_endpoint_includes_embedder_status(monkeypatch):
    """/api/health should surface embedder_status() without requiring auth."""
    os.environ.setdefault("PAEDIA_ALLOW_FIXTURE_AUTH", "1")
    from src.api.app import create_app

    app = create_app()
    client = app.test_client()
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.get_json()
    assert "embedder" in body
    assert "status" in body["embedder"]
