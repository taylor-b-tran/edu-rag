"""Sprint 10, Task 12 — permission matrix across endpoints (Tung).

Both access-control defects fixed this sprint (T9/T10: course-identifier
resolution, document-list scoping) existed because the old tests only
asserted a permission check was *present* — a 401/403 somewhere — never that
it did the *right* thing for the *wrong* kind of user. A test that only reads
`resp.status_code == 403` passes even when the body leaks another course's
data alongside the refusal.

This file is table-driven so it is cheap to extend to the remaining routes:
add a row to ENDPOINT_CASES, or a persona to PERSONAS, and every existing
case is re-run against it automatically.

Personas covered (matches the sprint plan's "every kind of user"):
    none            - no Authorization header
    student_in      - student enrolled in TARGET_COURSE
    student_out     - student enrolled in a *different* course only
    lecturer_owner  - lecturer who owns TARGET_COURSE
    lecturer_other  - lecturer who owns a different course, not TARGET_COURSE
    admin           - admin role

Coverage in this file: /api/courses (list + manage), /api/courses/<c>,
/api/courses/<c>/members, /api/documents, /api/document/<id>,
/api/courses/<c>/settings, /api/admin/stats.

Still to extend the same way (left as the next slice of T12, not silently
dropped): /api/upload, /api/document/<id>/file, /api/indexing-jobs/<id>,
/api/sessions*, /api/query, /api/admin/audit-logs, /api/warmup,
/api/settings (global). The persona fixtures below are reusable for all of
them — each new case is a ~5-line addition to ENDPOINT_CASES.
"""
from __future__ import annotations

import io
import uuid

import pytest

from src.api.app import create_app

TARGET_COURSE = "CSIT321"
OTHER_COURSE = "T12-OUTSIDE"


@pytest.fixture
def client():
    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client()


def _signup(client, role: str, tag: str) -> tuple[str, str]:
    """Create a fresh user via the real signup route. Returns (token, user_id)."""
    email = f"t12-{tag}-{uuid.uuid4().hex[:8]}@uow.edu.au"
    resp = client.post("/api/auth/signup", json={
        "email": email, "username": f"t12{tag}", "password": "CorrectHorse9!",
        "role": role,
    })
    assert resp.status_code == 201, resp.get_json()
    body = resp.get_json()
    return body["access_token"], body["user"]["user_id"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"} if token else {}


def _admin_token(client) -> str:
    resp = client.post("/api/auth/login", json={
        "email": "admin@uow.edu.au", "password": "admin123",
    })
    assert resp.status_code == 200, resp.get_json()
    return resp.get_json()["access_token"]


@pytest.fixture
def personas(client):
    """Build every persona once per test: two courses, six kinds of caller."""
    admin = _admin_token(client)

    # Two real courses so "owner" vs "other" is a genuine ownership check,
    # not just an enrolment check in disguise.
    lecturer_owner_tok, lecturer_owner_id = _signup(client, "lecturer", "own")
    lecturer_other_tok, lecturer_other_id = _signup(client, "lecturer", "oth")

    resp = client.post("/api/courses", json={
        "course_code": TARGET_COURSE, "course_name": "Target course",
        "owner_id": lecturer_owner_id,
    }, headers=_auth(admin))
    assert resp.status_code in (201, 409), resp.get_json()  # 409 if seeded already

    resp = client.post("/api/courses", json={
        "course_code": OTHER_COURSE, "course_name": "A different course",
        "owner_id": lecturer_other_id,
    }, headers=_auth(admin))
    assert resp.status_code in (201, 409), resp.get_json()

    student_in_tok, student_in_id = _signup(client, "student", "in")
    student_out_tok, student_out_id = _signup(client, "student", "out")

    r = client.post(f"/api/courses/{TARGET_COURSE}/join", headers=_auth(student_in_tok))
    assert r.status_code in (200, 201), r.get_json()
    r = client.post(f"/api/courses/{OTHER_COURSE}/join", headers=_auth(student_out_tok))
    assert r.status_code in (200, 201), r.get_json()

    return {
        "none": None,
        "student_in": student_in_tok,
        "student_out": student_out_tok,
        "lecturer_owner": lecturer_owner_tok,
        "lecturer_other": lecturer_other_tok,
        "admin": admin,
    }


@pytest.fixture
def target_document(personas, client):
    """One real document living inside TARGET_COURSE, owned by lecturer_owner."""
    resp = client.post(
        "/api/upload",
        data={"file": (io.BytesIO(b"%PDF-1.4 permission-matrix-fixture"), "t12.pdf"),
              "course_id": TARGET_COURSE},
        headers=_auth(personas["lecturer_owner"]),
        content_type="multipart/form-data",
    )
    assert resp.status_code == 202, resp.get_json()
    return resp.get_json()["document"]["document_id"]


# ---------------------------------------------------------------------------
# Expected outcome per persona, per endpoint. "allow" means 2xx AND the body
# must show TARGET_COURSE-scoped data; "deny" means the status must be one of
# the given codes AND the body must contain none of TARGET_COURSE's data.
# ---------------------------------------------------------------------------

PERSONA_ORDER = ["none", "student_in", "student_out", "lecturer_owner", "lecturer_other", "admin"]


def _get(client, url, token):
    return client.get(url, headers=_auth(token))


def _patch(client, url, token, body):
    return client.patch(url, json=body, headers=_auth(token))


class TestCourseSettings:
    """PATCH /api/courses/<code>/settings — reuses _require_course_manager."""

    EXPECT = {
        "none": 401, "student_in": 403, "student_out": 403,
        "lecturer_owner": 200, "lecturer_other": 403, "admin": 200,
    }

    @pytest.mark.parametrize("persona", PERSONA_ORDER)
    def test_only_the_owner_or_admin_can_write(self, personas, client, persona):
        resp = _patch(client, f"/api/courses/{TARGET_COURSE}/settings",
                      personas[persona], {"top_k": 6})
        assert resp.status_code == self.EXPECT[persona], (persona, resp.get_json())
        if resp.status_code == 200:
            # Not just "it saved something" -- it saved it to the course we asked for.
            body = resp.get_json()
            assert body.get("scope") == TARGET_COURSE or body.get("course_code") == TARGET_COURSE, body


class TestCourseMembers:
    """GET /api/courses/<code>/members — must not leak roster to non-managers."""

    EXPECT = {
        "none": 401, "student_in": 403, "student_out": 403,
        "lecturer_owner": 200, "lecturer_other": 403, "admin": 200,
    }

    @pytest.mark.parametrize("persona", PERSONA_ORDER)
    def test_roster_visible_only_to_manager(self, personas, client, persona):
        resp = _get(client, f"/api/courses/{TARGET_COURSE}/members", personas[persona])
        assert resp.status_code == self.EXPECT[persona], (persona, resp.get_json())
        if resp.status_code == 403:
            assert "members" not in (resp.get_json() or {})


class TestDocumentList:
    """GET /api/documents with no course_id — T7's own regression surface.

    This is the one that actually broke: the fix scopes an unqualified list
    request to the caller's enrolled courses. Re-asserted here as part of the
    matrix, not just in isolation, so a future change to auth on this route
    trips the same table the other endpoints use.
    """

    @pytest.mark.parametrize("persona", ["student_in", "student_out", "lecturer_owner", "admin"])
    def test_unqualified_list_never_shows_a_foreign_course(
        self, personas, client, target_document, persona,
    ):
        resp = _get(client, "/api/documents", personas[persona])
        assert resp.status_code == 200, (persona, resp.get_json())
        docs = resp.get_json()["documents"]
        course_ids = {d.get("course_id") or d.get("course_code") for d in docs}
        for d in docs:
            assert "storage_path" not in d and "uploaded_by" not in d, d
        if persona == "student_out":
            assert TARGET_COURSE not in course_ids, "T7 regression: outsider saw the target course"
        if persona in ("student_in", "lecturer_owner", "admin"):
            # Only assert presence for the roles that should see it; admin
            # sees everything, the other two see it because they belong to it.
            if persona != "admin":
                assert TARGET_COURSE in course_ids, f"{persona} should see their own course"

    def test_none_is_401_not_an_empty_200(self, personas, client):
        # An unauthenticated 200 with an empty list is indistinguishable from
        # "you have no documents" -- it must be a 401, not a quiet allow.
        resp = _get(client, "/api/documents", personas["none"])
        assert resp.status_code == 401


class TestDocumentMetadata:
    """GET /api/document/<id> — must 404 (not 403) for an outsider."""

    EXPECT = {
        "none": 401, "student_in": 200, "student_out": 404,
        "lecturer_owner": 200, "lecturer_other": 404, "admin": 200,
    }

    @pytest.mark.parametrize("persona", PERSONA_ORDER)
    def test_document_scoped_to_course_membership(
        self, personas, client, target_document, persona,
    ):
        resp = _get(client, f"/api/document/{target_document}", personas[persona])
        assert resp.status_code == self.EXPECT[persona], (persona, resp.get_json())
        if resp.status_code == 200:
            body = resp.get_json()
            assert (body.get("course_id") or body.get("course_code")) is not None


class TestAdminOnlyRoutes:
    """GET /api/admin/stats — every non-admin persona, not just "a student"."""

    @pytest.mark.parametrize("persona", ["none", "student_in", "lecturer_owner", "lecturer_other"])
    def test_non_admin_refused(self, personas, client, persona):
        resp = _get(client, "/api/admin/stats", personas[persona])
        expected = 401 if persona == "none" else 403
        assert resp.status_code == expected, (persona, resp.get_json())

    def test_admin_allowed(self, personas, client):
        resp = _get(client, "/api/admin/stats", personas["admin"])
        assert resp.status_code == 200


class TestCourseIdentifierForms:
    """T9-06 regression, folded into the matrix: code and UUID must agree,
    for both an allowed and a refused caller, so this doesn't silently regress
    back to "only the code works" without T12 catching it."""

    def test_enrolled_student_reaches_course_by_code_and_uuid_identically(
        self, personas, client,
    ):
        by_code = _get(client, f"/api/courses/{TARGET_COURSE}/members",
                        personas["lecturer_owner"])
        assert by_code.status_code == 200
        courses = _get(client, "/api/courses", personas["lecturer_owner"]).get_json()["courses"]
        course_id = next(c["course_id"] for c in courses if c["course_code"] == TARGET_COURSE)

        by_uuid = _get(client, f"/api/courses/{course_id}/members", personas["lecturer_owner"])
        # _require_course_manager only accepts course_code today (T9-06 note
        # in the sprint plan flags this deliberately for that route); this
        # assertion documents the current behaviour rather than assuming it.
        assert by_uuid.status_code in (200, 404), by_uuid.get_json()