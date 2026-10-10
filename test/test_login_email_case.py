"""Signing in works with the address typed in any letter case.

Sign-up lower-cases the address before it is stored, but sign-in looked it up
exactly as typed, so "Student@uow.edu.au" was refused with "invalid
credentials" even with the right password. Phone and tablet keyboards
capitalise the first letter on their own, which made this easy to hit.
"""
from __future__ import annotations

import pytest

from src.api.app import create_app
from src.api.routes import auth

USER = {"user_id": "u1", "email": "student@uow.edu.au", "role": "student",
        "username": "student_demo", "enrolled_courses": []}


class _State:
    """The part of APIState that sign-in touches, recording what it was asked."""

    def __init__(self):
        self.looked_up = []

    def authenticate_user(self, email, password):
        self.looked_up.append(email)
        # What the SQL does: an exact match against the stored, lower-case address.
        return dict(USER) if email == "student@uow.edu.au" and password == "pw" else None

    def issue_tokens(self, user):
        return {"access_token": "t", "refresh_token": "r", "user": user}


@pytest.fixture
def client(monkeypatch):
    state = _State()
    monkeypatch.setattr(auth, "_state", lambda: state)
    return create_app().test_client(), state


@pytest.mark.parametrize("typed", [
    "Student@uow.edu.au",
    "STUDENT@UOW.EDU.AU",
    "  student@uow.edu.au  ",
    "  Student@Uow.Edu.Au ",
])
def test_login_finds_the_account_whatever_the_letter_case(client, typed):
    http, state = client
    response = http.post("/api/auth/login", json={"email": typed, "password": "pw"})
    assert response.status_code == 200
    assert state.looked_up == ["student@uow.edu.au"]


def test_a_wrong_password_is_still_refused(client):
    http, _ = client
    response = http.post("/api/auth/login", json={"email": "Student@uow.edu.au", "password": "nope"})
    assert response.status_code == 401


def test_an_unknown_address_is_still_refused(client):
    http, _ = client
    response = http.post("/api/auth/login", json={"email": "Nobody@uow.edu.au", "password": "pw"})
    assert response.status_code == 401
