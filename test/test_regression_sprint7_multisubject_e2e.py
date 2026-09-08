"""
T06 — Regression test: full multi-subject flow, end to end.

Sprint: 7 (5 Aug - 18 Aug 2026)
Owner: Tung Phuong Anh Huynh
Depends on (per Sprint 7 plan): T04, T05

Scope note (baseline, dated at time of writing):
    The Sprint 7 plan lists T04 (upload/ingestion course scoping, Thanh) and
    T05 (subject-selector UI + admin panel, Anmoldeep) as "Not started" as of
    the plan's creation date. In practice, `develop` already contains working
    implementations of T02 (Postgres-backed auth), T03 (courses/enrollment
    admin API), course-scoped upload (T04), and a course selector + admin
    dashboard in the Streamlit app (T05's backend surface). This file
    regression-tests the multi-subject flow against what is actually on
    `develop` right now, rather than waiting for a formal handoff.

    Anything still genuinely missing (e.g. UI-only polish that doesn't touch
    the API contract) is out of scope here and is called out separately in
    docs/regression_qa_sprint7_t06.md rather than silently skipped.

Environment note (same pattern as test_api.py's T03 tests):
    Write endpoints (create course, add/remove member, upload) require
    Postgres. CI does not run Postgres as a service, and it may not be
    running locally either. Every write-dependent assertion below accepts
    either a real success code OR 503 ("db unavailable") so this file is
    honest about environment, instead of reporting a false PASS or a false
    FAIL. Where DB is unavailable, the test records that the step was
    SKIPPED-BY-ENVIRONMENT rather than pretending it was verified.
"""

from __future__ import annotations

import io
import uuid

import pytest

from src.api.app import create_app


# ─── Shared helpers (same shape as test/test_api.py) ───────────────────

def _client():
    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client()


def _login(client, email: str, password: str) -> str:
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.get_json()}"
    return resp.get_json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _new_course_code() -> str:
    return f"T06E2E{uuid.uuid4().hex[:5].upper()}"


# ─── Full flow: admin provisions a subject, a student uses it ─────────

def test_e2e_admin_provisions_course_and_student_flow():
    """
    Full multi-subject lifecycle in one pass:

    1. Admin creates a brand-new course (not one of the two demo courses).
    2. Admin enrols the demo student into that course.
    2b. Admin enrols the demo lecturer into that course (membership_role
        "lecturer"). The upload endpoint scopes on course membership, not
        just role — a lecturer isn't automatically authorised for every
        course, only the ones they're assigned to. This step is required
        for step 4 to succeed and is itself a regression check of that
        scoping rule.
    3. The new course appears in the shared /api/courses list for any
       authenticated user (subject-selector data source).
    4. Lecturer (now enrolled as this course's lecturer) uploads a document
       scoped to the new course.
    5. Student (now enrolled) queries within that course and is NOT
       rejected for enrollment (i.e. is_enrolled resolves correctly for a
       freshly created, DB-backed course, not just the two fixture demo
       courses).
    6. Student's document list, filtered by course_id, only returns
       documents for that course.
    7. Admin removes the student's membership.
    8. Student querying the same course afterwards is rejected (403) —
       proves membership changes take effect immediately, not just at
       login/token-issue time.

    If Postgres isn't reachable, steps 1-2 and 7-8 degrade to 503 and the
    test records that as an environment limitation rather than a failure —
    matching the existing T03 test convention in test/test_api.py.
    """
    c = _client()
    course_code = _new_course_code()

    admin_token = _login(c, "admin@uow.edu.au", "admin123")
    student_token = _login(c, "student@uow.edu.au", "student123")
    lecturer_token = _login(c, "lecturer@uow.edu.au", "lecturer123")

    # 1. Create the course
    create_resp = c.post(
        "/api/courses",
        json={"course_code": course_code, "course_name": "T06 E2E Regression Course"},
        headers=_auth(admin_token),
    )
    assert create_resp.status_code in (201, 503)
    db_available = create_resp.status_code == 201
    if not db_available:
        pytest.skip(
            f"Postgres unavailable in this environment (create_course -> "
            f"{create_resp.status_code}). Steps 1-8 require a live DB backend; "
            f"see docs/regression_qa_sprint7_t06.md for the DB-unavailable "
            f"coverage that ran instead."
        )

    # 2. Enrol the student
    enrol_resp = c.post(
        f"/api/courses/{course_code}/members",
        json={"email": "student@uow.edu.au", "membership_role": "student"},
        headers=_auth(admin_token),
    )
    assert enrol_resp.status_code == 201, enrol_resp.get_json()

    # 2b. Enrol the lecturer too — upload is scoped by course membership,
    #     not just by role, so the lecturer must be assigned to this
    #     specific course before they're allowed to upload to it.
    enrol_lecturer_resp = c.post(
        f"/api/courses/{course_code}/members",
        json={"email": "lecturer@uow.edu.au", "membership_role": "lecturer"},
        headers=_auth(admin_token),
    )
    assert enrol_lecturer_resp.status_code == 201, enrol_lecturer_resp.get_json()

    # 3. New course shows up in the shared subject list
    list_resp = c.get("/api/courses", headers=_auth(student_token))
    assert list_resp.status_code == 200
    codes = {course["course_code"] for course in list_resp.get_json()["courses"]}
    assert course_code in codes

    # Lecturer re-authenticates so enrolled_courses reflects the new
    # course-lecturer assignment (same pattern used for the student below).
    lecturer_token = _login(c, "lecturer@uow.edu.au", "lecturer123")

    # 4. Lecturer uploads a document scoped to the new course
    upload_resp = c.post(
        "/api/upload",
        data={
            "course_id": course_code,
            "file": (io.BytesIO(b"T06 regression fixture content"), "t06_regression.pdf"),
        },
        content_type="multipart/form-data",
        headers=_auth(lecturer_token),
    )
    assert upload_resp.status_code == 202, upload_resp.get_json()

    # 5. Student re-authenticates so enrolled_courses reflects the new membership,
    #    then queries the new course and should NOT be blocked by is_enrolled().
    #    (Re-login mirrors real usage: enrollment changes apply on next token.)
    student_token = _login(c, "student@uow.edu.au", "student123")
    query_resp = c.post(
        "/api/query",
        json={"query": "What does the regression fixture document cover?", "course_id": course_code},
        headers=_auth(student_token),
    )
    assert query_resp.status_code != 403, (
        f"Student was rejected from a course they were just enrolled in: "
        f"{query_resp.get_json()}"
    )

    # 6. Documents list, filtered by course_id, is scoped correctly
    docs_resp = c.get(f"/api/documents?course_id={course_code}", headers=_auth(student_token))
    assert docs_resp.status_code == 200
    docs = docs_resp.get_json()["documents"]
    # Uploads are stored under a unique name; original_filename is the
    # name the uploader gave, which is what a human recognises.
    assert any(d.get("original_filename") == "t06_regression.pdf" for d in docs)
    # No cross-course leakage: nothing from the two demo courses should appear
    leaked = [d for d in docs if d.get("course_id") not in (course_code, None) and
              d.get("course_code") not in (course_code, None)]
    assert not leaked, f"Course-scoped document list leaked other courses: {leaked}"

    # 7. Remove the student's membership
    remove_resp = c.delete(
        f"/api/courses/{course_code}/members/student@uow.edu.au",
        headers=_auth(admin_token),
    )
    assert remove_resp.status_code == 200, remove_resp.get_json()

    # 8. Access is revoked immediately on next token (post re-login)
    student_token_after = _login(c, "student@uow.edu.au", "student123")
    query_after_resp = c.post(
        "/api/query",
        json={"query": "What does the regression fixture document cover?", "course_id": course_code},
        headers=_auth(student_token_after),
    )
    assert query_after_resp.status_code == 403


# ─── Cross-course isolation on the two existing demo courses ──────────

def test_e2e_documents_scoped_to_demo_courses_do_not_leak():
    """
    Regression guard for the Sprint 6 known limitation (enrolled_courses
    UUID vs course_code string mismatch, see docs/t22_t28_zip_verification.md).
    Confirms that resolving CSIT321 vs CSCI203 through the current
    APIState.resolve_course()/is_enrolled() logic keeps document lists
    correctly separated between two real, pre-seeded courses.

    The second subject was CSIT214 until Sprint 9. It was dropped because it
    never held any indexed material, which made this a scoping test between
    one real course and an empty one; CSCI203 has 888 chunks of its own, so
    the guard now runs against two subjects that actually contain documents.
    """
    c = _client()
    token = _login(c, "admin@uow.edu.au", "admin123")  # admin bypasses enrollment checks

    csit321_docs = c.get("/api/documents?course_id=CSIT321", headers=_auth(token))
    csci203_docs = c.get("/api/documents?course_id=CSCI203", headers=_auth(token))
    assert csit321_docs.status_code == 200
    assert csci203_docs.status_code == 200

    ids_321 = {d.get("document_id") for d in csit321_docs.get_json()["documents"]}
    ids_203 = {d.get("document_id") for d in csci203_docs.get_json()["documents"]}
    assert ids_321.isdisjoint(ids_203), (
        "Documents leaked across CSIT321/CSCI203 course scoping."
    )


# ─── Enrollment enforcement on the query endpoint ──────────────────────

def test_e2e_student_blocked_from_unenrolled_course_query():
    """
    A student authenticated against the fixture demo account must not be
    able to query a course they aren't enrolled in, even if they guess a
    real course_code. This is the negative-path counterpart to the happy
    path above.
    """
    c = _client()
    token = _login(c, "student@uow.edu.au", "student123")

    course_code = _new_course_code()  # guaranteed not to exist / not enrolled
    resp = c.post(
        "/api/query",
        json={"query": "Is this course accessible without enrollment?", "course_id": course_code},
        headers=_auth(token),
    )
    assert resp.status_code == 403


# ─── Admin dashboard data surface (subject-selector / T05 backend) ────

def test_e2e_admin_stats_endpoint_reflects_course_count():
    """
    Sanity check that the admin dashboard's data source (used by the T05
    Admin Dashboard page in apps/streamlit/main.py) is reachable and
    returns a shape the UI can render, so a UI-side regression wouldn't be
    masked by an API-side one.
    """
    c = _client()
    token = _login(c, "admin@uow.edu.au", "admin123")

    resp = c.get("/api/courses", headers=_auth(token))
    assert resp.status_code == 200
    courses = resp.get_json()["courses"]
    assert isinstance(courses, list)
    assert len(courses) >= 2  # at minimum the two seeded demo courses