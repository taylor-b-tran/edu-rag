"""A new lecturer has no access until an administrator approves the account.

A lecturer can do what a student cannot (upload and delete material, manage a
course), and anyone could register as one. Now a lecturer who signs up for
themselves gets 202 and no tokens, signing in is refused with 403 until an
administrator approves, and the administrator sees the waiting accounts and
decides. Students are unchanged; every account that existed before counts as
approved.

The suite runs with no database configured (see conftest), so `db` is stubbed
with an in-memory table here. That keeps these tests about the rules, which is
where the risk is: locking out an existing account, and revealing an account's
state to someone who does not hold its password. The real tables are covered by
test_lecturer_approval_postgres.py.
"""
from __future__ import annotations

import itertools
import uuid

import pytest

from src.api.app import create_app
from src.api import db as real_db

GOOD_PASSWORD = "Str0ngPassw0rd!"
ADMIN = {"user_id": str(uuid.uuid4()), "email": "admin@uow.edu.au", "role": "admin",
         "username": "admin_demo", "enrolled_courses": []}
STUDENT = {"user_id": str(uuid.uuid4()), "email": "student@uow.edu.au", "role": "student",
           "username": "student_demo", "enrolled_courses": []}
LECTURER = {"user_id": str(uuid.uuid4()), "email": "lecturer@uow.edu.au", "role": "lecturer",
            "username": "lecturer_demo", "enrolled_courses": []}


class FakeUsers:
    """Just enough of the users table: what create_user, the lookups and the
    approval writes do, including the default status."""

    def __init__(self):
        self.rows = {}
        self.created = itertools.count(1)
        self.create_calls = []
        for account in (ADMIN, STUDENT, LECTURER):
            self.rows[account["user_id"]] = {**account, "password": GOOD_PASSWORD,
                                             "approval_status": "approved", "order": next(self.created)}

    # Same parameters as db.create_user. The keyword arguments are recorded
    # exactly as passed, so a test can tell "not passed" from "passed approved".
    def create_user(self, username, email, role, password, **kw):
        approval_status = kw.get("approval_status", "approved")
        self.create_calls.append({"role": role, "kwargs": kw})
        if any(r["email"] == email or r["username"] == username for r in self.rows.values()):
            return None, "email"
        user_id = str(uuid.uuid4())
        self.rows[user_id] = {"user_id": user_id, "username": username, "email": email, "role": role,
                              "password": password, "approval_status": approval_status,
                              "enrolled_courses": [], "order": next(self.created)}
        return {k: self.rows[user_id][k] for k in
                ("user_id", "username", "email", "role", "approval_status", "enrolled_courses")}, None

    def get_by_id(self, user_id):
        row = self.rows.get(user_id)
        return None if row is None else {k: row[k] for k in
                                         ("user_id", "username", "email", "role", "approval_status")}

    def list_by_status(self, status):
        rows = [r for r in self.rows.values() if r["role"] == "lecturer" and r["approval_status"] == status]
        return [{k: r[k] for k in ("user_id", "username", "email", "role", "approval_status")}
                for r in sorted(rows, key=lambda r: r["order"])]

    def set_status(self, user_id, status):
        row = self.rows.get(user_id)
        if row is None:
            return None
        row["approval_status"] = status
        return self.get_by_id(user_id)

    def authenticate(self, email, password):
        for row in self.rows.values():
            if row["email"] == email and row["password"] == password:
                return {k: row[k] for k in ("user_id", "username", "email", "role",
                                            "approval_status", "enrolled_courses")}
        return None


@pytest.fixture
def api(monkeypatch):
    app = create_app()
    app.config.update(TESTING=True)
    state = app.config["EDURAG_API_STATE"]
    users = FakeUsers()
    current = {"user": None}

    monkeypatch.setattr(type(state), "db_available", property(lambda self: True))
    monkeypatch.setattr(type(state), "validate_bearer", lambda self, authorization: current["user"])
    monkeypatch.setattr(type(state), "authenticate_user", lambda self, email, pw: users.authenticate(email, pw))
    monkeypatch.setattr(type(state), "issue_tokens",
                        lambda self, user, family_id=None, refresh_token_to_rotate=None:
                        {"access_token": "t", "refresh_token": "r", "user": {"role": user["role"]}})
    monkeypatch.setattr(real_db, "create_user", users.create_user)
    monkeypatch.setattr(real_db, "get_user_by_id", users.get_by_id)
    monkeypatch.setattr(real_db, "list_users_by_approval_status", users.list_by_status)
    monkeypatch.setattr(real_db, "set_approval_status", users.set_status)

    client = app.test_client()
    client.users = users
    client.as_user = lambda user: current.__setitem__("user", user)
    return client


def _signup(client, role, email="new.person@uow.edu.au", username="new_person"):
    return client.post("/api/auth/signup", json={"email": email, "username": username,
                                                 "password": GOOD_PASSWORD, "role": role})


def _login(client, email="new.person@uow.edu.au", password=GOOD_PASSWORD):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def _id_of(client, email):
    return next(r["user_id"] for r in client.users.rows.values() if r["email"] == email)


# --- sign-up ---------------------------------------------------------------

def test_a_lecturer_who_signs_up_is_pending_and_gets_no_tokens(api):
    resp = _signup(api, "lecturer")
    assert resp.status_code == 202
    body = resp.get_json()
    assert body["status"] == "pending_approval"
    assert "administrator must approve" in body["message"]
    assert "access_token" not in body and "refresh_token" not in body
    assert api.users.create_calls[-1] == {"role": "lecturer", "kwargs": {"approval_status": "pending"}}


def test_a_student_who_signs_up_is_unchanged(api):
    resp = _signup(api, "student")
    assert resp.status_code == 201
    assert resp.get_json()["access_token"] == "t"
    # The student path must not pass the new keyword: existing callers and test
    # doubles of create_user know only the original four arguments.
    assert api.users.create_calls[-1] == {"role": "student", "kwargs": {}}


# --- sign-in ---------------------------------------------------------------

def test_a_pending_lecturer_cannot_sign_in(api):
    _signup(api, "lecturer")
    resp = _login(api)
    assert resp.status_code == 403
    assert resp.get_json()["error"] == "pending_approval"
    assert "access_token" not in resp.get_json()


def test_a_wrong_password_is_still_a_401_so_the_state_is_not_revealed(api):
    _signup(api, "lecturer")
    wrong = _login(api, password="not-the-password")
    unknown = _login(api, email="nobody@uow.edu.au")
    assert wrong.status_code == 401 and unknown.status_code == 401
    assert wrong.get_json() == unknown.get_json()


def test_existing_accounts_still_sign_in(api):
    for account in (ADMIN, STUDENT, LECTURER):
        assert _login(api, email=account["email"]).status_code == 200


# --- the administrator's decision -----------------------------------------

def test_the_pending_list_holds_only_pending_lecturers(api):
    _signup(api, "lecturer", "first@uow.edu.au", "first_l")
    _signup(api, "lecturer", "second@uow.edu.au", "second_l")
    _signup(api, "student", "stu2@uow.edu.au", "stu2")
    api.as_user(ADMIN)
    emails = [u["email"] for u in api.get("/api/admin/users/pending").get_json()["users"]]
    assert emails == ["first@uow.edu.au", "second@uow.edu.au"]


def test_approving_lets_the_lecturer_sign_in_with_the_lecturer_role(api):
    _signup(api, "lecturer")
    api.as_user(ADMIN)
    resp = api.post(f"/api/admin/users/{_id_of(api, 'new.person@uow.edu.au')}/approve")
    assert resp.status_code == 200 and resp.get_json()["user"]["approval_status"] == "approved"
    assert api.get("/api/admin/users/pending").get_json()["users"] == []
    login = _login(api)
    assert login.status_code == 200 and login.get_json()["user"]["role"] == "lecturer"


def test_rejecting_blocks_sign_in_and_a_later_approval_restores_it(api):
    _signup(api, "lecturer")
    user_id = _id_of(api, "new.person@uow.edu.au")
    api.as_user(ADMIN)
    assert api.post(f"/api/admin/users/{user_id}/reject").status_code == 200
    refused = _login(api)
    assert refused.status_code == 403 and refused.get_json()["error"] == "account_rejected"
    assert api.post(f"/api/admin/users/{user_id}/approve").status_code == 200
    assert _login(api).status_code == 200


def test_an_approved_lecturer_cannot_be_rejected(api):
    # Rejecting the row would not end a session the lecturer already holds.
    api.as_user(ADMIN)
    resp = api.post(f"/api/admin/users/{LECTURER['user_id']}/reject")
    assert resp.status_code == 409
    assert api.users.rows[LECTURER["user_id"]]["approval_status"] == "approved"


def test_rejecting_twice_is_harmless(api):
    _signup(api, "lecturer")
    user_id = _id_of(api, "new.person@uow.edu.au")
    api.as_user(ADMIN)
    assert api.post(f"/api/admin/users/{user_id}/reject").status_code == 200
    assert api.post(f"/api/admin/users/{user_id}/reject").status_code == 200
    assert api.users.rows[user_id]["approval_status"] == "rejected"


def test_repeating_a_decision_changes_nothing(api):
    _signup(api, "lecturer")
    user_id = _id_of(api, "new.person@uow.edu.au")
    api.as_user(ADMIN)
    assert api.post(f"/api/admin/users/{user_id}/approve").status_code == 200
    assert api.post(f"/api/admin/users/{user_id}/approve").status_code == 200
    assert api.users.rows[user_id]["approval_status"] == "approved"


@pytest.mark.parametrize("target", [STUDENT, ADMIN])
def test_only_lecturer_accounts_can_be_decided(api, target):
    api.as_user(ADMIN)
    assert api.post(f"/api/admin/users/{target['user_id']}/approve").status_code == 409
    assert api.post(f"/api/admin/users/{target['user_id']}/reject").status_code == 409
    assert api.users.rows[target["user_id"]]["approval_status"] == "approved"


@pytest.mark.parametrize("user_id", [str(uuid.uuid4()), "not-a-uuid", "1"])
def test_an_unknown_or_malformed_id_is_a_404(api, user_id):
    api.as_user(ADMIN)
    assert api.post(f"/api/admin/users/{user_id}/approve").status_code == 404
    assert api.post(f"/api/admin/users/{user_id}/reject").status_code == 404


# --- who may ask -----------------------------------------------------------

ROUTES = [("get", "/api/admin/users/pending"),
          ("post", f"/api/admin/users/{uuid.uuid4()}/approve"),
          ("post", f"/api/admin/users/{uuid.uuid4()}/reject")]


@pytest.mark.parametrize("method,path", ROUTES)
def test_anonymous_callers_get_401(api, method, path):
    api.as_user(None)
    assert getattr(api, method)(path).status_code == 401


@pytest.mark.parametrize("method,path", ROUTES)
@pytest.mark.parametrize("who", [STUDENT, LECTURER])
def test_students_and_lecturers_get_403(api, method, path, who):
    api.as_user(who)
    assert getattr(api, method)(path).status_code == 403


def test_without_the_database_the_admin_routes_say_so(api, monkeypatch):
    monkeypatch.setattr(type(api.application.config["EDURAG_API_STATE"]), "db_available",
                        property(lambda self: False))
    api.as_user(ADMIN)
    assert api.get("/api/admin/users/pending").status_code == 503
    api.as_user(STUDENT)  # the role is settled before the database is consulted
    assert api.get("/api/admin/users/pending").status_code == 403


# --- the state layer -------------------------------------------------------

class _Record(dict):
    pass


@pytest.fixture
def state(monkeypatch):
    app = create_app()
    st = app.config["EDURAG_API_STATE"]
    import bcrypt
    password_hash = bcrypt.hashpw(GOOD_PASSWORD.encode(), bcrypt.gensalt()).decode()
    touched = []
    st._touched = touched
    st._hash = password_hash
    monkeypatch.setattr(real_db, "touch_last_login", lambda user_id: touched.append(user_id))
    monkeypatch.setattr(real_db, "get_enrolled_course_codes", lambda user_id: [])
    return st


def _record(state, **extra):
    return {"user_id": "u1", "username": "u", "email": "u@uow.edu.au", "role": "lecturer",
            "password_hash": state._hash, **extra}


@pytest.mark.parametrize("status", ["pending", "rejected"])
def test_a_not_approved_account_is_returned_with_its_status_and_leaves_no_last_login(state, monkeypatch, status):
    monkeypatch.setattr(real_db, "get_user_by_email", lambda email: _record(state, approval_status=status))
    user = state._authenticate_via_postgres("u@uow.edu.au", GOOD_PASSWORD)
    assert user["approval_status"] == status
    assert state._touched == []


def test_an_approved_account_records_its_last_login(state, monkeypatch):
    monkeypatch.setattr(real_db, "get_user_by_email", lambda email: _record(state, approval_status="approved"))
    user = state._authenticate_via_postgres("u@uow.edu.au", GOOD_PASSWORD)
    assert user["approval_status"] == "approved" and state._touched == ["u1"]


def test_a_record_without_the_column_counts_as_approved(state, monkeypatch):
    # An older row or test double that has never heard of approval_status.
    monkeypatch.setattr(real_db, "get_user_by_email", lambda email: _record(state))
    user = state._authenticate_via_postgres("u@uow.edu.au", GOOD_PASSWORD)
    assert user["approval_status"] == "approved" and state._touched == ["u1"]


def test_the_wrong_password_returns_nothing_whatever_the_status(state, monkeypatch):
    monkeypatch.setattr(real_db, "get_user_by_email", lambda email: _record(state, approval_status="pending"))
    assert state._authenticate_via_postgres("u@uow.edu.au", "wrong") is None


@pytest.mark.parametrize("status,allowed", [("approved", True), ("pending", False), ("rejected", False)])
def test_only_an_approved_account_can_renew_a_login(state, monkeypatch, status, allowed):
    monkeypatch.setattr(type(state), "db_available", property(lambda self: True))
    monkeypatch.setattr(state, "_db_available", True)
    monkeypatch.setattr(real_db, "get_user_by_email", lambda email: _record(state, approval_status=status))
    assert (state.find_user_any_source("u@uow.edu.au") is not None) is allowed
