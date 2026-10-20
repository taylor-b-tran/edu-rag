"""The interface side of lecturer approval.

A lecturer who signs up is told the account is waiting and is not signed in; the
sign-in page shows the server's reason; the Admin Dashboard lists the accounts
waiting for a decision and lets an administrator approve or reject each one,
after a confirmation (the same two-step as deleting a document).
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "streamlit"))
import main
import api_client
from api_client import APIConfig, APIReadError, PaediaAPIClient


class State(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


PENDING = [
    {"user_id": "u-1", "username": "new_lecturer", "email": "new.lecturer@uow.edu.au",
     "role": "lecturer", "approval_status": "pending", "created_at": "2026-10-08T01:30:00+00:00"},
    {"user_id": "u-2", "username": "second", "email": "second@uow.edu.au",
     "role": "lecturer", "approval_status": "pending", "created_at": "2026-10-08T02:30:00+00:00"},
]


@pytest.fixture
def ui(monkeypatch):
    st = MagicMock()
    st.session_state = State(user={"role": "Admin", "name": "Admin", "enrolled_courses": []},
                             authenticated=False, login_error=None, signup_error=None,
                             current_page="admin", sessions=[], active_session_id=None, course_id="")
    st.button.return_value = False
    st.form_submit_button.return_value = False
    st.tabs.return_value = (MagicMock(), MagicMock())
    st.columns.side_effect = lambda spec, **kwargs: [MagicMock() for _ in range(spec if isinstance(spec, int) else len(spec))]
    api = MagicMock()
    api.get_pending_users.return_value = list(PENDING)
    api.get_admin_stats.return_value = {"courses": 2}
    api.get_courses.return_value = []
    monkeypatch.setattr(main, "st", st)
    monkeypatch.setattr(main, "api", api)
    return st, api


def _texts(mock):
    return [str(c.args[0]) for c in mock.call_args_list if c.args]


def _click(st, *keys):
    st.button.side_effect = lambda *a, **kw: kw.get("key") in keys


# --- sign-up and sign-in ---------------------------------------------------

def test_a_pending_lecturer_is_not_signed_in_and_is_told_why(ui):
    st, api = ui
    st.session_state.signup_email = "new@uow.edu.au"
    st.session_state.signup_username = "new"
    st.session_state.signup_password = "Str0ngPassw0rd!"
    st.session_state.signup_confirm = "Str0ngPassw0rd!"
    st.session_state.signup_role = "Lecturer"
    api.signup.return_value = {"success": False, "pending": True, "user": {}, "jwt_token": None,
                               "error": "Your lecturer account has been created. An administrator must approve it before you can sign in."}
    main.handle_signup_submit()
    assert not st.session_state.authenticated
    assert "administrator must approve" in st.session_state.signup_notice
    assert not st.session_state.signup_error


def test_the_sign_up_page_shows_the_notice_as_a_success_not_an_error(ui):
    st, api = ui
    st.session_state.signup_notice = "Your lecturer account has been created."
    main.render_login_page()
    assert "Your lecturer account has been created." in _texts(st.success)
    assert "Your lecturer account has been created." not in _texts(st.error)


def test_a_failed_sign_up_still_shows_an_error(ui):
    st, api = ui
    st.session_state.signup_email = "new@uow.edu.au"
    st.session_state.signup_username = "new"
    st.session_state.signup_password = "Str0ngPassw0rd!"
    st.session_state.signup_confirm = "Str0ngPassw0rd!"
    api.signup.return_value = {"success": False, "user": {}, "jwt_token": None, "error": "That email is already registered."}
    main.handle_signup_submit()
    assert st.session_state.signup_error == "That email is already registered."
    assert not st.session_state.get("signup_notice")


def test_the_server_reason_reaches_the_sign_in_page(ui):
    st, api = ui
    st.session_state.login_email = "new@uow.edu.au"
    st.session_state.login_password = "x"
    api.login.return_value = {"success": False, "user": {}, "error": "Your lecturer account is waiting for an administrator to approve it."}
    main.handle_login_submit()
    assert st.session_state.login_error == "Your lecturer account is waiting for an administrator to approve it."
    assert not st.session_state.authenticated


# --- the Admin Dashboard ---------------------------------------------------

def test_the_dashboard_lists_the_waiting_accounts_with_a_count(ui):
    st, api = ui
    main.render_pending_lecturers()
    assert "#### Pending lecturer accounts (2)" in _texts(st.markdown)
    keys = [c.kwargs.get("key") for c in st.button.call_args_list]
    assert {"approve_u-1", "reject_u-1", "approve_u-2", "reject_u-2"} <= set(keys)


def test_an_empty_list_says_so(ui):
    st, api = ui
    api.get_pending_users.return_value = []
    main.render_pending_lecturers()
    assert "#### Pending lecturer accounts (0)" in _texts(st.markdown)
    assert "No accounts are waiting." in _texts(st.caption)


def test_pressing_approve_asks_before_acting(ui):
    st, api = ui
    _click(st, "approve_u-1")
    main.render_pending_lecturers()
    api.approve_user.assert_not_called()
    assert st.session_state.confirm_user_decision == {"user_id": "u-1", "action": "approve"}
    st.rerun.assert_called()


def test_confirming_approve_calls_the_api_once_and_clears_the_question(ui):
    st, api = ui
    api.approve_user.return_value = {"success": True, "error": None, "user": {}}
    st.session_state.confirm_user_decision = {"user_id": "u-1", "action": "approve"}
    _click(st, "approve_yes_u-1")
    main.render_pending_lecturers()
    api.approve_user.assert_called_once_with("u-1")
    api.reject_user.assert_not_called()
    assert st.session_state.confirm_user_decision is None
    st.toast.assert_called()
    st.rerun.assert_called()


def test_typed_names_never_reach_a_markdown_message(ui):
    # The address is typed by whoever signed up; st.warning and st.toast render
    # markdown, so it is shown only on the plain-text card line.
    st, api = ui
    api.get_pending_users.return_value = [{"user_id": "u-9", "username": "x",
                                           "email": "[click](https://example.invalid)@x.com",
                                           "created_at": "2026-10-01T09:00:00+00:00"}]
    api.approve_user.return_value = {"success": True, "error": None, "user": {}}
    st.session_state.confirm_user_decision = {"user_id": "u-9", "action": "approve"}
    main.render_pending_lecturers()
    shown = _texts(st.warning)
    assert shown and not any("click" in t or "example.invalid" in t for t in shown)
    _click(st, "approve_yes_u-9")
    main.render_pending_lecturers()
    assert not any("click" in str(c) for c in st.toast.call_args_list)


def test_a_pending_question_does_not_survive_a_change_of_account(ui):
    st, api = ui
    st.session_state.confirm_user_decision = {"user_id": "u-1", "action": "approve"}
    st.session_state.signup_notice = "waiting"
    main._clear_identity_state()
    assert not st.session_state.get("confirm_user_decision")
    assert not st.session_state.get("signup_notice")


def test_confirming_reject_calls_reject(ui):
    st, api = ui
    api.reject_user.return_value = {"success": True, "error": None, "user": {}}
    st.session_state.confirm_user_decision = {"user_id": "u-2", "action": "reject"}
    _click(st, "reject_yes_u-2")
    main.render_pending_lecturers()
    api.reject_user.assert_called_once_with("u-2")
    api.approve_user.assert_not_called()


def test_cancelling_changes_nothing(ui):
    st, api = ui
    st.session_state.confirm_user_decision = {"user_id": "u-1", "action": "approve"}
    _click(st, "decision_no_u-1")
    main.render_pending_lecturers()
    api.approve_user.assert_not_called()
    api.reject_user.assert_not_called()
    assert st.session_state.confirm_user_decision is None


def test_a_failed_decision_is_shown_and_does_not_look_done(ui):
    st, api = ui
    api.approve_user.return_value = {"success": False, "error": "Account approval requires the database backend."}
    st.session_state.confirm_user_decision = {"user_id": "u-1", "action": "approve"}
    _click(st, "approve_yes_u-1")
    main.render_pending_lecturers()
    assert "Account approval requires the database backend." in _texts(st.error)
    st.toast.assert_not_called()


def test_an_unreadable_list_does_not_take_the_dashboard_down(ui):
    st, api = ui
    api.get_pending_users.side_effect = APIReadError("/api/admin/users/pending", {"status_code": 500, "message": "boom"})
    main.render_pending_lecturers()
    st.warning.assert_called_once()


def test_the_admin_page_includes_the_section(ui):
    st, api = ui
    api.get_course_members.return_value = []
    main.render_admin_page()
    api.get_pending_users.assert_called_once()


# --- the client ----------------------------------------------------------------

@pytest.fixture
def client():
    return PaediaAPIClient(APIConfig(base_url="http://test.invalid", use_fixtures=False))


def test_client_signup_reports_a_pending_lecturer(client, monkeypatch):
    monkeypatch.setattr(client, "_post", lambda ep, body: {"status": "pending_approval", "message": "Wait for approval."})
    result = client.signup("a@b.c", "a", "Str0ngPassw0rd!", "lecturer")
    assert result["success"] is False and result["pending"] is True
    assert result["error"] == "Wait for approval."
    assert client._jwt_token is None


def test_client_signup_still_signs_a_student_in(client, monkeypatch):
    monkeypatch.setattr(client, "_post", lambda ep, body: {"access_token": "t", "refresh_token": "r", "user": {"role": "student"}})
    result = client.signup("a@b.c", "a", "Str0ngPassw0rd!", "student")
    assert result["success"] is True and result["jwt_token"] == "t" and not result.get("pending")


def test_client_decisions_post_to_the_right_route(client, monkeypatch):
    seen = []
    monkeypatch.setattr(client, "_post", lambda ep, body: seen.append(ep) or {"user": {"user_id": "u-1"}})
    assert client.approve_user("u-1")["success"] is True
    assert client.reject_user("u-1")["success"] is True
    assert seen == ["/api/admin/users/u-1/approve", "/api/admin/users/u-1/reject"]


def test_client_decision_failure_carries_the_reason(client, monkeypatch):
    monkeypatch.setattr(client, "_post", lambda ep, body: {"_api_error": True, "message": "Admin role required."})
    assert client.approve_user("u-1") == {"success": False, "error": "Admin role required."}
    monkeypatch.setattr(client, "_post", lambda ep, body: None)
    assert client.reject_user("u-1")["success"] is False


def test_client_lists_pending_users(client, monkeypatch):
    monkeypatch.setattr(client, "_get", lambda ep, params=None: {"users": PENDING})
    assert client.get_pending_users() == PENDING


def test_client_in_demo_mode_sends_nothing():
    demo = PaediaAPIClient(APIConfig(base_url="http://test.invalid", use_fixtures=True))
    assert demo.approve_user("u-1")["success"] is False
    assert "live system" in demo.approve_user("u-1")["error"]
