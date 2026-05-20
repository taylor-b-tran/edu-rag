from __future__ import annotations

import json

from scripts import sprint5_integration_gate as gate


def test_conflict_marker_detection_reports_line_numbers(tmp_path):
    marker_file = tmp_path / "README.md"
    marker_file.write_text("ok\n<<<<<<< HEAD\nbad\n", encoding="utf-8")

    original_root = gate.REPO_ROOT
    gate.REPO_ROOT = tmp_path
    try:
        errors = gate.check_no_conflict_markers(["README.md"])
    finally:
        gate.REPO_ROOT = original_root

    assert errors == ["README.md:2: leftover merge-conflict marker"]


def test_tracked_path_policy_blocks_old_integration_and_raw_samples():
    errors = gate.check_tracked_path_policy(
        [
            "itegration/backend/api.py",
            "data/samples/course.pdf",
            "apps/integration/backend/api.py",
        ]
    )

    assert "itegration/backend/api.py: forbidden tracked path for Sprint 5 demo hygiene" in errors
    assert "data/samples/course.pdf: forbidden tracked path for Sprint 5 demo hygiene" in errors
    assert all("apps/integration" not in error for error in errors)


def test_compose_contract_requires_demo_services_and_healthchecks(tmp_path):
    compose_json = tmp_path / "compose.json"
    compose_json.write_text(
        json.dumps(
            {
                "services": {
                    "postgres": {},
                    "chromadb": {},
                    "ollama": {},
                    "api": {
                        "depends_on": {"postgres": {}, "chromadb": {}, "ollama": {}},
                        "healthcheck": {"test": ["CMD", "true"]},
                    },
                    "streamlit": {
                        "depends_on": {"api": {}},
                        "healthcheck": {"test": ["CMD", "true"]},
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    assert gate.check_compose_contract(compose_json) == []


def test_seeded_ingestion_imports_seed_documents_and_offline_embedder(monkeypatch):
    monkeypatch.setenv("EDURAG_OFFLINE_EMBEDDER", "1")

    from src.document_processor import ingest_corpus

    model, model_name, dim = ingest_corpus._load_embedder()

    assert model_name == "all-MiniLM-L6-v2-offline"
    assert dim == 384
    assert len(ingest_corpus.SEED_DOCUMENTS) >= 5
