"""Students join and leave courses themselves (T8-05).

The only way into a course used to be POST /courses/<code>/members, which only
the course's manager may call, so a student who had just signed up could see
every course and ask about none of them. A student may now join any active
course directly, and leave any course.

What these tests pin down:

  * only students use these routes, and the manager-only members route is not
    loosened by them;
  * success is reported only once the stored token carries the change, because
    that token - not the membership table - is what authorises the student's
    next request on every worker;
  * joining and leaving are safe to repeat, and an inactive course cannot be
    joined.

The suite runs without a database (see conftest), so `db` is stubbed here the
same way test_course_ownership does. test_student_self_enrolment_postgres runs
the same flow against real tables.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

from src.api.app import create_app

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "streamlit"))
import api_client  # noqa: E402
from api_client import APIConfig, PaediaAPIClient  # noqa: E402


STUDENT = {"user_id": "stu-1", "email": "student@uow.edu.au", "role": "student",
           "username": "student_demo"}
LECTURER = {"user_id": "lect-1", "email": "lecturer@uow.edu.au", "role": "lecturer",
            "username": "lecturer_demo"}
ADMIN = {"user_id": "adm-1", "email": "admin@uow.edu.au", "role": "admin",
         "username": "admin_demo"}

OPEN = {"course_code": "OPEN101", "course_name": "Open", "is_active": True, "owner_id": "lect-1"}
CLOSED = {"course_code": "SHUT101", "course_name": "Closed", "is_active": False, "owner_id": "lect-1"}

AUTH = {"Authorization": "Bearer stub"}


class Backend:
    """What the stubbed db holds: membership rows and each user's stored token."""

    def __init__(self):
        self.memberships: dict[str, set[str]] = {}
        self.added: list[tuple[str, str, str]] = []
        self.token_courses: dict[str, list[str]] = {}
        self.token_writes_fail = False


@pytest.fixture
def backend(monkeypatch):
    from src.api import db

    store = Backend()
    courses = {c["course_code"]: c for c in (OPEN, CLOSED)}
    identities = {code: {**course, "id": f"course-{code}"}
                  for code, course in courses.items()}
    monkeypatch.setattr(db, "get_course_by_ref", lambda ref: next(
        (row for code, row in identities.items() if ref in (code, row["id"])), None))
    emails = {u["user_id"]: u["email"] for u in (STUDENT, LECTURER, ADMIN)}

    def add(code, email, role):
        store.memberships.setdefault(email, set()).add(code)
        store.added.append((code, email, role))
        return {"membership_role": role}

    def remove(code, email):
        codes = store.memberships.get(email, set())
        if code not in codes:
            return False
        codes.discard(code)
        return True

    def write_tokens(user_id, codes):
        if store.token_writes_fail:
            raise RuntimeError("postgres is away")
        store.token_courses[user_id] = list(codes)

    monkeypatch.setattr(db, "get_course_by_code", lambda code: courses.get(code))
    monkeypatch.setattr(db, "add_course_membership", add)
    monkeypatch.setattr(db, "remove_course_membership", remove)
    monkeypatch.setattr(db, "get_enrolled_course_codes",
                        lambda uid: sorted(store.memberships.get(emails[uid], set())))
    monkeypatch.setattr(db, "update_enrolled_courses_for_user", write_tokens)
    monkeypatch.setattr(db, "load_all_documents", lambda: [])
    return store


@pytest.fixture
def client(monkeypatch, backend):
    monkeypatch.setenv("EDURAG_OLLAMA_WARMUP", "false")
    app = create_app()
    app.config.update(TESTING=True)
    state = app.config["EDURAG_API_STATE"]
    monkeypatch.setattr(state, "_db_available", True)

    signed_in = {"user": None}

    def sign_in(user, courses=()):
        signed_in["user"] = user
        if user is not None:
            backend.memberships[user["email"]] = set(courses)
            backend.token_courses[user["user_id"]] = list(courses)

    def read_stored_token(self, authorization, **kwargs):
        # With Postgres up, every worker authorises from the stored token row,
        # so answer from the backend's copy of it, never from this process.
        user = signed_in["user"]
        if user is None:
            return None
        return {**user, "enrolled_courses": list(backend.token_courses[user["user_id"]])}

    monkeypatch.setattr(type(state), "validate_bearer", read_stored_token)
    c = app.test_client()
    c.sign_in = sign_in
    c.state = state
    return c


def join(client, code="OPEN101"):
    return client.post(f"/api/courses/{code}/join", headers=AUTH)


def leave(client, code="OPEN101"):
    return client.post(f"/api/courses/{code}/leave", headers=AUTH)


def documents_status(client, code="OPEN101"):
    return client.get(f"/api/documents?course_id={code}", headers=AUTH).status_code


def catalog_flags(client):
    return {c["course_code"]: c["is_enrolled"]
            for c in client.get("/api/courses", headers=AUTH).get_json()["courses"]}


# --- joining -----------------------------------------------------------

def test_a_student_joins_an_active_course(client, backend):
    client.sign_in(STUDENT)
    resp = join(client)

    assert resp.status_code == 201
    assert resp.get_json() == {"status": "enrolled", "course_code": "OPEN101",
                               "enrolled_courses": ["OPEN101"]}
    assert backend.added == [("OPEN101", STUDENT["email"], "student")]


def test_the_next_request_in_that_course_is_allowed(client):
    """The token carried the enrolment list from login. Without the refresh the
    student would join and still be told they are not a member."""
    client.sign_in(STUDENT)
    assert documents_status(client) == 403

    join(client)

    assert documents_status(client) == 200


def test_joining_twice_changes_nothing(client, backend):
    client.sign_in(STUDENT)
    join(client)
    again = join(client)

    assert again.status_code == 200
    assert again.get_json()["status"] == "already_enrolled"
    assert len(backend.added) == 1


def test_an_inactive_course_cannot_be_joined(client, backend):
    client.sign_in(STUDENT)
    resp = join(client, "SHUT101")

    assert resp.status_code == 409
    assert backend.added == []


def test_an_unknown_course_is_not_found(client):
    client.sign_in(STUDENT)

    assert join(client, "NOPE999").status_code == 404
    assert leave(client, "NOPE999").status_code == 404


# --- success means the student can use it -----------------------------

def test_a_join_the_token_does_not_carry_yet_is_not_reported_as_done(client, backend):
    """The membership row is written but the stored token could not be. Saying
    "enrolled" here would send the student to a course that refuses them."""
    client.sign_in(STUDENT)
    backend.token_writes_fail = True

    resp = join(client)

    assert resp.status_code == 503
    assert "try again" in resp.get_json()["error"]
    assert documents_status(client) == 403

    backend.token_writes_fail = False
    retry = join(client)

    assert retry.status_code == 200
    assert retry.get_json()["status"] == "already_enrolled"
    assert documents_status(client) == 200


def test_a_leave_the_token_does_not_carry_yet_is_not_reported_as_done(client, backend):
    client.sign_in(STUDENT, courses=["OPEN101"])
    backend.token_writes_fail = True

    assert leave(client).status_code == 503

    backend.token_writes_fail = False
    retry = leave(client)

    assert retry.status_code == 200
    assert retry.get_json()["status"] == "not_enrolled"
    assert documents_status(client) == 403


# --- who may use it ----------------------------------------------------

@pytest.mark.parametrize("user", [LECTURER, ADMIN], ids=["lecturer", "admin"])
def test_only_students_join_or_leave_themselves(client, backend, user):
    client.sign_in(user)

    assert join(client).status_code == 403
    assert leave(client).status_code == 403
    assert backend.added == []


def test_the_manager_only_members_route_is_not_loosened(client, backend):
    """Joining is a separate route precisely so this one stays closed."""
    client.sign_in(STUDENT)
    resp = client.post("/api/courses/OPEN101/members",
                       json={"email": STUDENT["email"]}, headers=AUTH)

    assert resp.status_code == 403
    assert backend.added == []


def test_signed_out_callers_are_rejected(client):
    client.sign_in(None)

    assert join(client).status_code == 401
    assert leave(client).status_code == 401


def test_without_the_database_joining_is_unavailable(client, monkeypatch, backend):
    monkeypatch.setattr(client.state, "_db_available", False)
    client.sign_in(STUDENT)

    assert join(client).status_code == 503
    assert leave(client).status_code == 503
    assert backend.added == []


# --- leaving -----------------------------------------------------------

def test_a_student_leaves_a_course_and_loses_access(client):
    client.sign_in(STUDENT)
    join(client)
    resp = leave(client)

    assert resp.status_code == 200
    assert resp.get_json() == {"status": "unenrolled", "course_code": "OPEN101",
                               "enrolled_courses": []}
    assert documents_status(client) == 403


def test_leaving_a_course_you_are_not_in_is_not_an_error(client):
    client.sign_in(STUDENT)
    resp = leave(client)

    assert resp.status_code == 200
    assert resp.get_json()["status"] == "not_enrolled"


def test_a_course_that_has_closed_can_still_be_left(client):
    client.sign_in(STUDENT, courses=["SHUT101"])
    resp = leave(client, "SHUT101")

    assert resp.status_code == 200
    assert resp.get_json()["status"] == "unenrolled"


# --- the refresh both routes rely on -----------------------------------

def test_a_login_during_the_refresh_does_not_break_it(client, backend):
    """Logins on other threads add tokens to this worker's store while a join
    walks it to rewrite the student's copies. Walking the dict itself raised
    "dictionary changed size during iteration"; the refresh walks a copy."""
    state = client.state

    class LogsSomeoneInWhenRead(dict):
        def get(self, key, default=None):
            state.access_tokens[f"login-{len(state.access_tokens)}"] = {"user_id": "someone-else"}
            return super().get(key, default)

    backend.memberships[STUDENT["email"]] = {"OPEN101"}
    state.access_tokens["theirs"] = LogsSomeoneInWhenRead(user_id="stu-1", enrolled_courses=[])
    state.access_tokens["another"] = {"user_id": "someone-else"}

    assert state.refresh_enrolled_courses("stu-1") == ["OPEN101"]
    assert state.access_tokens["theirs"]["enrolled_courses"] == ["OPEN101"]


# --- the catalog -------------------------------------------------------

def test_the_catalog_says_which_courses_you_are_in(client, monkeypatch):
    from src.api.state import APIState
    monkeypatch.setattr(APIState, "list_courses", lambda self: [
        {"course_code": c["course_code"], "name": c["course_name"], "is_active": c["is_active"]}
        for c in (OPEN, CLOSED)])
    client.sign_in(STUDENT)

    assert catalog_flags(client) == {"OPEN101": False, "SHUT101": False}
    join(client)
    assert catalog_flags(client) == {"OPEN101": True, "SHUT101": False}


def test_the_catalog_flag_follows_the_access_check_without_a_database(client, monkeypatch):
    """A login without Postgres carries fixture course ids, not codes. Comparing
    codes alone would show that student as outside every course they are in."""
    monkeypatch.setattr(client.state, "_db_available", False)
    fixture_ids = [c["course_id"] for c in client.state.fixtures["courses"]]
    client.sign_in(STUDENT, courses=fixture_ids)

    assert catalog_flags(client) == {"CSIT321": True, "CSCI203": True}


# --- the Streamlit client ----------------------------------------------

def _response(status, body):
    return Mock(status_code=status, json=Mock(return_value=body))


@pytest.fixture
def live_client():
    # Retries are configured on purpose: a join must still be sent only once.
    return PaediaAPIClient(APIConfig(base_url="http://test.invalid", use_fixtures=False, max_retries=2))


def test_client_join_returns_the_new_enrolment_list(live_client, monkeypatch):
    post = Mock(return_value=_response(201, {
        "status": "enrolled", "course_code": "OPEN101", "enrolled_courses": ["OPEN101"]}))
    monkeypatch.setattr(api_client.requests, "post", post)

    result = live_client.join_course("OPEN101")

    assert result["success"] is True
    assert result["enrolled_courses"] == ["OPEN101"]
    assert post.call_args.args[0] == "http://test.invalid/api/courses/OPEN101/join"


def test_client_join_refusal_carries_the_servers_reason(live_client, monkeypatch):
    monkeypatch.setattr(api_client.requests, "post", Mock(return_value=_response(
        409, {"error": "course 'SHUT101' is not open to join right now"})))

    result = live_client.join_course("SHUT101")

    assert result["success"] is False
    assert "not open to join" in result["error"]
    assert result["status_code"] == 409
    assert result["enrolled_courses"] is None


def test_client_join_is_sent_once_after_a_timeout(live_client, monkeypatch):
    post = Mock(side_effect=api_client.requests.Timeout())
    monkeypatch.setattr(api_client.requests, "post", post)

    assert live_client.join_course("OPEN101")["success"] is False
    assert post.call_count == 1


def test_client_does_not_treat_an_unconfirmed_change_as_done(live_client, monkeypatch):
    monkeypatch.setattr(api_client.requests, "post", Mock(return_value=_response(
        503, {"error": "Your courses could not be updated just now. Please try again."})))

    result = live_client.join_course("OPEN101")

    assert result["success"] is False
    assert result["error"] == "Your courses could not be updated just now. Please try again."
    assert result["enrolled_courses"] is None


def test_client_leave(live_client, monkeypatch):
    post = Mock(return_value=_response(
        200, {"status": "unenrolled", "course_code": "OPEN101", "enrolled_courses": []}))
    monkeypatch.setattr(api_client.requests, "post", post)

    result = live_client.leave_course("OPEN101")

    assert result["success"] is True
    assert result["status"] == "unenrolled"
    assert result["enrolled_courses"] == []
    assert post.call_args.args[0] == "http://test.invalid/api/courses/OPEN101/leave"


def test_client_in_demo_mode_sends_nothing(monkeypatch):
    monkeypatch.setattr(api_client.requests, "post",
                        Mock(side_effect=AssertionError("demo mode used the network")))
    demo = PaediaAPIClient(APIConfig(use_fixtures=True))

    assert demo.join_course("OPEN101")["success"] is False
    assert demo.leave_course("OPEN101")["success"] is False
