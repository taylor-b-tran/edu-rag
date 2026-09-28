"""Sprint 10, Task 12 — permission matrix across endpoints (Tung).

Rewritten after Taylor's 27 Sept review of PR #134. The first version signed
up real users through /api/auth/signup and logged in through /api/auth/login
against whatever Postgres CI happened to be running, which carried five bugs
of its own:

  - it logged the admin in with the hardcoded "admin123", but the demo
    password has come from PAEDIA_DEMO_ADMIN_PASSWORD since #127
  - it read user["user_id"] from the signup response; the API returns
    user["id"]
  - it used a fixed username per persona ("t12own", "t12oth", ...), which
    collided on a second run against a persistent database
  - it assumed CSIT321/"T12-OUTSIDE" were safe course codes to create
  - its one identifier-form check hit /api/courses/<code>/members (which has
    never accepted anything but a course code) and accepted either 200 or
    404, so it could not actually catch a regression on the real T6/T7
    surface, /api/documents

This version drops the real signup/login path entirely and follows the
isolated-schema convention already used by test_student_self_enrolment_postgres.py
and test_token_transactions_postgres.py: a fresh, randomly-named Postgres
schema per test, `db.connect` monkeypatched onto it, `db.init_schema()` run
fresh, and every persona's user/course/membership/token row inserted directly
by SQL — no password, no signup race, no dependency on what else lives in
the target database. Route behaviour itself is still only ever exercised
through the real Flask routes; only the *setup* bypasses the API.

Opt-in: skipped unless PAEDIA_TEST_POSTGRES_HOST is set (conftest.py forces
every other test into no-database mode on purpose — see its header comment).
CI runs this in the same step as the other three Postgres-opt-in files (see
.github/workflows/ci.yml, "Verify token transactions, course joining and demo
account seeding..."); this file's name has been added to that step's pytest
invocation. Locally:

    docker compose up -d postgres
    $env:PAEDIA_TEST_POSTGRES_HOST = "localhost"
    $env:POSTGRES_PASSWORD = "edurag_dev_password"
    python -m pytest test/test_sprint10_t12_permission_matrix.py -v
"""
from __future__ import annotations

import os
import uuid
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row
import pytest

from src.api import db
from src.api.app import create_app

pytestmark = pytest.mark.skipif(not os.getenv("PAEDIA_TEST_POSTGRES_HOST"),
                                reason="Opt-in isolated PostgreSQL tests")

PERSONA_ORDER = ["none", "student_in", "student_out", "lecturer_owner", "lecturer_other", "admin"]


# ─── Isolated schema, same pattern as test_student_self_enrolment_postgres.py ──

@pytest.fixture
def pg(monkeypatch):
    schema = "qa_t12_" + uuid.uuid4().hex
    config = dict(host=os.environ["PAEDIA_TEST_POSTGRES_HOST"],
                  port=os.getenv("POSTGRES_PORT", "5432"),
                  dbname=os.getenv("POSTGRES_DB", "edurag"),
                  user=os.getenv("POSTGRES_USER", "edurag"),
                  password=os.environ["POSTGRES_PASSWORD"],
                  autocommit=True, row_factory=dict_row)
    with psycopg.connect(**config) as conn:
        conn.execute(psycopg.sql.SQL("CREATE SCHEMA {}").format(psycopg.sql.Identifier(schema)))

    @contextmanager
    def isolated():
        with psycopg.connect(**config, options=f"-c search_path={schema}") as conn:
            yield conn

    monkeypatch.setattr(db, "connect", isolated)
    monkeypatch.setenv("EDURAG_OLLAMA_WARMUP", "false")
    try:
        yield isolated
    finally:
        with psycopg.connect(**config) as conn:
            conn.execute(psycopg.sql.SQL("DROP SCHEMA {} CASCADE").format(psycopg.sql.Identifier(schema)))


def _client():
    app = create_app()
    app.config.update(TESTING=True)
    assert app.config["EDURAG_API_STATE"].db_available, "worker should have reached the test schema"
    return app.test_client()


def _auth(token):
    return {"Authorization": f"Bearer {token}"} if token else {}


@pytest.fixture
def world(pg):
    """Two courses, six personas, one document -- all inserted directly so
    no persona depends on a password, a signup race, or data already living
    on whatever Postgres runs this."""
    db.init_schema()

    with pg() as conn:
        def make_user(tag: str, role: str) -> str:
            return conn.execute(
                "INSERT INTO users (username, email, role, password_hash) "
                "VALUES (%s, %s, %s, %s) RETURNING id",
                (f"t12_{tag}", f"t12-{tag}@uow.edu.au", role, "x" * 60),
            ).fetchone()["id"]

        admin_id = make_user("admin", "admin")
        owner_id = make_user("lect_owner", "lecturer")
        other_lect_id = make_user("lect_other", "lecturer")
        student_in_id = make_user("stu_in", "student")
        student_out_id = make_user("stu_out", "student")

        def make_course(code: str, owner: str | None) -> str:
            return conn.execute(
                "INSERT INTO courses (course_code, course_name, owner_id) "
                "VALUES (%s, %s, %s) RETURNING id",
                (code, f"Course {code}", owner),
            ).fetchone()["id"]

        target_id = make_course("T12TGT", owner_id)
        other_id = make_course("T12OTH", other_lect_id)

        def membership(user_id: str, course_id: str, role: str) -> None:
            conn.execute(
                "INSERT INTO course_memberships (user_id, course_id, membership_role) "
                "VALUES (%s, %s, %s)",
                (user_id, course_id, role),
            )

        membership(owner_id, target_id, "lecturer")
        membership(other_lect_id, other_id, "lecturer")
        membership(student_in_id, target_id, "student")
        membership(student_out_id, other_id, "student")

        doc_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO uploaded_documents "
            "(document_id, course_id, course_code, filename, original_filename, "
            " file_type, status, indexing_status) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (doc_id, "T12TGT", "T12TGT", "t12-fixture.pdf", "t12-fixture.pdf",
             "pdf", "indexed", "completed"),
        )

    def issue(user_id: str, email: str, role: str, enrolled_courses: list[str]) -> str:
        token = f"t12-{uuid.uuid4().hex}"
        payload = {"user_id": str(user_id), "email": email, "role": role,
                   "enrolled_courses": enrolled_courses, "family_id": f"fam-{token}"}
        db.insert_token_pair(token, f"{token}-r", payload, 3600, 86400)
        return token

    tokens = {
        "none": None,
        "admin": issue(admin_id, "t12-admin@uow.edu.au", "admin", []),
        "lecturer_owner": issue(owner_id, "t12-lect_owner@uow.edu.au", "lecturer", ["T12TGT"]),
        "lecturer_other": issue(other_lect_id, "t12-lect_other@uow.edu.au", "lecturer", ["T12OTH"]),
        "student_in": issue(student_in_id, "t12-stu_in@uow.edu.au", "student", ["T12TGT"]),
        "student_out": issue(student_out_id, "t12-stu_out@uow.edu.au", "student", ["T12OTH"]),
    }

    client = _client()
    return {
        "client": client, "tokens": tokens, "target_course": "T12TGT",
        "other_course": "T12OTH", "target_course_uuid": str(target_id),
        "document_id": doc_id,
    }


def _get(world, url, persona):
    return world["client"].get(url, headers=_auth(world["tokens"][persona]))


def _patch(world, url, persona, body):
    return world["client"].patch(url, json=body, headers=_auth(world["tokens"][persona]))


# ─── Endpoint cases ──────────────────────────────────────────────────────

class TestCourseSettings:
    """PATCH /api/courses/<code>/settings — reuses _require_course_manager."""

    EXPECT = {"none": 401, "student_in": 403, "student_out": 403,
              "lecturer_owner": 200, "lecturer_other": 403, "admin": 200}

    @pytest.mark.parametrize("persona", PERSONA_ORDER)
    def test_only_the_owner_or_admin_can_write(self, world, persona):
        resp = _patch(world, f"/api/courses/{world['target_course']}/settings",
                      persona, {"top_k": 6})
        assert resp.status_code == self.EXPECT[persona], (persona, resp.get_json())
        if resp.status_code == 200:
            body = resp.get_json()
            assert body.get("scope") == world["target_course"]


class TestCourseMembers:
    """GET /api/courses/<code>/members — must not leak the roster to non-managers."""

    EXPECT = {"none": 401, "student_in": 403, "student_out": 403,
              "lecturer_owner": 200, "lecturer_other": 403, "admin": 200}

    @pytest.mark.parametrize("persona", PERSONA_ORDER)
    def test_roster_visible_only_to_manager(self, world, persona):
        resp = _get(world, f"/api/courses/{world['target_course']}/members", persona)
        assert resp.status_code == self.EXPECT[persona], (persona, resp.get_json())
        if resp.status_code == 403:
            assert "members" not in (resp.get_json() or {})


class TestDocumentList:
    """GET /api/documents with no course_id — T7's own regression surface."""

    @pytest.mark.parametrize("persona", ["student_in", "student_out", "lecturer_owner", "admin"])
    def test_unqualified_list_never_shows_a_foreign_course(self, world, persona):
        resp = _get(world, "/api/documents", persona)
        assert resp.status_code == 200, (persona, resp.get_json())
        docs = resp.get_json()["documents"]
        for d in docs:
            assert "storage_path" not in d and "uploaded_by" not in d, d
        course_ids = {d.get("course_id") or d.get("course_code") for d in docs}
        if persona == "student_out":
            assert world["target_course"] not in course_ids, \
                "T7 regression: outsider saw the target course"
        if persona in ("student_in", "lecturer_owner"):
            assert world["target_course"] in course_ids, f"{persona} should see their own course"

    def test_none_is_401_not_an_empty_200(self, world):
        resp = _get(world, "/api/documents", "none")
        assert resp.status_code == 401


class TestDocumentMetadata:
    """GET /api/document/<id> — must 404 (not 403) for an outsider."""

    EXPECT = {"none": 401, "student_in": 200, "student_out": 404,
              "lecturer_owner": 200, "lecturer_other": 404, "admin": 200}

    @pytest.mark.parametrize("persona", PERSONA_ORDER)
    def test_document_scoped_to_course_membership(self, world, persona):
        resp = _get(world, f"/api/document/{world['document_id']}", persona)
        assert resp.status_code == self.EXPECT[persona], (persona, resp.get_json())
        if resp.status_code == 200:
            body = resp.get_json()
            assert (body.get("course_id") or body.get("course_code")) is not None


class TestAdminOnlyRoutes:
    """GET /api/admin/stats — every non-admin persona, not just "a student"."""

    @pytest.mark.parametrize("persona", ["none", "student_in", "lecturer_owner", "lecturer_other"])
    def test_non_admin_refused(self, world, persona):
        resp = _get(world, "/api/admin/stats", persona)
        assert resp.status_code == (401 if persona == "none" else 403), (persona, resp.get_json())

    def test_admin_allowed(self, world):
        assert _get(world, "/api/admin/stats", "admin").status_code == 200


class TestCourseIdentifierForms:
    """T6/T7 regression (flagged by Taylor as S-3): the actual surface is
    /api/documents, which resolves a caller-supplied course_id through both
    forms — /api/courses/<code>/members never has, and asserting (200, 404)
    there let a real regression through undetected. This checks a strict,
    single expected status on /api/documents for both an allowed and a
    refused caller, in both identifier forms."""

    def test_enrolled_student_reaches_documents_by_code_and_uuid_identically(self, world):
        by_code = _get(world, f"/api/documents?course_id={world['target_course']}", "student_in")
        by_uuid = _get(world, f"/api/documents?course_id={world['target_course_uuid']}", "student_in")
        assert by_code.status_code == 200, by_code.get_json()
        assert by_uuid.status_code == 200, by_uuid.get_json()
        assert ({d["document_id"] for d in by_code.get_json()["documents"]}
                == {d["document_id"] for d in by_uuid.get_json()["documents"]})

    def test_unenrolled_student_refused_identically_by_both_forms(self, world):
        by_code = _get(world, f"/api/documents?course_id={world['target_course']}", "student_out")
        by_uuid = _get(world, f"/api/documents?course_id={world['target_course_uuid']}", "student_out")
        assert by_code.status_code == 403, by_code.get_json()
        assert by_uuid.status_code == 403, by_uuid.get_json()