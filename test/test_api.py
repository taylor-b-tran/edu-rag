from __future__ import annotations

import io

from src.api.app import create_app


def _client():
    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client()


def _login(test_client, email: str, password: str):
    resp = test_client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed: {resp.get_json()}"
    return resp.get_json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ─── Health ───────────────────────────────────────────────────────────


def test_health_reports_core_routes():
    response = _client().get("/api/health")

    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "ok"
    assert "/api/query" in body["routes"]
    assert "/api/upload" in body["routes"]


# ─── Auth ─────────────────────────────────────────────────────────────


def test_login_returns_tokens_with_correct_password():
    c = _client()
    response = c.post("/api/auth/login", json={"email": "student@uow.edu.au", "password": "student123"})

    assert response.status_code == 200
    body = response.get_json()
    assert body["access_token"].startswith("dev_access_")
    assert body["user"]["role"] == "student"


def test_login_rejects_wrong_password():
    c = _client()
    response = c.post("/api/auth/login", json={"email": "student@uow.edu.au", "password": "wrongpassword"})

    assert response.status_code == 401


def test_login_rejects_unknown_email():
    c = _client()
    response = c.post("/api/auth/login", json={"email": "nobody@uow.edu.au", "password": "anything"})

    assert response.status_code == 401


def test_login_rejects_missing_fields():
    c = _client()
    assert c.post("/api/auth/login", json={"email": "student@uow.edu.au"}).status_code == 400
    assert c.post("/api/auth/login", json={"password": "student123"}).status_code == 400


# ─── Query ────────────────────────────────────────────────────────────


def test_query_returns_grounded_answer_with_citations_when_authenticated():
    """Asserts the full /api/query contract — works in both ChromaDB-backed and
    fixture-fallback modes (the response shape is identical; only `model_used` and
    `source_references` content differ)."""
    c = _client()
    token = _login(c, "student@uow.edu.au", "student123")

    response = c.post(
        "/api/query",
        json={
            "query": "What is Retrieval-Augmented Generation and how does it differ from standard LLMs?",
            "course_id": "CSIT321",
        },
        headers=_auth(token),
    )

    assert response.status_code == 200
    body = response.get_json()

    assert isinstance(body.get("answer"), str) and body["answer"].strip()
    assert body["session_id"]
    assert body.get("backend_mode") == "chromadb"
    assert isinstance(body.get("model_used"), str) and body["model_used"]
    assert isinstance(body.get("source_references"), list)
    assert isinstance(body.get("is_fallback"), bool)
    assert body.get("confidence") in {"Low", "Medium", "High"}
    assert isinstance(body.get("confidence_score"), (int, float))
    assert 0.0 <= body["confidence_score"] <= 1.0
    assert isinstance(body.get("latency_ms"), int) and body["latency_ms"] >= 0

    if not body["is_fallback"] and body["model_used"] != "fixture":
        for ref in body["source_references"]:
            assert "source_file" in ref or "source" in ref


def test_query_off_topic_question_does_not_fabricate_citations():
    """Off-topic queries must either return is_fallback=true OR drop to Low confidence
    with no citations — they must NOT fabricate sources from the seeded corpus."""
    c = _client()
    token = _login(c, "student@uow.edu.au", "student123")

    response = c.post(
        "/api/query",
        json={"query": "What is the best chocolate cake recipe?", "course_id": "CSIT321"},
        headers=_auth(token),
    )

    assert response.status_code == 200
    body = response.get_json()

    is_low_confidence = body.get("confidence") == "Low"
    is_explicit_fallback = body.get("is_fallback") is True
    has_no_sources = len(body.get("source_references", [])) == 0
    assert is_low_confidence or is_explicit_fallback or has_no_sources, (
        f"Off-topic query produced grounded answer: {body}"
    )


def test_query_returns_401_without_token():
    c = _client()
    response = c.post(
        "/api/query",
        json={"query": "What is RAG?", "course_id": "CSIT321"},
    )

    assert response.status_code == 401


def test_query_returns_403_for_unenrolled_course():
    c = _client()
    # lecturer@uow.edu.au is only enrolled in CSIT214
    token = _login(c, "lecturer@uow.edu.au", "lecturer123")

    response = c.post(
        "/api/query",
        json={"query": "Tell me about RAG", "course_id": "CSIT321"},
        headers=_auth(token),
    )

    assert response.status_code == 403


# ─── Documents ────────────────────────────────────────────────────────


def test_upload_queues_document_when_lecturer_authenticated():
    c = _client()
    token = _login(c, "lecturer@uow.edu.au", "lecturer123")

    response = c.post(
        "/api/upload",
        data={
            "course_id": "CSIT214",
            "file": (io.BytesIO(b"demo content"), "demo.pdf"),
        },
        content_type="multipart/form-data",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 202
    body = response.get_json()
    assert body["document"]["filename"] == "demo.pdf"
    assert body["indexing_job"]["status"] == "queued"


def test_upload_returns_401_without_token():
    c = _client()
    response = c.post(
        "/api/upload",
        data={"course_id": "CSIT321", "file": (io.BytesIO(b"x"), "x.pdf")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 401


def test_upload_returns_403_for_student_role():
    c = _client()
    token = _login(c, "student@uow.edu.au", "student123")

    response = c.post(
        "/api/upload",
        data={"course_id": "CSIT321", "file": (io.BytesIO(b"x"), "x.pdf")},
        content_type="multipart/form-data",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_documents_returns_401_without_token():
    c = _client()
    assert c.get("/api/documents").status_code == 401


def test_documents_returns_list_when_authenticated():
    c = _client()
    token = _login(c, "student@uow.edu.au", "student123")

    response = c.get("/api/documents", headers=_auth(token))

    assert response.status_code == 200
    assert isinstance(response.get_json()["documents"], list)


# ─── Sessions ─────────────────────────────────────────────────────────


def test_sessions_returns_collection_after_query():
    c = _client()
    token = _login(c, "student@uow.edu.au", "student123")

    c.post(
        "/api/query",
        json={"query": "Can you summarize the key steps in the RAG pipeline?", "course_id": "CSIT321"},
        headers=_auth(token),
    )

    sessions_response = c.get("/api/sessions", headers=_auth(token))
    assert sessions_response.status_code == 200
    assert len(sessions_response.get_json()["sessions"]) == 1
