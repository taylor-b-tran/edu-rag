"""An account with no course is told what is true for its own role.

A new lecturer has no courses, and the student-only notice sent them to
"join an available course" through Join buttons the API refuses (students
join themselves; lecturers and admins are added by the person who manages the
course). The wording now follows the role. The student text and its Browse
button are unchanged.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "streamlit"))
import main


class State(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


@pytest.fixture
def ui(monkeypatch):
    st = MagicMock()
    st.session_state = State(user={"role": "Student", "name": "Test User", "enrolled_courses": []},
                             course_id="", current_page="chat", sessions=[], active_session_id=None)
    st.button.return_value = False
    st.columns.side_effect = lambda spec, **kwargs: [MagicMock() for _ in range(spec if isinstance(spec, int) else len(spec))]
    api = MagicMock()
    api.get_courses.return_value = [{"course_code": "TEST101", "name": "Test course", "is_active": True}]
    api.get_health.return_value = {}
    monkeypatch.setattr(main, "st", st)
    monkeypatch.setattr(main, "api", api)
    return st, api


def _texts(mock):
    return [str(c.args[0]) for c in mock.call_args_list if c.args]


def _button_keys(st):
    return [c.kwargs.get("key") for c in st.button.call_args_list]


def test_lecturer_without_a_course_is_told_to_ask_an_administrator(ui):
    st, api = ui
    st.session_state.user["role"] = "Lecturer"
    main.render_chat_page()
    assert any("not assigned" in t for t in _texts(st.info))
    assert any("administrator" in t for t in _texts(st.write))
    everything = _texts(st.info) + _texts(st.write) + _texts(st.caption) + _texts(st.markdown)
    assert not any("join an available course" in t for t in everything)
    assert "browse_courses_empty" not in _button_keys(st)


def test_admin_with_no_active_course_is_sent_to_the_admin_dashboard(ui):
    st, api = ui
    st.session_state.user["role"] = "Admin"
    api.get_courses.return_value = []
    st.button.side_effect = lambda *a, **kw: kw.get("key") == "open_admin_empty"
    main.render_chat_page()
    assert st.session_state.current_page == "admin"
    st.rerun.assert_called()


def test_student_notice_is_unchanged(ui):
    # Guard: the student text and the Browse button stay exactly as they were.
    st, api = ui
    main.render_chat_page()
    assert "Open My Courses and join an available course to start asking questions." in _texts(st.write)
    assert "browse_courses_empty" in _button_keys(st)


def test_sidebar_hint_matches_the_role(ui):
    st, api = ui
    st.session_state.user["role"] = "Lecturer"
    main.render_sidebar()
    captions = _texts(st.caption)
    assert "Ask an administrator to add you to a course." in captions
    assert "Join a course in My Courses to view its materials." not in captions


def test_sidebar_hint_for_a_student_is_unchanged(ui):
    st, api = ui
    main.render_sidebar()
    assert "Join a course in My Courses to view its materials." in _texts(st.caption)


def test_document_manager_without_a_course_names_the_next_step(ui):
    st, api = ui
    st.session_state.user["role"] = "Lecturer"
    main.render_doc_manager_page()
    assert any("administrator" in t and "nothing to manage" in t for t in _texts(st.info))


def test_admin_pointer_does_not_name_a_heading_that_may_not_exist(ui):
    # The Admin Dashboard heading's spelling differs between releases, so the
    # notice points at the dashboard itself.
    st, api = ui
    st.session_state.user = {"role": "Admin", "name": "Test Admin", "enrolled_courses": []}
    main._render_no_courses_notice()
    assert not any("Enrol" in t or "Enroll" in t for t in _texts(st.write))


def test_admin_whose_courses_are_all_inactive_is_not_called_unassigned(ui):
    st, api = ui
    st.session_state.user = {"role": "Admin", "name": "Test Admin", "enrolled_courses": []}
    api.get_courses.return_value = [{"course_code": "OLD101", "name": "Old course", "is_active": False}]
    main.render_courses_page()
    infos = _texts(st.info)
    assert not any("not assigned" in t or "not enrolled" in t for t in infos)
    assert any("Admin Dashboard" in t for t in infos)
