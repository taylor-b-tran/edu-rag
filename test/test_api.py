from __future__ import annotations

import io

from src.api.app import create_app


def client():
    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client()


def test_health_reports_core_routes():
    response = client().get("/api/health")

    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "ok"
    assert "/api/query" in body["routes"]
    assert "/api/upload" in body["routes"]


def test_login_returns_demo_tokens():
    response = client().post(
        "/api/auth/login",
        json={"email": "student@uow.edu.au", "password": "password123"},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["access_token"].startswith("dev_access_")
    assert body["user"]["role"] == "student"


def test_query_returns_fixture_answer_and_session_id():
    response = client().post(
        "/api/query",
        json={
            "query": "What is Retrieval-Augmented Generation and how does it differ from standard LLMs?",
            "course_id": "CSIT321",
        },
    )

    assert response.status_code == 200
    body = response.get_json()
    assert "Retrieval-Augmented Generation" in body["answer"]
    assert body["session_id"]
    assert body["source_references"]


def test_upload_queues_document_and_indexing_job():
    response = client().post(
        "/api/upload",
        data={
            "course_id": "CSIT321",
            "file": (io.BytesIO(b"demo content"), "demo.pdf"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 202
    body = response.get_json()
    assert body["document"]["filename"] == "demo.pdf"
    assert body["indexing_job"]["status"] == "queued"


def test_documents_and_sessions_return_collections():
    test_client = client()
    test_client.post(
        "/api/query",
        json={"query": "Can you summarize the key steps in the RAG pipeline?", "course_id": "CSIT321"},
    )

    documents_response = test_client.get("/api/documents")
    sessions_response = test_client.get("/api/sessions")

    assert documents_response.status_code == 200
    assert sessions_response.status_code == 200
    assert isinstance(documents_response.get_json()["documents"], list)
    assert len(sessions_response.get_json()["sessions"]) == 1
