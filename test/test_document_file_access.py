"""Reading the original file: GET /api/document/<id>/file.

Students could see a list of course materials and open none of them, so that
screen had nothing to do and the nav item leading to it was misnamed. This
route grants reading and nothing else -- uploading and deleting still require
the lecturer role.

Two things it must get right, because both are easy to get wrong and neither
is visible on screen: the enrolment check, and never letting a name out of the
database escape the upload directory.
"""
from __future__ import annotations

import pytest

from src.api.app import create_app

AUTH = {"Authorization": "Bearer stub"}

ENROLLED = {"user_id": "stu-1", "email": "student@uow.edu.au", "role": "student",
            "enrolled_courses": ["CSIT321"]}
OUTSIDER = {"user_id": "stu-2", "email": "other@uow.edu.au", "role": "student",
            "enrolled_courses": ["CSCI203"]}

DOCUMENT = {"document_id": "doc-1", "course_id": "CSIT321",
            "filename": "lecture-abcd1234.pdf", "original_filename": "Week 1 Lecture.pdf"}


@pytest.fixture
def uploads(tmp_path, monkeypatch):
    d = tmp_path / "uploads"
    d.mkdir()
    (d / "lecture-abcd1234.pdf").write_bytes(b"%PDF-1.4 pretend contents")
    (tmp_path / "secret.txt").write_text("not for anyone")
    monkeypatch.setenv("EDURAG_UPLOAD_DIR", str(d))
    return d


@pytest.fixture
def client(monkeypatch, uploads):
    app = create_app()
    app.config.update(TESTING=True)
    state = app.config["EDURAG_API_STATE"]

    current = {"user": ENROLLED, "document": DOCUMENT}
    monkeypatch.setattr(type(state), "validate_bearer",
                        lambda self, authorization, **kw: current["user"])
    monkeypatch.setattr(type(state), "is_enrolled",
                        lambda self, user, cid: cid in (user.get("enrolled_courses") or []))
    monkeypatch.setattr(type(state), "find_document",
                        lambda self, doc_id: current["document"])

    c = app.test_client()
    c.as_user = lambda u: current.__setitem__("user", u)
    c.holding = lambda d: current.__setitem__("document", d)
    return c


# --- the happy path -----------------------------------------------------

def test_an_enrolled_student_can_read_the_file(client):
    resp = client.get("/api/document/doc-1/file", headers=AUTH)
    assert resp.status_code == 200
    assert resp.data == b"%PDF-1.4 pretend contents"


def test_the_download_is_named_the_way_the_lecturer_uploaded_it(client):
    """Stored under a generated name so two uploads cannot collide; the reader
    should still get the name they recognise."""
    resp = client.get("/api/document/doc-1/file", headers=AUTH)
    assert "Week 1 Lecture.pdf" in resp.headers.get("Content-Disposition", "")


# --- who may read it ----------------------------------------------------

def test_a_student_from_another_course_gets_nothing(client):
    client.as_user(OUTSIDER)
    resp = client.get("/api/document/doc-1/file", headers=AUTH)
    assert resp.status_code == 404
    assert b"pretend contents" not in resp.data


def test_the_refusal_is_a_404_not_a_403(client):
    """A 403 would confirm the id is real, which is enough to walk the id
    space and learn what other courses hold."""
    client.as_user(OUTSIDER)
    assert client.get("/api/document/doc-1/file", headers=AUTH).status_code == 404


def test_signed_out_is_refused(client, monkeypatch):
    state = client.application.config["EDURAG_API_STATE"]
    monkeypatch.setattr(type(state), "validate_bearer", lambda self, a, **kw: None)
    assert client.get("/api/document/doc-1/file", headers=AUTH).status_code == 401


def test_an_unknown_document_is_a_404(client):
    client.holding(None)
    assert client.get("/api/document/nope/file", headers=AUTH).status_code == 404


# --- the file itself ----------------------------------------------------

def test_a_row_whose_file_is_gone_says_so(client):
    """Seeded chunks have no file behind them, and a row can outlive its
    upload."""
    client.holding({**DOCUMENT, "filename": "never-uploaded.pdf"})
    resp = client.get("/api/document/doc-1/file", headers=AUTH)
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "file unavailable"


def test_a_row_with_no_filename_is_a_404(client):
    client.holding({**DOCUMENT, "filename": ""})
    assert client.get("/api/document/doc-1/file", headers=AUTH).status_code == 404


@pytest.mark.parametrize("escape", [
    "../secret.txt",
    "../../etc/passwd",
    "subdir/../../secret.txt",
])
def test_a_name_cannot_escape_the_upload_directory(client, escape):
    """The name is read from the database, so it is not automatically safe to
    join onto a path."""
    client.holding({**DOCUMENT, "filename": escape})
    resp = client.get("/api/document/doc-1/file", headers=AUTH)
    assert resp.status_code == 404
    assert b"not for anyone" not in resp.data


def test_an_absolute_path_cannot_escape_either(client, uploads):
    client.holding({**DOCUMENT, "filename": str(uploads.parent / "secret.txt")})
    resp = client.get("/api/document/doc-1/file", headers=AUTH)
    assert resp.status_code == 404
    assert b"not for anyone" not in resp.data


# --- reading is all it grants -------------------------------------------

def test_the_route_is_read_only(client):
    for method in ("post", "put", "patch", "delete"):
        resp = getattr(client, method)("/api/document/doc-1/file", headers=AUTH)
        assert resp.status_code == 405
