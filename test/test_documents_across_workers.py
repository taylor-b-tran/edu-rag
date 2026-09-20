"""Uploaded documents and their indexing jobs must be readable from any worker.

The same fault as
test_tokens_across_workers and test_sessions_across_workers: `APIState` is
hydrated from Postgres once at start-up and only mutated locally afterwards.
Writes reach Postgres, nothing reads back, so with `--workers=2` an upload
handled by one worker does not exist for the other.

Before this change, after an upload that returned 202 and whose chunks were
really in ChromaDB — sixteen reads of the same ids:

    GET /api/indexing-jobs/<job>   404 x14 / 200 x2
    GET /api/document/<id>         404 x12 / 200 x4

So the lecturer was told the upload succeeded and then shown a document that
did not exist, roughly five times out of six, at random. Retrying looked like
it fixed it, which is the worst possible failure shape: nobody can tell a real
loss from a bad draw.

The two directions both matter. A document uploaded elsewhere has to be found,
and a document deleted elsewhere must not come back from a worker that still
holds a copy — deleting also removes the ChromaDB chunks, so a resurrected row
points at nothing.
"""
from __future__ import annotations

import pytest

from src.api.app import create_app


# From fixtures/sample_responses.json — fixture documents carry the course
# UUID, real uploads carry the code, and both have to keep working.
CSIT321_UUID = "c9a1f2e0-4b3d-4e6a-8f1c-2d3e4f5a6b7c"
FIXTURE_DOC_ID = "d4d5e6f7-8a9b-0c1d-2e3f-b4c5d6e7f8a9"   # CSIT321

LECTURER = {"user_id": "lect-1", "email": "lecturer@uow.edu.au", "role": "lecturer",
            "enrolled_courses": ["CSIT321", CSIT321_UUID]}
OUTSIDER = {"user_id": "lect-2", "email": "other@uow.edu.au", "role": "lecturer",
            "enrolled_courses": ["CSCI203"]}
ADMIN = {"user_id": "admin-1", "email": "admin@uow.edu.au", "role": "admin",
         "enrolled_courses": []}
AUTH = {"Authorization": "Bearer stub"}

# What the other worker wrote to Postgres. This worker has never seen either.
REMOTE_DOC = {
    "document_id": "doc-remote", "id": "doc-remote",
    "course_id": "CSIT321", "course_code": "CSIT321", "course_uuid": CSIT321_UUID,
    "original_filename": "week12.pdf", "filename": "week12-ab12cd34.pdf",
    "file_type": "pdf", "file_size_bytes": 4096,
    "status": "indexed", "indexing_status": "indexed",
    "indexing_job_id": "job-remote", "chunks": 12,
    "uploaded_at": "2026-09-09T01:00:00Z",
}
REMOTE_JOB = {
    "job_id": "job-remote", "id": "job-remote", "document_id": "doc-remote",
    "status": "completed", "progress_percent": 100, "error": None,
    "created_at": "2026-09-09T01:00:00Z",
}


@pytest.fixture
def current():
    return {"user": LECTURER}


@pytest.fixture
def postgres():
    """Stands in for what every worker can see."""
    return {"documents": [REMOTE_DOC], "jobs": {REMOTE_JOB["job_id"]: REMOTE_JOB},
            "deleted": []}


@pytest.fixture
def client(monkeypatch, current, postgres):
    app = create_app()
    app.config.update(TESTING=True)
    state = app.config["EDURAG_API_STATE"]

    monkeypatch.setattr(type(state), "db_available", property(lambda self: True))
    monkeypatch.setattr(state, "_db_available", True)
    monkeypatch.setattr(type(state), "validate_bearer",
                        lambda self, authorization: current["user"])
    monkeypatch.setattr(type(state), "is_enrolled",
                        lambda self, user, cid: cid in (user.get("enrolled_courses") or []))

    # The point of these tests: this worker's own state is empty.
    state.uploaded_documents.clear()
    state.indexing_jobs.clear()

    from src.api import db
    monkeypatch.setattr(db, "get_course_by_ref", lambda ref:
                        {"id": CSIT321_UUID, "course_code": "CSIT321"}
                        if ref in ("CSIT321", CSIT321_UUID) else None)
    # Fresh dicts each call, so a test mutating a result cannot rewrite history.
    monkeypatch.setattr(db, "load_all_documents",
                        lambda: [dict(d) for d in postgres["documents"]])
    monkeypatch.setattr(db, "load_all_jobs",
                        lambda: {k: dict(v) for k, v in postgres["jobs"].items()})
    monkeypatch.setattr(db, "delete_document",
                        lambda document_id: postgres["deleted"].append(document_id))

    c = app.test_client()
    c.state = state
    c.postgres = postgres
    return c


@pytest.fixture
def no_chroma(monkeypatch):
    """Deletion also clears ChromaDB chunks; keep that out of a unit test."""
    from src.document_processor import ingest_corpus

    def unavailable():
        raise RuntimeError("ChromaDB not reachable in tests")

    monkeypatch.setattr(ingest_corpus, "get_chroma_client", unavailable)


# --- reading what another worker uploaded ------------------------------

def test_a_document_uploaded_on_another_worker_is_found(client):
    """The 404 x12 of 16 in the measurement above."""
    resp = client.get("/api/document/doc-remote", headers=AUTH)
    assert resp.status_code == 200
    assert resp.get_json()["original_filename"] == "week12.pdf"


def test_its_indexing_job_is_found_too(client):
    """The 404 x14 of 16 — the one the upload screen polls."""
    resp = client.get("/api/indexing-jobs/job-remote", headers=AUTH)
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "completed"


def test_it_appears_in_the_document_list(client):
    resp = client.get("/api/documents", headers=AUTH)
    assert resp.status_code == 200
    ids = {d.get("document_id") or d.get("id") for d in resp.get_json()["documents"]}
    assert "doc-remote" in ids


def test_it_appears_in_the_course_scoped_list(client):
    """Scoping is where the lecturer actually looks: Document Manager filters
    by the course they are viewing."""
    resp = client.get("/api/documents?course_id=CSIT321", headers=AUTH)
    assert resp.status_code == 200
    ids = {d.get("document_id") or d.get("id") for d in resp.get_json()["documents"]}
    assert "doc-remote" in ids


def test_fixture_documents_are_still_listed(client):
    """Reading through to Postgres must not drop the fixture corpus, which has
    no rows of its own and is what the demo mode shows."""
    resp = client.get("/api/documents?course_id=CSIT321", headers=AUTH)
    ids = {d.get("document_id") or d.get("id") for d in resp.get_json()["documents"]}
    assert FIXTURE_DOC_ID in ids


# --- the other direction: deleted elsewhere ----------------------------

def test_postgres_is_authoritative_over_a_stale_local_copy(client):
    """A document deleted on the other worker must not come back.

    Deletion removes the file and its ChromaDB chunks, so serving this
    worker's leftover copy would advertise a document with nothing behind it —
    and `GET /api/documents` would keep listing it forever.
    """
    client.state.uploaded_documents.append(dict(REMOTE_DOC, document_id="ghost", id="ghost"))
    assert client.get("/api/document/ghost", headers=AUTH).status_code == 404

    listed = client.get("/api/documents", headers=AUTH).get_json()["documents"]
    assert "ghost" not in {d.get("document_id") for d in listed}


def test_a_genuinely_missing_document_is_still_404(client):
    assert client.get("/api/document/nope", headers=AUTH).status_code == 404


def test_a_genuinely_missing_job_is_still_404(client):
    assert client.get("/api/indexing-jobs/nope", headers=AUTH).status_code == 404


# --- authorisation is unchanged by any of this -------------------------

def test_someone_outside_the_course_still_gets_404(client, current):
    """404 rather than 403 on purpose: a 403 would confirm the id is real.
    Reading through to Postgres must not turn that into a disclosure."""
    current["user"] = OUTSIDER
    assert client.get("/api/document/doc-remote", headers=AUTH).status_code == 404
    assert client.get("/api/indexing-jobs/job-remote", headers=AUTH).status_code == 404


def test_the_scoped_list_still_refuses_a_course_you_are_not_in(client, current):
    current["user"] = OUTSIDER
    assert client.get("/api/documents?course_id=CSIT321", headers=AUTH).status_code == 403


# --- deleting across workers -------------------------------------------

def test_a_document_uploaded_elsewhere_can_be_deleted(client, no_chroma):
    """`delete_uploaded_document` filtered this worker's list, so deleting a
    document the other worker had handled reported "not found" while the row,
    the file and the chunks all stayed."""
    resp = client.delete("/api/document/doc-remote", headers=AUTH)
    assert resp.status_code == 200
    assert client.postgres["deleted"] == ["doc-remote"]


def test_a_fixture_document_is_still_not_deletable(client, no_chroma):
    """Fixture documents have no file and no chunks of their own. Treating one
    as a real upload would delete another document's chunks by filename, so
    deletion looks only at uploads."""
    resp = client.delete(f"/api/document/{FIXTURE_DOC_ID}", headers=AUTH)
    assert resp.status_code == 404
    assert client.postgres["deleted"] == []


# --- the no-database case, which is how the suite runs ------------------

def test_without_postgres_this_workers_own_upload_still_answers(client, monkeypatch):
    """The dictionary stays the source of truth when there is no database."""
    monkeypatch.setattr(client.state, "_db_available", False)
    client.state.uploaded_documents.append(dict(REMOTE_DOC, document_id="local", id="local"))

    assert client.get("/api/document/local", headers=AUTH).status_code == 200


def test_a_job_absent_from_postgres_is_not_resurrected(client):
    """A local copy cannot override a cascade delete on another worker."""
    client.state.indexing_jobs["job-local"] = dict(REMOTE_JOB, job_id="job-local",
                                                   id="job-local", status="running")
    resp = client.get("/api/indexing-jobs/job-local", headers=AUTH)
    assert resp.status_code == 404
    assert "job-local" not in client.state.indexing_jobs


def test_deleted_document_and_job_disappear_on_another_worker(client):
    assert client.get("/api/indexing-jobs/job-remote", headers=AUTH).status_code == 200
    client.postgres["documents"].clear()
    client.postgres["jobs"].clear()
    assert client.get("/api/document/doc-remote", headers=AUTH).status_code == 404
    assert client.get("/api/indexing-jobs/job-remote", headers=AUTH).status_code == 404


@pytest.mark.parametrize("user", [OUTSIDER, ADMIN])
def test_orphan_job_fails_closed_even_without_database(client, current, monkeypatch, user):
    current["user"] = user
    monkeypatch.setattr(client.state, "_db_available", False)
    client.state.indexing_jobs["orphan"] = dict(REMOTE_JOB, document_id="missing")
    assert client.get("/api/indexing-jobs/orphan", headers=AUTH).status_code == 404


# --- what the admin dashboard reports -----------------------------------

def test_admin_stats_count_the_deployment_not_one_worker(client, current):
    """The dashboard read `len(state.uploaded_documents)` straight off the
    local dictionary, so the same page showed different totals depending on
    which worker served it."""
    current["user"] = ADMIN
    stats = client.get("/api/admin/stats", headers=AUTH).get_json()
    assert stats["uploaded_documents"] == 1
    assert stats["indexing_jobs"] == 1
