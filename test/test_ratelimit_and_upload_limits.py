"""Regression tests for T8-20 (per-user rate limiting) and T8-28 (upload limits).

The rate limit used to key on request.remote_addr. Streamlit calls the API
server-side, so every student arrived as the same container address and the
10-per-minute cap was one bucket shared by the whole class.

Uploads had no size cap and no type check, and were stored under the uploader's
own filename, so two people uploading week1.pdf overwrote each other on disk and
deleting either one removed both sets of ChromaDB chunks.
"""
from __future__ import annotations

import io

import pytest

from src.api.app import create_app
from src.api.routes import query as query_routes


@pytest.fixture
def client():
    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client()


@pytest.fixture(autouse=True)
def clear_rate_store():
    query_routes._RATE_STORE.clear()
    yield
    query_routes._RATE_STORE.clear()


def _token(client, email: str, password: str) -> str:
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.get_json()
    return resp.get_json()["access_token"]


def _ask(client, token: str):
    # A two-word question is rejected as ambiguous before retrieval or the model
    # run, which keeps this test fast. The rate limiter has already counted it.
    return client.post(
        "/api/query",
        json={"query": "hi there", "course_id": "CSIT321"},
        headers={"Authorization": f"Bearer {token}"},
    )


# ─── T8-20 ────────────────────────────────────────────────────────────

def test_rate_limit_is_per_user_not_shared(client):
    """One user exhausting their budget must not lock everyone else out."""
    student = _token(client, "student@uow.edu.au", "student123")
    lecturer = _token(client, "lecturer@uow.edu.au", "lecturer123")

    for _ in range(query_routes._RATE_MAX):
        assert _ask(client, student).status_code != 429
    assert _ask(client, student).status_code == 429, "the student's own budget should run out"

    assert _ask(client, lecturer).status_code != 429, \
        "a different user must still have their own budget"


def test_unauthenticated_request_is_rejected_before_counting(client):
    resp = client.post("/api/query", json={"query": "hi there", "course_id": "CSIT321"})
    assert resp.status_code == 401
    assert query_routes._RATE_STORE == {}, "anonymous calls should not occupy a bucket"


def test_expired_windows_are_pruned(client):
    """The store used to grow one entry per key for the life of the process."""
    query_routes._RATE_STORE["someone-long-gone"] = [0.0]
    token = _token(client, "student@uow.edu.au", "student123")

    _ask(client, token)

    assert "someone-long-gone" not in query_routes._RATE_STORE


# ─── T8-28 ────────────────────────────────────────────────────────────

def _upload(client, token: str, filename: str, payload: bytes = b"%PDF-1.4 test"):
    return client.post(
        "/api/upload",
        data={"file": (io.BytesIO(payload), filename), "course_id": "CSIT321"},
        headers={"Authorization": f"Bearer {token}"},
        content_type="multipart/form-data",
    )


def test_unsupported_file_type_is_rejected(client):
    token = _token(client, "lecturer@uow.edu.au", "lecturer123")
    resp = _upload(client, token, "notes.txt")
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "unsupported file type"


def test_oversized_upload_is_rejected(client):
    """Flask refuses the body before the view runs, so nothing is buffered."""
    client.application.config["MAX_CONTENT_LENGTH"] = 1024
    token = _token(client, "lecturer@uow.edu.au", "lecturer123")

    resp = _upload(client, token, "big.pdf", payload=b"x" * 4096)

    assert resp.status_code == 413


def test_same_filename_twice_is_stored_under_distinct_names(client):
    token = _token(client, "lecturer@uow.edu.au", "lecturer123")

    first = _upload(client, token, "week1.pdf")
    second = _upload(client, token, "week1.pdf")

    assert first.status_code == 202 and second.status_code == 202
    a = first.get_json()["document"]
    b = second.get_json()["document"]

    assert a["filename"] != b["filename"], "stored names must not collide"
    assert a["original_filename"] == b["original_filename"] == "week1.pdf", \
        "the uploader's own name is what the UI shows"
