"""Tests for the self-signup endpoint (T8-02).

The role arrives in the request body, so the thing that matters most here is
that "admin" can never be honoured. The rest is ordinary input validation, plus
a clean 409 rather than a 500 when an email or username is taken.

Validation happens before the database is consulted, which is deliberate: a bad
request should not depend on the backend being up. Where a test needs the
no-database path it forces it, rather than assuming Postgres is absent — run
inside the api container the suite reaches the live database, which made an
earlier version of these tests pass or fail depending on where it ran.
"""
from __future__ import annotations

import pytest

from src.api.app import create_app
from src.api.routes import auth as auth_routes


GOOD_PASSWORD = "Str0ngPassw0rd!"


@pytest.fixture
def client():
    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client()


def _signup(client, **overrides):
    body = {
        "email": "someone@uow.edu.au",
        "username": "someone",
        "password": GOOD_PASSWORD,
        "role": "student",
    }
    body.update(overrides)
    return client.post("/api/auth/signup", json=body)


# ─── the one that matters ─────────────────────────────────────────────

@pytest.mark.parametrize("role", ["admin", "ADMIN", "Admin", "superuser", "root"])
def test_cannot_sign_up_as_admin_or_anything_unlisted(client, role):
    resp = _signup(client, role=role)
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "invalid role"


@pytest.fixture
def no_database(monkeypatch, client):
    """Force the no-database path so these assertions do not depend on whether
    Postgres happens to be reachable from wherever the suite is run."""
    monkeypatch.setattr(type(client.application.config["EDURAG_API_STATE"]),
                        "db_available", property(lambda self: False))
    return client


@pytest.mark.parametrize("role", ["student", "lecturer"])
def test_the_two_allowed_roles_pass_validation(no_database, role):
    """503 means it got past every check and only the database was missing."""
    assert _signup(no_database, role=role).status_code == 503


def test_role_defaults_to_student_when_absent(no_database):
    """Omitting the role is ordinary, not an attempt to escalate."""
    resp = no_database.post("/api/auth/signup", json={
        "email": "norole@uow.edu.au", "username": "norole", "password": GOOD_PASSWORD,
    })
    assert resp.status_code == 503, "reached the database step, so the role was accepted"


# ─── password rules ───────────────────────────────────────────────────

def test_short_password_is_rejected(client):
    resp = _signup(client, password="Sh0rt!")
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "weak password"


def test_password_longer_than_bcrypt_can_hash_is_rejected(client):
    """bcrypt ignores anything past 72 bytes, so accepting a longer password
    would silently truncate it at login."""
    resp = _signup(client, password="A1!" + "x" * 80)
    assert resp.status_code == 400
    assert "72" in resp.get_json()["message"]


def test_common_password_is_rejected(client):
    assert _signup(client, password="password123").status_code == 400


def test_password_equal_to_the_email_is_rejected(client):
    resp = _signup(client, email="reuse@uow.edu.au", password="reuse@uow.edu.au")
    assert resp.status_code == 400


def test_password_equal_to_the_username_is_rejected(client):
    resp = _signup(client, username="justmyname", password="justmyname")
    assert resp.status_code == 400


# ─── ordinary input validation ────────────────────────────────────────

@pytest.mark.parametrize("email", ["", "not-an-email", "   "])
def test_email_must_look_like_an_email(client, email):
    assert _signup(client, email=email).status_code == 400


def test_username_is_required(client):
    assert _signup(client, username="  ").status_code == 400


def test_username_longer_than_the_column_is_rejected(client):
    assert _signup(client, username="u" * 51).status_code == 400


def test_email_is_normalised_to_lowercase(monkeypatch, client):
    """Otherwise Alice@x and alice@x are two accounts that both look like one."""
    seen = {}

    def fake_create_user(username, email, role, password):
        seen["email"] = email
        return {"user_id": "u1", "email": email, "username": username,
                "role": role, "enrolled_courses": []}, None

    from src.api import db
    monkeypatch.setattr(db, "create_user", fake_create_user)
    monkeypatch.setattr(type(client.application.config["EDURAG_API_STATE"]),
                        "db_available", property(lambda self: True))

    resp = _signup(client, email="MixedCase@UOW.edu.au")

    assert resp.status_code == 201
    assert seen["email"] == "mixedcase@uow.edu.au"


def test_duplicate_registration_is_a_409_not_a_500(monkeypatch, client):
    from src.api import db
    monkeypatch.setattr(db, "create_user", lambda **kw: (None, "email"))
    monkeypatch.setattr(type(client.application.config["EDURAG_API_STATE"]),
                        "db_available", property(lambda self: True))

    resp = _signup(client)

    assert resp.status_code == 409
    assert resp.get_json()["error"] == "already_registered"
    assert "email" in resp.get_json()["message"]


def test_allowed_roles_do_not_include_admin():
    """Guards the constant itself, so widening it is a deliberate act."""
    assert auth_routes._SELF_SIGNUP_ROLES == {"student", "lecturer"}
