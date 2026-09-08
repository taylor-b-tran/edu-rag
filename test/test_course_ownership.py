"""Course ownership and lecturer self-serve course management (T8-04).

Course CRUD used to be admin-only, so a lecturer could not create a course at
all. This adds `courses.owner_id` and authorizes writes against it.

Two things these tests pin down that are easy to regress:

  * the owner is taken from the token, never from the request body, so a
    lecturer cannot create a course belonging to someone else;
  * a course with a NULL owner (everything that predates this change) stays
    admin-only rather than becoming every lecturer's.

The suite runs with no database configured (see conftest), so `db` is stubbed
here. That keeps these tests about authorization, which is where the risk is.
"""
from __future__ import annotations

import pytest

from src.api.app import create_app


LECTURER = {"user_id": "lect-1", "email": "lecturer@uow.edu.au", "role": "lecturer",
            "username": "lecturer_demo", "enrolled_courses": []}
OTHER_LECTURER = {"user_id": "lect-2", "email": "other@uow.edu.au", "role": "lecturer",
                  "username": "other_demo", "enrolled_courses": []}
STUDENT = {"user_id": "stu-1", "email": "student@uow.edu.au", "role": "student",
           "username": "student_demo", "enrolled_courses": []}
ADMIN = {"user_id": "adm-1", "email": "admin@uow.edu.au", "role": "admin",
         "username": "admin_demo", "enrolled_courses": []}

OWNED = {"course_code": "OWNED101", "course_name": "Owned", "owner_id": LECTURER["user_id"]}
FOREIGN = {"course_code": "FOREIGN101", "course_name": "Theirs",
           "owner_id": OTHER_LECTURER["user_id"]}
LEGACY = {"course_code": "LEGACY101", "course_name": "No owner", "owner_id": None}

_COURSES = {c["course_code"]: c for c in (OWNED, FOREIGN, LEGACY)}
_USERS = {u["email"]: u for u in (LECTURER, OTHER_LECTURER, STUDENT, ADMIN)}

AUTH = {"Authorization": "Bearer stub"}


@pytest.fixture
def app():
    app = create_app()
    app.config.update(TESTING=True)
    return app


@pytest.fixture
def client(app, monkeypatch):
    """A client whose bearer token resolves to whichever user the test picks."""
    state = app.config["EDURAG_API_STATE"]
    monkeypatch.setattr(type(state), "db_available", property(lambda self: True))

    current = {"user": None}
    monkeypatch.setattr(type(state), "validate_bearer",
                        lambda self, authorization: current["user"])
    monkeypatch.setattr(type(state), "refresh_enrolled_courses",
                        lambda self, user_id: None)

    c = app.test_client()
    c.as_user = lambda u: current.__setitem__("user", u)
    return c


@pytest.fixture(autouse=True)
def stub_db(monkeypatch):
    """Stand in for src.api.db so these tests never need Postgres."""
    from src.api import db

    created = []

    def fake_create(code, name, description=None, owner_id=None):
        course = {"course_code": code, "course_name": name,
                  "description": description, "owner_id": owner_id}
        created.append(course)
        return course

    def fake_by_id(uid):
        return next((u for u in _USERS.values() if u["user_id"] == uid), None)

    monkeypatch.setattr(db, "get_course_by_code", lambda code: _COURSES.get(code))
    monkeypatch.setattr(db, "get_user_by_email", lambda email: _USERS.get(email))
    monkeypatch.setattr(db, "get_user_by_id", fake_by_id)
    monkeypatch.setattr(db, "list_course_members", lambda code: [])
    monkeypatch.setattr(db, "add_course_membership", lambda *a, **k: {"ok": True})
    monkeypatch.setattr(db, "remove_course_membership", lambda *a, **k: True)
    monkeypatch.setattr(db, "create_course", fake_create)
    monkeypatch.setattr(
        db, "update_course",
        lambda code, **kw: {**_COURSES[code],
                            **{k: v for k, v in kw.items() if v is not None}})
    monkeypatch.setattr(db, "set_course_owner",
                        lambda code, owner: {**_COURSES[code], "owner_id": owner})
    monkeypatch.setattr(
        db, "list_courses_owned_by",
        lambda uid: [c for c in _COURSES.values() if c.get("owner_id") == uid])
    return created


# --- creating ---------------------------------------------------------

def test_lecturer_can_create_a_course(client):
    client.as_user(LECTURER)
    resp = client.post("/api/courses",
                       json={"course_code": "NEW101", "course_name": "New"},
                       headers=AUTH)
    assert resp.status_code == 201


def test_a_lecturers_new_course_is_owned_by_them(client, stub_db):
    client.as_user(LECTURER)
    client.post("/api/courses", json={"course_code": "NEW101", "course_name": "New"},
                headers=AUTH)
    assert stub_db[-1]["owner_id"] == LECTURER["user_id"]


def test_a_lecturer_cannot_create_a_course_owned_by_someone_else(client, stub_db):
    """The owner comes from the token; owner_id in the body is ignored."""
    client.as_user(LECTURER)
    client.post("/api/courses",
                json={"course_code": "NEW101", "course_name": "New",
                      "owner_id": OTHER_LECTURER["user_id"]},
                headers=AUTH)
    assert stub_db[-1]["owner_id"] == LECTURER["user_id"]


def test_students_cannot_create_courses(client):
    client.as_user(STUDENT)
    resp = client.post("/api/courses",
                       json={"course_code": "NEW101", "course_name": "New"},
                       headers=AUTH)
    assert resp.status_code == 403


def test_admin_may_name_the_owner(client, stub_db):
    client.as_user(ADMIN)
    client.post("/api/courses",
                json={"course_code": "NEW101", "course_name": "New",
                      "owner_id": OTHER_LECTURER["user_id"]},
                headers=AUTH)
    assert stub_db[-1]["owner_id"] == OTHER_LECTURER["user_id"]


def test_admin_course_without_an_owner_stays_unowned(client, stub_db):
    client.as_user(ADMIN)
    client.post("/api/courses", json={"course_code": "NEW101", "course_name": "New"},
                headers=AUTH)
    assert stub_db[-1]["owner_id"] is None


# --- managing someone else's course -----------------------------------

WRITES = [
    ("patch", "/api/courses/FOREIGN101", {"course_name": "Renamed"}),
    ("delete", "/api/courses/FOREIGN101", None),
    ("get", "/api/courses/FOREIGN101/members", None),
    ("post", "/api/courses/FOREIGN101/members", {"email": "student@uow.edu.au"}),
    ("delete", "/api/courses/FOREIGN101/members/student@uow.edu.au", None),
]


@pytest.mark.parametrize("method,path,body", WRITES)
def test_lecturer_cannot_touch_another_lecturers_course(client, method, path, body):
    client.as_user(LECTURER)
    resp = getattr(client, method)(path, json=body, headers=AUTH)
    assert resp.status_code == 403
    assert "own" in resp.get_json()["error"].lower()


@pytest.mark.parametrize("method,path,body", WRITES)
def test_admin_can_touch_any_course(client, method, path, body):
    client.as_user(ADMIN)
    resp = getattr(client, method)(path, json=body, headers=AUTH)
    assert resp.status_code < 400, resp.get_json()


def test_lecturer_can_manage_their_own_course(client):
    client.as_user(LECTURER)
    assert client.patch("/api/courses/OWNED101", json={"course_name": "Renamed"},
                        headers=AUTH).status_code == 200
    assert client.get("/api/courses/OWNED101/members", headers=AUTH).status_code == 200


# --- the null owner ---------------------------------------------------

def test_a_course_with_no_owner_is_not_everyones(client):
    """Courses that predate ownership must not become writable by any lecturer
    just because owner_id is NULL."""
    client.as_user(LECTURER)
    resp = client.patch("/api/courses/LEGACY101", json={"course_name": "Hijacked"},
                        headers=AUTH)
    assert resp.status_code == 403


def test_admin_still_manages_an_unowned_course(client):
    client.as_user(ADMIN)
    assert client.patch("/api/courses/LEGACY101", json={"course_name": "Fine"},
                        headers=AUTH).status_code == 200


# --- membership guards ------------------------------------------------

def test_the_owner_cannot_be_removed_from_their_own_course(client):
    """Otherwise one click leaves a course only an admin can manage."""
    client.as_user(LECTURER)
    resp = client.delete("/api/courses/OWNED101/members/lecturer@uow.edu.au",
                         headers=AUTH)
    assert resp.status_code == 409


def test_a_normal_member_can_still_be_removed(client):
    client.as_user(LECTURER)
    resp = client.delete("/api/courses/OWNED101/members/student@uow.edu.au",
                         headers=AUTH)
    assert resp.status_code == 200


def test_unknown_course_is_a_404_not_a_403(client):
    client.as_user(ADMIN)
    assert client.patch("/api/courses/NOPE999", json={"course_name": "x"},
                        headers=AUTH).status_code == 404


# --- transfer ---------------------------------------------------------

def test_only_an_admin_can_transfer_a_course(client):
    client.as_user(LECTURER)
    resp = client.post("/api/courses/OWNED101/owner",
                       json={"owner_email": OTHER_LECTURER["email"]}, headers=AUTH)
    assert resp.status_code == 403


def test_admin_transfers_a_course(client):
    client.as_user(ADMIN)
    resp = client.post("/api/courses/OWNED101/owner",
                       json={"owner_email": OTHER_LECTURER["email"]}, headers=AUTH)
    assert resp.status_code == 200
    assert resp.get_json()["course"]["owner_id"] == OTHER_LECTURER["user_id"]


def test_a_student_cannot_be_made_the_owner(client):
    client.as_user(ADMIN)
    resp = client.post("/api/courses/OWNED101/owner",
                       json={"owner_email": STUDENT["email"]}, headers=AUTH)
    assert resp.status_code == 400


def test_unauthenticated_calls_are_rejected(client):
    client.as_user(None)
    assert client.post("/api/courses",
                       json={"course_code": "X", "course_name": "Y"},
                       headers=AUTH).status_code == 401
    assert client.patch("/api/courses/OWNED101", json={},
                        headers=AUTH).status_code == 401


# --- enrollment refresh reaches storage, not just memory -------------

def test_enrollment_refresh_is_written_to_postgres(app, monkeypatch):
    """T8-24 reloads tokens from Postgres at startup, so refreshing only the
    in-memory copy would last until the next restart and no further - the
    lecturer would quietly lose the course they had just made."""
    from src.api import db

    state = app.config["EDURAG_API_STATE"]
    monkeypatch.setattr(state, "_db_available", True)
    monkeypatch.setattr(db, "get_enrolled_course_codes", lambda uid: ["NEW101"])

    written = {}
    monkeypatch.setattr(db, "update_enrolled_courses_for_user",
                        lambda uid, courses: written.update({uid: list(courses)}))

    state.access_tokens["tok"] = {"user_id": "lect-1", "enrolled_courses": []}
    state.refresh_enrolled_courses("lect-1")

    assert state.access_tokens["tok"]["enrolled_courses"] == ["NEW101"], "in memory"
    assert written == {"lect-1": ["NEW101"]}, "and persisted"


def test_a_failed_write_does_not_break_the_request(app, monkeypatch):
    """The enrollment is still correct for this process; losing it on restart
    is worth a warning, not a 500 in the middle of creating a course."""
    from src.api import db

    state = app.config["EDURAG_API_STATE"]
    monkeypatch.setattr(state, "_db_available", True)
    monkeypatch.setattr(db, "get_enrolled_course_codes", lambda uid: ["NEW101"])

    def boom(uid, courses):
        raise RuntimeError("postgres is away")

    monkeypatch.setattr(db, "update_enrolled_courses_for_user", boom)
    state.access_tokens["tok"] = {"user_id": "lect-1", "enrolled_courses": []}

    assert state.refresh_enrolled_courses("lect-1") == ["NEW101"]
    assert state.access_tokens["tok"]["enrolled_courses"] == ["NEW101"]


# --- can_manage on the course list (T8-09) ----------------------------
#
# The live-config screen decides which courses to offer controls for from this
# flag alone. If it disagreed with _require_course_manager, the page would show
# a lecturer settings they cannot save — the same shape of lie as an API that
# accepts a setting and ignores it. These pin the two together.


def _codes(resp):
    return {c["course_code"]: c["can_manage"] for c in resp.get_json()["courses"]}


@pytest.fixture(autouse=True)
def stub_course_list(monkeypatch):
    """The list endpoint reads APIState.list_courses, not db directly."""
    from src.api.state import APIState
    monkeypatch.setattr(
        APIState, "list_courses",
        lambda self: [{"course_code": c["course_code"], "name": c["course_name"]}
                      for c in _COURSES.values()])


def test_an_admin_may_manage_every_course(client):
    client.as_user(ADMIN)
    assert _codes(client.get("/api/courses", headers=AUTH)) == {
        "OWNED101": True, "FOREIGN101": True, "LEGACY101": True}


def test_a_lecturer_may_manage_only_what_they_own(client):
    client.as_user(LECTURER)
    assert _codes(client.get("/api/courses", headers=AUTH)) == {
        "OWNED101": True, "FOREIGN101": False, "LEGACY101": False}


def test_a_student_may_manage_nothing(client):
    client.as_user(STUDENT)
    assert set(_codes(client.get("/api/courses", headers=AUTH)).values()) == {False}


def test_an_ownerless_course_is_not_managed_by_any_lecturer(client):
    """A null owner is read as admin-only, matching _require_course_manager."""
    client.as_user(OTHER_LECTURER)
    assert _codes(client.get("/api/courses", headers=AUTH))["LEGACY101"] is False


def test_can_manage_agrees_with_what_a_write_actually_does(client):
    """The flag has to predict the PATCH, or the screen misleads."""
    client.as_user(LECTURER)
    flags = _codes(client.get("/api/courses", headers=AUTH))
    for code, may in flags.items():
        resp = client.patch(f"/api/courses/{code}",
                            json={"course_name": "renamed"}, headers=AUTH)
        allowed = resp.status_code == 200
        assert allowed == may, (
            f"{code}: can_manage={may} but PATCH returned {resp.status_code}")


def test_the_list_still_works_without_a_database(client, monkeypatch, app):
    """No Postgres means no ownership lookup; nobody is offered controls
    rather than everybody being offered them."""
    state = app.config["EDURAG_API_STATE"]
    monkeypatch.setattr(type(state), "db_available", property(lambda self: False))
    client.as_user(LECTURER)
    resp = client.get("/api/courses", headers=AUTH)
    assert resp.status_code == 200
    assert set(_codes(resp).values()) == {False}
