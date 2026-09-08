"""Regression tests for document-level authorization (T8-29).

Three routes checked only that the caller was logged in, or at most that they
held a role, and never that the document belonged to a course they are in:

  GET    /api/document/<id>       any user could read any course's metadata
  DELETE /api/document/<id>       any lecturer could delete anyone's material
  GET    /api/indexing-jobs/<id>  no check at all, and its error field can
                                  quote server-side file paths

The demo fixtures enroll student@ and lecturer@ in CSIT321 and CSCI203, so a
course outside that set is what an outsider looks like.
"""
from __future__ import annotations

import io

import pytest

from src.api.app import create_app


OUTSIDE_COURSE = "CSIT999"


@pytest.fixture
def client():
    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client()


def _token(client, email: str, password: str) -> str:
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.get_json()
    return resp.get_json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def foreign_document(client):
    """A document in a course nobody but an admin is enrolled in."""
    admin = _token(client, "admin@uow.edu.au", "admin123")
    resp = client.post(
        "/api/upload",
        data={"file": (io.BytesIO(b"%PDF-1.4 x"), "secret.pdf"), "course_id": OUTSIDE_COURSE},
        headers=_auth(admin),
        content_type="multipart/form-data",
    )
    assert resp.status_code == 202, resp.get_json()
    body = resp.get_json()
    return body["document"]["document_id"], body["job_id"]


def test_student_cannot_read_a_document_from_another_course(client, foreign_document):
    doc_id, _ = foreign_document
    token = _token(client, "student@uow.edu.au", "student123")

    resp = client.get(f"/api/document/{doc_id}", headers=_auth(token))

    assert resp.status_code == 404, "must not confirm the document exists"


def test_lecturer_cannot_delete_another_courses_document(client, foreign_document):
    doc_id, _ = foreign_document
    token = _token(client, "lecturer@uow.edu.au", "lecturer123")

    resp = client.delete(f"/api/document/{doc_id}", headers=_auth(token))

    assert resp.status_code == 404
    # and it is still there afterwards
    admin = _token(client, "admin@uow.edu.au", "admin123")
    assert client.get(f"/api/document/{doc_id}", headers=_auth(admin)).status_code == 200


def test_student_cannot_read_another_courses_indexing_job(client, foreign_document):
    _, job_id = foreign_document
    token = _token(client, "student@uow.edu.au", "student123")

    resp = client.get(f"/api/indexing-jobs/{job_id}", headers=_auth(token))

    assert resp.status_code == 404


def test_enrolled_user_can_still_read_their_own_courses_document(client):
    """The fix must not break the path that is supposed to work."""
    lecturer = _token(client, "lecturer@uow.edu.au", "lecturer123")
    upload = client.post(
        "/api/upload",
        data={"file": (io.BytesIO(b"%PDF-1.4 x"), "lecture.pdf"), "course_id": "CSIT321"},
        headers=_auth(lecturer),
        content_type="multipart/form-data",
    )
    assert upload.status_code == 202
    doc_id = upload.get_json()["document"]["document_id"]

    student = _token(client, "student@uow.edu.au", "student123")
    resp = client.get(f"/api/document/{doc_id}", headers=_auth(student))

    assert resp.status_code == 200
    assert resp.get_json()["original_filename"] == "lecture.pdf"


def test_admin_still_reaches_everything(client, foreign_document):
    doc_id, job_id = foreign_document
    admin = _token(client, "admin@uow.edu.au", "admin123")

    assert client.get(f"/api/document/{doc_id}", headers=_auth(admin)).status_code == 200
    assert client.get(f"/api/indexing-jobs/{job_id}", headers=_auth(admin)).status_code == 200


def test_unknown_document_is_still_a_404(client):
    token = _token(client, "student@uow.edu.au", "student123")
    assert client.get("/api/document/does-not-exist", headers=_auth(token)).status_code == 404
