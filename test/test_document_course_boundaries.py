"""Document visibility and authoritative course identity contracts."""
from unittest.mock import Mock

import pytest
from werkzeug.exceptions import ServiceUnavailable

from src.api import db
from src.api.app import create_app
from src.api.state import APIState


COURSE_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
COURSE_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"


@pytest.fixture
def setup(monkeypatch):
    monkeypatch.setenv("PAEDIA_USE_FIXTURES", "false")
    monkeypatch.setattr(APIState, "__post_init__", lambda self: None)
    app = create_app()
    app.config["TESTING"] = True
    state = app.config["EDURAG_API_STATE"]
    state._db_available = True
    state.fixtures = {
        "courses": [{"course_id": "fixture-a", "course_code": "ALPHA101"}],
        "documents": [{"document_id": "sample", "course_id": "ALPHA101"}],
    }
    rows = [
        {"document_id": "a", "course_id": COURSE_A, "storage_path": "/private/a", "uploaded_by": "owner-a"},
        {"document_id": "b", "course_id": "BETA101", "storage_path": "/private/b"},
        {"document_id": "orphan", "course_id": None},
    ]
    courses = [{"id": COURSE_A, "course_code": "ALPHA101"},
               {"id": COURSE_B, "course_code": "BETA101"}]
    monkeypatch.setattr(db, "get_course_by_ref", lambda ref: next(
        (c for c in courses if ref in (c["id"], c["course_code"])), None))
    monkeypatch.setattr(db, "load_all_documents", lambda: rows)
    memberships = ["ALPHA101"]
    monkeypatch.setattr(db, "get_enrolled_course_codes", lambda uid: memberships[:])
    user = {"user_id": "reader", "role": "student", "enrolled_courses": ["ALPHA101", "BETA101"]}
    monkeypatch.setattr(state, "validate_bearer", lambda authorization: user)
    return app.test_client(), state, user, memberships


@pytest.mark.parametrize("ref", [COURSE_A, "ALPHA101", COURSE_A.upper()])
def test_database_identity_overrides_fixture_alias(setup, ref):
    client, state, user, memberships = setup
    assert state.resolve_course(ref) == (COURSE_A, "ALPHA101")
    assert state.is_enrolled(user, ref)
    response = client.get("/api/documents", query_string={"course_id": ref})
    assert response.status_code == 200
    assert [d["document_id"] for d in response.json["documents"]] == ["a"]


@pytest.mark.parametrize("suffix", ["", "?course_id=", "?course_id=%20%20"])
@pytest.mark.parametrize("role", ["student", "lecturer"])
def test_unscoped_list_returns_only_authorized_payload(setup, suffix, role):
    client, state, user, memberships = setup
    user["role"] = role
    response = client.get("/api/documents" + suffix)
    assert response.status_code == 200
    assert response.json["documents"] == [{"document_id": "a", "course_id": COURSE_A}]


@pytest.mark.parametrize("ref", [COURSE_B, "BETA101", "UNKNOWN", "fixture-a"])
def test_unenrolled_or_unknown_reference_is_denied(setup, ref):
    client, state, user, memberships = setup
    response = client.get("/api/documents", query_string={"course_id": ref})
    assert response.status_code == 403
    assert response.json["documents"] == []


def test_revoked_membership_does_not_trust_token_snapshot(setup):
    client, state, user, memberships = setup
    user["enrolled_courses"] = ["ALPHA101"]
    memberships.clear()
    assert client.get("/api/documents").json["documents"] == []


def test_multiple_memberships_include_both_courses_but_not_orphans(setup):
    client, state, user, memberships = setup
    memberships.append("BETA101")
    documents = client.get("/api/documents").json["documents"]
    assert {d["document_id"] for d in documents} == {"a", "b"}


def test_anonymous_listing_is_denied(setup, monkeypatch):
    client, state, user, memberships = setup
    monkeypatch.setattr(state, "validate_bearer", lambda authorization: None)
    assert client.get("/api/documents").status_code == 401


def test_admin_global_view_excludes_internal_fields(setup):
    client, state, user, memberships = setup
    user["role"] = "admin"
    docs = client.get("/api/documents").json["documents"]
    assert {d["document_id"] for d in docs} == {"a", "b", "orphan"}
    assert all("storage_path" not in d and "uploaded_by" not in d for d in docs)


def test_fixture_documents_require_explicit_mode(setup, monkeypatch):
    client, state, user, memberships = setup
    assert state.find_document("sample") is None
    assert not state.fixture_loaded
    monkeypatch.setenv("PAEDIA_USE_FIXTURES", "true")
    assert state.find_document("sample")["document_id"] == "sample"
    assert state.fixture_loaded


def test_offline_identity_requires_explicit_fixture_mode(setup, monkeypatch):
    client, state, user, memberships = setup
    state._db_available = False
    with pytest.raises(ServiceUnavailable):
        state.resolve_course("ALPHA101")
    monkeypatch.setenv("PAEDIA_USE_FIXTURES", "true")
    assert state.resolve_course("ALPHA101") == ("fixture-a", "ALPHA101")
    assert state.resolve_course("UNKNOWN") == (None, None)


@pytest.mark.parametrize("method", ["get_course_by_ref", "get_enrolled_course_codes"])
def test_database_failure_returns_503_without_fixture_authorization(setup, monkeypatch, method):
    client, state, user, memberships = setup
    monkeypatch.setenv("PAEDIA_USE_FIXTURES", "true")
    monkeypatch.setattr(db, method, Mock(side_effect=RuntimeError("unavailable")))
    response = client.get("/api/documents?course_id=ALPHA101")
    assert response.status_code == 503
    assert response.json["error"] == "service_unavailable"


@pytest.mark.parametrize("ref", ["NOSUCH101", COURSE_B.replace("b", "c"), "not-a-uuid"])
def test_query_does_not_say_whether_an_unknown_course_exists(setup, ref):
    """An unknown course is refused the same way a forbidden one is.

    Answering 404 here and 403 for a real course the caller may not read would
    let any signed-in account tell the two apart. The refusal is the same either
    way, and the caller learns only that this course is not theirs to read.
    """
    client, _state, _user, _memberships = setup
    response = client.post(
        "/api/query",
        json={"query": "What is retrieval-augmented generation?", "course_id": ref},
        headers={"Authorization": "Bearer t"})
    assert response.status_code == 403
    assert response.get_json()["error"] == "Not enrolled in this course."
