from types import SimpleNamespace

import pytest
from flask import Flask

from src.api.routes.health import health_bp
from src.document_processor import ingest_corpus


@pytest.mark.parametrize("mode", ["chromadb", "fixture", "not_initialized", "embedder_mismatch"])
@pytest.mark.parametrize("status", ["ok", "offline_fallback", "not_loaded"])
def test_quality_requires_chroma_and_real_embedder(monkeypatch, mode, status):
    embedder = {"status": status}
    monkeypatch.setattr(ingest_corpus, "embedder_status", lambda: embedder)
    app = Flask(__name__)
    app.register_blueprint(health_bp)
    app.config["EDURAG_API_STATE"] = SimpleNamespace(
        backend_mode=mode, rag_available=mode == "chromadb",
        db_available=True, fixture_loaded=False,
    )
    response = app.test_client().get("/api/health")
    data = response.get_json()
    assert response.status_code == 200
    assert data["retrieval_quality"] == (
        "ok" if mode == "chromadb" and status == "ok" else "degraded"
    )
    assert data["rag_available"] == (mode == "chromadb")
    assert data["embedder"] == embedder
