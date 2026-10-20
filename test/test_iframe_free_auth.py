"""Native sign-in and fixed-lifetime, first-party session persistence."""
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps/streamlit"))
import main
import auth_cookies


class State(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


@pytest.fixture
def ui(monkeypatch):
    st = MagicMock()
    st.session_state = State(authenticated=False, login_error=None, signup_error=None)
    st.context.cookies = {}
    st.columns.side_effect = lambda spec, **kw: [MagicMock() for _ in spec]
    st.tabs.return_value = (MagicMock(), MagicMock())
    st.form_submit_button.return_value = False
    st.button.return_value = False
    api = MagicMock()
    monkeypatch.setattr(main, "st", st)
    monkeypatch.setattr(main, "api", api)
    return st, api


def test_sign_in_fields_render_without_mounting_a_legacy_component(ui, monkeypatch):
    st, api = ui
    legacy = MagicMock(side_effect=AssertionError("Legacy iframe must not mount"))
    monkeypatch.setattr(main.components, "declare_component", legacy)
    main.render_login_page()
    legacy.assert_not_called()
    api.login.assert_not_called()
    assert any(c.args[0] == "Email Address" for c in st.text_input.call_args_list)
    assert any(c.kwargs.get("type") == "password" for c in st.text_input.call_args_list)


def test_native_form_reuses_api_authentication_and_shows_rejection(ui):
    st, api = ui
    st.text_input.side_effect = ["candidate@example.invalid", "wrong-pass"]
    st.form_submit_button.return_value = True
    api.login.return_value = {"success": False, "error": "Invalid email or password."}
    main._render_basic_login()
    api.login.assert_called_once_with("candidate@example.invalid", "wrong-pass")
    assert not st.session_state.authenticated
    assert st.session_state.login_error == "Invalid email or password."


def test_form_does_not_authenticate_before_submission(ui):
    st, api = ui
    st.text_input.side_effect = ["candidate@example.invalid", "some-password"]
    main._render_basic_login()
    api.login.assert_not_called()
    st.rerun.assert_not_called()


def test_successful_native_sign_in_uses_only_server_identity(ui, monkeypatch):
    st, api = ui
    st.text_input.side_effect = ["candidate@example.invalid", "accepted-password"]
    st.form_submit_button.return_value = True
    api.login.return_value = {
        "success": True, "jwt_token": "test-access-token",
        "user": {"user_id": "test-user", "email": "candidate@example.invalid",
                 "role": "student", "enrolled_courses": ["COURSE123"]}}
    monkeypatch.setattr(main, "_course_options_for_user", lambda user: ["COURSE123"])
    monkeypatch.setattr(main, "_default_course_for_user", lambda user: "COURSE123")
    monkeypatch.setattr(main, "_hydrate_sessions_from_server",
                        lambda: st.session_state.update(sessions=["test-session"]))
    main._render_basic_login()
    assert st.session_state.authenticated
    assert st.session_state.user["role"] == "Student"
    assert main._cookies().get(main._AUTH_COOKIE) == "test-access-token"
    token, expires = st.session_state["_auth_cookie_write"]
    assert token == "test-access-token"
    assert expires.tzinfo is not None


def test_cookie_restore_reads_initial_request_without_frontend_round_trip(ui):
    st, _ = ui
    st.context.cookies = {main._AUTH_COOKIE: "access-from-reload"}
    assert main._cookies().get(main._AUTH_COOKIE) == "access-from-reload"


def test_logout_does_not_restore_the_stale_initial_request_cookie(ui):
    st, api = ui
    st.context.cookies = {main._AUTH_COOKIE: "old-access"}
    main._forget_session()
    assert main._cookies().get(main._AUTH_COOKIE) is None
    assert not main._restore_session_from_cookie()
    api.get_current_user.assert_not_called()


def test_new_login_overrides_an_older_request_cookie(ui):
    st, _ = ui
    st.context.cookies = {main._AUTH_COOKIE: "old-access"}
    main._remember_session("new-access")
    assert main._cookies().get(main._AUTH_COOKIE) == "new-access"


@pytest.mark.parametrize("ack,cleared,failed", [
    ({"id": "current", "ok": True}, True, False),
    ({"id": "stale", "ok": True}, False, None),
    ({"id": "current", "ok": False}, True, True),
    (None, False, None),
])
def test_only_the_current_cookie_acknowledgement_finishes_the_write(ui, monkeypatch, ack, cleared, failed):
    st, _ = ui
    main._remember_session("test-access")
    st.session_state["_auth_cookie_revision"] = "current"
    writer = MagicMock(return_value=SimpleNamespace(result=ack))
    monkeypatch.setattr(auth_cookies, "_cookie_writer", lambda: writer)
    initial_expiry = st.session_state["_auth_cookie_write"][1]
    main._flush_auth_cookie()
    assert ("_auth_cookie_write" not in st.session_state) is cleared
    assert st.session_state.get("_auth_cookie_write_failed") is failed
    assert writer.call_args.kwargs["data"]["expires"] == initial_expiry.isoformat()
    assert "refresh_token" not in writer.call_args.kwargs["data"]


def test_delete_write_has_no_access_token_and_does_not_extend_expiry(ui, monkeypatch):
    st, _ = ui
    main._forget_session()
    writer = MagicMock(return_value=SimpleNamespace(result=None))
    monkeypatch.setattr(auth_cookies, "_cookie_writer", lambda: writer)
    main._flush_auth_cookie()
    data = writer.call_args.kwargs["data"]
    assert data["value"] is None and data["expires"] is None
    assert st.session_state["_auth_cookie_override"] is None
