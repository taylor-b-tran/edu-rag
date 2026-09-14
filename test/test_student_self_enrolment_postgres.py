"""Joining and leaving against real tables, in a disposable schema (T8-05).

Opt-in: run with PAEDIA_TEST_POSTGRES_HOST set. CI does; inside the API
container use PAEDIA_TEST_POSTGRES_HOST=postgres. Covers what the stubbed tests
cannot: the membership row really lands, the new list reaches the stored tokens
a second worker reads, and starting a worker leaves memberships alone.
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

STUDENT_EMAIL = "qa-student@example.invalid"
HEADERS = {"Authorization": "Bearer qa-access"}


@pytest.fixture
def pg(monkeypatch):
    schema = "qa_enrol_" + uuid.uuid4().hex
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
        # Exact randomly named test schema only; no production relations.
        with psycopg.connect(**config) as conn:
            conn.execute(psycopg.sql.SQL("DROP SCHEMA {} CASCADE").format(psycopg.sql.Identifier(schema)))


@pytest.fixture
def student(pg):
    """The schema and demo data a first start leaves behind, then a student and
    two courses that are not demo data."""
    db.init_schema()
    with pg() as conn:
        user_id = conn.execute(
            "INSERT INTO users (username, email, role, password_hash) "
            "VALUES (%s, %s, 'student', %s) RETURNING id",
            ("qa_student", STUDENT_EMAIL, "x" * 60)).fetchone()["id"]
        for code, active in (("OPEN101", True), ("SHUT101", False)):
            conn.execute("INSERT INTO courses (course_code, course_name, is_active) "
                         "VALUES (%s, %s, %s)", (code, code.title(), active))
    payload = {"user_id": str(user_id), "email": STUDENT_EMAIL, "role": "student",
               "enrolled_courses": [], "family_id": "fam-qa"}
    db.insert_token_pair("qa-access", "qa-refresh", payload, 3600, 86400)
    return payload


def start_worker():
    app = create_app()
    app.config.update(TESTING=True)
    assert app.config["EDURAG_API_STATE"].db_available, "the worker should have reached the test schema"
    return app.test_client()


@pytest.fixture
def workers(student):
    """Two API processes over the same tables, as gunicorn runs them. Both start
    after the student exists, so each start-up's demo seeding runs over them."""
    return [start_worker(), start_worker()]


def _courses_of(pg, email):
    with pg() as conn:
        rows = conn.execute(
            "SELECT c.course_code, cm.membership_role FROM course_memberships cm "
            "JOIN users u ON u.id = cm.user_id JOIN courses c ON c.id = cm.course_id "
            "WHERE u.email = %s ORDER BY c.course_code", (email,)).fetchall()
    return [(row["course_code"], row["membership_role"]) for row in rows]


# --- starting a worker leaves memberships alone ---------------------------

def test_starting_a_worker_enrols_nobody_in_anything(pg, workers):
    assert _courses_of(pg, STUDENT_EMAIL) == []
    with pg() as conn:
        members = conn.execute(
            "SELECT count(*) AS n FROM course_memberships cm "
            "JOIN courses c ON c.id = cm.course_id "
            "WHERE c.course_code IN ('OPEN101', 'SHUT101')").fetchone()["n"]
    assert members == 0


def test_the_demo_accounts_keep_their_demo_courses(pg, workers):
    for email, role in (("student@uow.edu.au", "student"), ("lecturer@uow.edu.au", "lecturer")):
        assert _courses_of(pg, email) == [("CSCI203", role), ("CSIT321", role)]


def test_a_student_who_left_is_not_put_back_by_a_restart(pg, workers):
    first, _ = workers
    assert first.post("/api/courses/CSIT321/join", headers=HEADERS).status_code == 201
    assert first.post("/api/courses/CSIT321/leave", headers=HEADERS).status_code == 200

    start_worker()

    assert _courses_of(pg, STUDENT_EMAIL) == []


# --- joining and leaving across workers -----------------------------------

def test_joining_on_one_worker_opens_the_course_on_the_other(pg, workers):
    first, second = workers
    assert second.get("/api/documents?course_id=OPEN101", headers=HEADERS).status_code == 403

    resp = first.post("/api/courses/OPEN101/join", headers=HEADERS)

    assert resp.status_code == 201
    assert resp.get_json()["enrolled_courses"] == ["OPEN101"]
    assert _courses_of(pg, STUDENT_EMAIL) == [("OPEN101", "student")]
    assert db.get_token("access_tokens", "qa-access")["enrolled_courses"] == ["OPEN101"]
    assert db.get_token("refresh_tokens", "qa-refresh")["enrolled_courses"] == ["OPEN101"]
    assert second.get("/api/documents?course_id=OPEN101", headers=HEADERS).status_code == 200


def test_an_inactive_course_is_refused_and_nothing_is_written(pg, workers):
    first, _ = workers

    assert first.post("/api/courses/SHUT101/join", headers=HEADERS).status_code == 409
    assert _courses_of(pg, STUDENT_EMAIL) == []


def test_leaving_on_one_worker_closes_the_course_on_the_other(pg, workers):
    first, second = workers
    first.post("/api/courses/OPEN101/join", headers=HEADERS)

    resp = second.post("/api/courses/OPEN101/leave", headers=HEADERS)

    assert resp.status_code == 200
    assert resp.get_json()["status"] == "unenrolled"
    assert _courses_of(pg, STUDENT_EMAIL) == []
    assert db.get_token("access_tokens", "qa-access")["enrolled_courses"] == []
    assert first.get("/api/documents?course_id=OPEN101", headers=HEADERS).status_code == 403
