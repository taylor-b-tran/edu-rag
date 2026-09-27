"""A citation names the file as its uploader did.

Chunks carry the stored file name, which has a suffix so two uploads of one file stay apart. The
citation chip was built from it, so a file uploaded as "notes.pdf" was cited as
"notes-bc36086a.pdf" while the document table beside it said "notes.pdf". These tests go in
through POST /api/query.
"""
from __future__ import annotations

import pytest

from src.api.app import create_app

STUDENT = {"user_id": "stu-1", "email": "student@uow.edu.au", "role": "student",
           "enrolled_courses": ["OWNED101"]}
OWNED = {"course_code": "OWNED101", "course_name": "Owned", "owner_id": "lect-1"}
AUTH = {"Authorization": "Bearer stub"}

DOCUMENTS = [
    {"document_id": "d-1", "course_id": "OWNED101", "filename": "notes-bc36086a.pdf",
     "original_filename": "notes.pdf"},
    {"document_id": "d-2", "course_id": "OWNED101", "filename": "W5_Decision_Trees.pdf",
     "original_filename": "W5_Decision_Trees.pdf"},
]


class _Generator:
    def __init__(self, refs):
        self.refs = refs

    def generate(self, query, **kwargs):
        from src.document_processor.rag_pipeline import GeneratedResponse
        return GeneratedResponse(
            answer="An answer [S1].", source_refs=self.refs, is_fallback=False,
            model_used="stub", top_chunks=[], confidence="High",
            confidence_score=0.7, response_style="concise",
        )


@pytest.fixture
def recorded():
    return {}


@pytest.fixture
def make_client(monkeypatch, recorded):
    def _make(refs, load_documents=lambda: [dict(d) for d in DOCUMENTS]):
        from src.api.routes import query as query_mod
        query_mod._RATE_STORE.clear()

        app = create_app()
        app.config.update(TESTING=True)
        state = app.config["EDURAG_API_STATE"]
        monkeypatch.setattr(state, "_db_available", True)
        monkeypatch.setattr(type(state), "validate_bearer", lambda self, authorization: STUDENT)
        monkeypatch.setattr(type(state), "is_enrolled", lambda self, user, cid: True)
        monkeypatch.setattr(type(state), "get_generator", lambda self: _Generator(refs))

        def _record(self, **kw):
            recorded.update(kw)
            return "sess-1"
        monkeypatch.setattr(type(state), "record_session_message", _record)

        from src.api import db
        monkeypatch.setattr(db, "get_course_by_ref", lambda ref:
                            {**OWNED, "id": "owned-id"} if ref in ("OWNED101", "owned-id") else None)
        monkeypatch.setattr(db, "get_course_by_code", lambda code: OWNED)
        monkeypatch.setattr(db, "get_settings", lambda scope: {})
        monkeypatch.setattr(db, "load_all_documents", load_documents)
        return app.test_client()
    return _make


def _ask(client):
    response = client.post("/api/query",
                           json={"query": "What is chunking?", "course_id": "OWNED101"},
                           headers=AUTH)
    assert response.status_code == 200, response.get_json()
    return response.get_json()["source_references"]


def test_an_uploaded_file_is_cited_by_the_name_it_was_uploaded_as(make_client):
    refs = _ask(make_client([{"source_file": "notes-bc36086a.pdf", "page": 7}]))
    assert refs[0]["filename"] == "notes.pdf"


def test_the_stored_name_is_kept_for_the_vector_store(make_client):
    refs = _ask(make_client([{"source_file": "notes-bc36086a.pdf", "page": 7}]))
    assert refs[0]["source_file"] == "notes-bc36086a.pdf"


def test_a_file_whose_name_never_changed_is_cited_unchanged(make_client):
    refs = _ask(make_client([{"source_file": "W5_Decision_Trees.pdf", "page": 5}]))
    assert refs[0]["filename"] == "W5_Decision_Trees.pdf"


def test_a_file_with_no_row_keeps_its_stored_name(make_client):
    refs = _ask(make_client([{"source_file": "seeded-without-a-row.pdf", "page": 1}]))
    assert refs[0]["filename"] == "seeded-without-a-row.pdf"


def test_an_unreadable_document_table_does_not_fail_the_answer(make_client):
    def _down():
        raise RuntimeError("database unreachable")
    refs = _ask(make_client([{"source_file": "notes-bc36086a.pdf", "page": 7}],
                            load_documents=_down))
    assert refs[0]["filename"] == "notes-bc36086a.pdf"


def test_references_without_a_stored_name_are_left_alone(make_client):
    refs = _ask(make_client([{"filename": "RAG_Pipeline_Overview.pdf", "page_number": 9}]))
    assert refs == [{"filename": "RAG_Pipeline_Overview.pdf", "page_number": 9}]


def test_the_conversation_history_keeps_the_uploaded_name(make_client, recorded):
    _ask(make_client([{"source_file": "notes-bc36086a.pdf", "page": 7}]))
    stored = recorded["answer"]["source_references"]
    assert stored[0]["filename"] == "notes.pdf"


def test_several_citations_are_each_named(make_client):
    refs = _ask(make_client([
        {"source_file": "notes-bc36086a.pdf", "page": 7},
        {"source_file": "W5_Decision_Trees.pdf", "page": 5},
    ]))
    assert [r["filename"] for r in refs] == ["notes.pdf", "W5_Decision_Trees.pdf"]
