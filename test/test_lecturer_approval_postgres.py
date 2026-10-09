"""Lecturer approval against real tables, in a disposable schema.

Opt-in: run with PAEDIA_TEST_POSTGRES_HOST set. CI does; inside the API
container use PAEDIA_TEST_POSTGRES_HOST=postgres. Covers what the stubbed tests
in test_lecturer_approval.py cannot: the new column and its default on a real
users table (so no existing account is locked out), running the schema twice,
and the whole flow through the API: sign up, refused sign-in, an
administrator's decision, sign-in.
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

PASSWORD = "Str0ngPassw0rd!"
ADMIN_HEADERS = {"Authorization": "Bearer qa-admin-access"}


@pytest.fixture
def pg(monkeypatch):
    schema = "qa_approval_" + uuid.uuid4().hex
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


def _status(pg, email):
    with pg() as conn:
        row = conn.execute("SELECT approval_status FROM users WHERE email = %s", (email,)).fetchone()
    return row["approval_status"] if row else None


@pytest.fixture
def client(pg):
    """The schema and demo accounts a first start leaves behind, an admin token,
    and a worker over them."""
    db.init_schema()
    payload = {"user_id": str(uuid.uuid4()), "email": "qa-admin@example.invalid", "role": "admin",
               "enrolled_courses": [], "family_id": "fam-qa-admin"}
    db.insert_token_pair("qa-admin-access", "qa-admin-refresh", payload, 3600, 86400)
    app = create_app()
    app.config.update(TESTING=True)
    assert app.config["EDURAG_API_STATE"].db_available, "the worker should have reached the test schema"
    return app.test_client()


def _signup(client, role, email="qa-new@example.invalid", username="qa_new"):
    return client.post("/api/auth/signup", json={"email": email, "username": username,
                                                 "password": PASSWORD, "role": role})


def _login(client, email="qa-new@example.invalid", password=PASSWORD):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def _pending_ids(client):
    return [u["user_id"] for u in client.get("/api/admin/users/pending", headers=ADMIN_HEADERS).get_json()["users"]]


# --- the column --------------------------------------------------------------

def test_the_seeded_demo_accounts_are_approved(pg, client):
    for email in ("admin@uow.edu.au", "lecturer@uow.edu.au", "student@uow.edu.au"):
        assert _status(pg, email) == "approved"


def test_accounts_that_predate_the_column_become_approved(pg):
    db.init_schema()
    with pg() as conn:
        conn.execute("ALTER TABLE users DROP COLUMN approval_status")
        conn.execute("INSERT INTO users (username, email, role, password_hash) "
                     "VALUES ('legacy_lecturer', 'legacy@example.invalid', 'lecturer', %s)", ("x" * 60,))
    db.init_schema()   # what the next start does to a database that already has users
    assert _status(pg, "legacy@example.invalid") == "approved"


def test_running_the_schema_again_does_not_reset_a_decision(pg):
    db.init_schema()
    user, _ = db.create_user("qa_wait", "wait@example.invalid", "lecturer", PASSWORD, approval_status="pending")
    assert user["approval_status"] == "pending"
    db.init_schema()
    assert _status(pg, "wait@example.invalid") == "pending"


def test_the_column_refuses_a_value_outside_the_three_states(pg):
    db.init_schema()
    with pytest.raises(psycopg.errors.CheckViolation):
        with pg() as conn:
            conn.execute("INSERT INTO users (username, email, role, password_hash, approval_status) "
                         "VALUES ('bad', 'bad@example.invalid', 'lecturer', %s, 'maybe')", ("x" * 60,))


# --- the whole flow ------------------------------------------------------------

def test_sign_up_refused_sign_in_approval_then_sign_in(pg, client):
    resp = _signup(client, "lecturer")
    assert resp.status_code == 202 and "access_token" not in resp.get_json()
    assert _status(pg, "qa-new@example.invalid") == "pending"

    refused = _login(client)
    assert refused.status_code == 403 and refused.get_json()["error"] == "pending_approval"
    assert _login(client, password="wrong-password").status_code == 401
    with pg() as conn:   # a refused sign-in leaves no last-login time
        assert conn.execute("SELECT last_login_at FROM users WHERE email = 'qa-new@example.invalid'"
                            ).fetchone()["last_login_at"] is None

    user_id = db.get_user_by_email("qa-new@example.invalid")["user_id"]
    assert _pending_ids(client) == [user_id]
    approve = client.post(f"/api/admin/users/{user_id}/approve", headers=ADMIN_HEADERS)
    assert approve.status_code == 200
    assert _pending_ids(client) == []

    login = _login(client)
    assert login.status_code == 200 and login.get_json()["user"]["role"] == "lecturer"


def test_rejecting_a_waiting_account_blocks_sign_in(pg, client):
    _signup(client, "lecturer")
    user_id = db.get_user_by_email("qa-new@example.invalid")["user_id"]
    assert client.post(f"/api/admin/users/{user_id}/reject", headers=ADMIN_HEADERS).status_code == 200
    refused = _login(client)
    assert refused.status_code == 403 and refused.get_json()["error"] == "account_rejected"
    assert _status(pg, "qa-new@example.invalid") == "rejected"


def test_an_approved_account_cannot_be_rejected(pg, client):
    # A live session would survive the row change, so the API refuses instead.
    _signup(client, "lecturer")
    user_id = db.get_user_by_email("qa-new@example.invalid")["user_id"]
    assert client.post(f"/api/admin/users/{user_id}/approve", headers=ADMIN_HEADERS).status_code == 200
    tokens = _login(client).get_json()

    assert client.post(f"/api/admin/users/{user_id}/reject", headers=ADMIN_HEADERS).status_code == 409
    assert _status(pg, "qa-new@example.invalid") == "approved"
    renewed = client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert renewed.status_code == 200


def test_a_student_signs_up_and_in_as_before(pg, client):
    resp = _signup(client, "student", "qa-student@example.invalid", "qa_student")
    assert resp.status_code == 201 and resp.get_json()["access_token"]
    assert _status(pg, "qa-student@example.invalid") == "approved"
    assert _login(client, "qa-student@example.invalid").status_code == 200


def test_the_seeded_lecturer_and_student_still_sign_in(pg, client):
    # The demo passwords are random per run here; set known ones through the table.
    for email, role in (("lecturer@uow.edu.au", "lecturer"), ("student@uow.edu.au", "student")):
        import bcrypt
        digest = bcrypt.hashpw(PASSWORD.encode(), bcrypt.gensalt()).decode()
        with pg() as conn:
            conn.execute("UPDATE users SET password_hash = %s WHERE email = %s", (digest, email))
        resp = _login(client, email)
        assert resp.status_code == 200 and resp.get_json()["user"]["role"] == role
