"""Unenrolled users must be able to browse, join and sign out."""
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "streamlit"))
import main
from api_client import APIReadError


class State(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


@pytest.fixture
def ui(monkeypatch):
    st = MagicMock()
    st.session_state = State(user={"role": "Student", "name": "Test Student", "enrolled_courses": []},
                             course_id="", current_page="chat", sessions=[], active_session_id=None)
    st.button.return_value = False
    st.columns.side_effect = lambda spec, **kwargs: [MagicMock() for _ in range(spec if isinstance(spec, int) else len(spec))]
    api = MagicMock()
    api.get_courses.return_value = [{"course_code": "TEST101", "name": "Test course", "is_active": True}]
    api.get_health.return_value = {}
    monkeypatch.setattr(main, "st", st)
    monkeypatch.setattr(main, "api", api)
    return st, api


def test_unenrolled_sidebar_does_not_fetch_private_materials_and_shows_logout(ui):
    st, api = ui
    main.render_sidebar()
    api.get_documents.assert_not_called()
    assert any("Sign Out" in c.args[0] for c in st.button.call_args_list)


def test_document_failure_does_not_remove_logout_or_navigation(ui):
    st, api = ui
    # Enrolled as well as selected: a course id set on an account that is in no
    # course is now resolved away as stale, and then the sidebar never fetches,
    # so the failure this test is about could not happen.
    st.session_state.user["enrolled_courses"] = ["TEST101"]
    st.session_state.course_options = ["TEST101"]
    st.session_state.course_id = "TEST101"
    api.get_documents.side_effect = APIReadError("/documents", {"status_code": 403, "message": "Forbidden"})
    main.render_sidebar()
    assert any("Sign Out" in c.args[0] for c in st.button.call_args_list)
    assert any(c.kwargs.get("key") == "nav_courses" for c in st.button.call_args_list)
    st.warning.assert_called_once()


def test_available_course_can_render_join_without_reading_private_documents(ui):
    st, api = ui
    main.render_courses_page()
    api.get_documents.assert_not_called()
    assert any(c.kwargs.get("key") == "join_TEST101" for c in st.button.call_args_list)


def test_empty_state_opens_course_browser(ui):
    st, api = ui
    st.button.return_value = True
    main._render_no_courses_notice()
    assert st.session_state.current_page == "courses"
    st.rerun.assert_called_once()


def test_new_chat_preserves_no_course_instead_of_assigning_default(ui, monkeypatch):
    st, api = ui
    monkeypatch.setattr(main, "_remember_chat_selection", lambda: None)
    session = main.create_new_session()
    assert session["course_id"] == ""
    assert st.session_state.course_id == ""


def test_materials_page_without_a_course_offers_browse(ui):
    st, api = ui
    main.render_uploads_page()
    api.get_documents.assert_not_called()
    assert any(c.kwargs.get("key") == "browse_courses_empty" for c in st.button.call_args_list)


def test_first_join_selects_course_and_updates_membership(ui):
    st, api = ui
    st.button.side_effect = lambda *a, **kw: kw.get("key") == "join_TEST101"
    api.join_course.return_value = {"success": True, "enrolled_courses": ["TEST101"]}
    main.render_courses_page()
    api.join_course.assert_called_once_with("TEST101")
    assert st.session_state.user["enrolled_courses"] == ["TEST101"]
    assert st.session_state.course_id == "TEST101"
    assert st.session_state.selected_course_id == "TEST101"


# ── Staff are not offered a Join the server always refuses ──

def _texts(mock):
    return [str(c.args[0]) for c in mock.call_args_list if c.args]


def test_lecturer_is_not_offered_a_join_the_server_refuses(ui):
    st, api = ui
    st.session_state.user["role"] = "Lecturer"
    main.render_courses_page()
    assert not any(str(c.kwargs.get("key", "")).startswith("join_") for c in st.button.call_args_list)
    api.join_course.assert_not_called()
    assert any("administrator" in t for t in _texts(st.caption) + _texts(st.info))


def test_lecturer_without_courses_is_told_they_are_not_assigned(ui):
    st, api = ui
    st.session_state.user["role"] = "Lecturer"
    main.render_courses_page()
    assert "You are not assigned to any course yet." in _texts(st.info)


def test_admin_is_not_offered_join(ui):
    # Guard: an admin sees every active course under Your Courses, so there is
    # nothing to join. Pins that behaviour.
    st, api = ui
    st.session_state.user["role"] = "Admin"
    main.render_courses_page()
    assert not any(str(c.kwargs.get("key", "")).startswith("join_") for c in st.button.call_args_list)
