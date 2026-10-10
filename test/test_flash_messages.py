"""Confirmations and upload results stay on screen after the page redraws.

st.rerun() stops the running script at once and the next run draws the page
from scratch, so an st.success() or st.error() drawn just before it is gone
before anyone can read it. Join, Leave, Create course, Tuning save and every
upload result had this. They now queue the message with _flash(), and the next
run shows it once, next to the control that was used.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "streamlit"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main  # noqa: E402


class State(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


class _Rerun(Exception):
    """st.rerun() stops the run; the tests need it to do the same."""


@pytest.fixture
def ui(monkeypatch):
    st = MagicMock()
    st.session_state = State(user={"role": "Student", "name": "Test Student", "enrolled_courses": []},
                             course_id="", current_page="chat", sessions=[], active_session_id=None)
    st.button.return_value = False
    st.rerun.side_effect = _Rerun
    st.columns.side_effect = lambda spec, **kw: [MagicMock() for _ in range(spec if isinstance(spec, int) else len(spec))]
    api = MagicMock()
    api.get_courses.return_value = [{"course_code": "TEST101", "name": "Test course", "is_active": True}]
    api.get_health.return_value = {}
    monkeypatch.setattr(main, "st", st)
    monkeypatch.setattr(main, "api", api)
    return st, api


def _queued(st, slot):
    return [(level, text) for level, text, *_ in st.session_state[main._FLASH_KEY][slot]]


def test_a_flash_is_shown_on_the_next_run(ui):
    st, _ = ui
    main._flash("Saved.")
    main._show_flashes()
    st.success.assert_called_once_with("Saved.")


def test_a_flash_survives_the_extra_runs_streamlit_starts_after_a_rerun(ui):
    st, _ = ui
    main._flash("Saved.")
    for _ in range(3):
        main._show_flashes()
        main._forget_flashes()
    assert st.success.call_count == 3


def test_a_flash_expires(ui, monkeypatch):
    st, _ = ui
    main._flash("Saved.")
    real = main.time.time()
    monkeypatch.setattr(main.time, "time", lambda: real + main._FLASH_SECONDS + 1)
    main._show_flashes()
    st.success.assert_not_called()
    main._forget_flashes()
    assert main._FLASH_KEY not in st.session_state


def test_a_flash_does_not_follow_the_reader_to_another_page(ui):
    st, _ = ui
    st.session_state.current_page = "courses"
    main._flash("Saved.")
    st.session_state.current_page = "history"
    main._show_flashes()
    st.success.assert_not_called()
    main._forget_flashes()
    st.session_state.current_page = "courses"
    main._show_flashes()
    st.success.assert_not_called()


def test_a_flash_waits_for_its_own_slot(ui):
    st, _ = ui
    main._flash("A", "success", "upload")
    main._show_flashes()
    st.success.assert_not_called()
    main._show_flashes("upload")
    st.success.assert_called_once_with("A")


def test_the_level_chooses_the_alert(ui):
    st, _ = ui
    main._flash("x", "error")
    main._flash("y", "warning")
    main._flash("z", "nonsense")
    main._show_flashes()
    st.error.assert_called_once_with("x")
    st.warning.assert_called_once_with("y")
    st.info.assert_called_once_with("z")


def test_signing_out_drops_queued_messages(ui):
    st, _ = ui
    main._flash("left over")
    main._clear_identity_state()
    assert main._FLASH_KEY not in st.session_state


def test_join_confirmation_is_queued_before_the_rerun(ui):
    st, api = ui
    st.button.side_effect = lambda *a, **kw: kw.get("key") == "join_TEST101"
    api.join_course.return_value = {"success": True, "enrolled_courses": ["TEST101"]}
    with pytest.raises(_Rerun):
        main.render_courses_page()
    assert _queued(st, "page") == [("success", "Enrolled in TEST101!")]
    st.success.assert_not_called()


def test_leave_confirmation_is_queued_before_the_rerun(ui):
    st, api = ui
    st.session_state.user["enrolled_courses"] = ["TEST101"]
    st.session_state.course_options = ["TEST101"]
    st.session_state.course_id = "TEST101"
    st.session_state.confirm_leave = "TEST101"
    st.button.side_effect = lambda *a, **kw: kw.get("key") == "leave_yes_TEST101"
    api.leave_course.return_value = {"success": True, "enrolled_courses": []}
    with pytest.raises(_Rerun):
        main.render_courses_page()
    assert ("success", "Left TEST101.") in _queued(st, "page")
    st.success.assert_not_called()


def test_create_course_confirmation_is_queued_before_the_rerun(ui, monkeypatch):
    st, api = ui
    st.form_submit_button.return_value = True
    st.text_area.return_value = ""
    cols = [MagicMock(), MagicMock()]
    cols[0].text_input.return_value = "csit330"
    cols[1].text_input.return_value = "Software Testing"
    st.columns.side_effect = lambda spec, **kw: (
        cols if spec == 2 else [MagicMock() for _ in range(spec if isinstance(spec, int) else len(spec))])
    api.create_course.return_value = {"success": True}
    monkeypatch.setattr(main, "_refresh_course_options", lambda *a, **k: None)
    with pytest.raises(_Rerun):
        main.render_course_management()
    assert _queued(st, "page") == [("success", "Created CSIT330.")]


def test_course_tuning_save_is_queued_for_its_own_slot(ui):
    st, api = ui
    api.get_course_settings.return_value = {"settings": {}, "effective": {}}
    api.get_global_settings.return_value = {"settings": {}}
    api.update_course_settings.return_value = {"success": True}
    st.checkbox.return_value = True
    st.button.side_effect = lambda *a, **kw: kw.get("key") == "save_TEST101"
    with pytest.raises(_Rerun):
        main._render_course_tuning("TEST101", [], None)
    queued = _queued(st, "tuning_TEST101")
    assert len(queued) == 1 and queued[0][0] == "success"
    assert queued[0][1].startswith("Saved. In effect for TEST101")


def test_global_tuning_save_is_queued_for_its_own_slot(ui):
    st, api = ui
    api.get_global_settings.return_value = {"settings": {}, "known_models": []}
    api.update_global_settings.return_value = {"success": True}
    st.checkbox.return_value = True
    st.button.side_effect = lambda *a, **kw: kw.get("key") == "save_global"
    with pytest.raises(_Rerun):
        main._render_global_tuning([])
    queued = _queued(st, "tuning_global")
    assert queued == [("success", "Saved. Applies to every course from the next question.")]


class _Upload:
    def __init__(self, name, data):
        self.name = name
        self._data = data

    def getvalue(self):
        return self._data


@pytest.mark.parametrize("data, upload_result, status_result, level, fragment", [
    (b"", None, None, "error", "empty"),
    (b"x", {"success": False, "error": "unsupported file type"}, None, "error", "Upload failed"),
    (b"x", {"success": True, "job_id": "j1"}, {"status": "completed"}, "success", "indexed successfully"),
    (b"x", {"success": True, "job_id": "j1"}, {"status": "failed", "error": "no text"}, "error", "Indexing failed"),
    (b"x", {"success": True, "job_id": "j1"}, {"status": "unavailable"}, "warning", "could not be confirmed"),
])
def test_upload_outcomes_are_queued_for_the_upload_slot(ui, data, upload_result, status_result, level, fragment):
    st, api = ui
    api.upload_document.return_value = upload_result
    api.get_indexing_status.return_value = status_result
    main._run_real_upload_and_indexing(_Upload("week1.pdf", data), "TEST101")
    queued = _queued(st, "upload")
    assert len(queued) == 1
    assert queued[0][0] == level and fragment in queued[0][1]


def test_upload_flash_is_shown_below_the_uploader(ui, monkeypatch):
    st, api = ui
    st.session_state.user["role"] = "Lecturer"
    st.session_state.user["enrolled_courses"] = ["TEST101"]
    st.session_state.course_options = ["TEST101"]
    st.session_state.course_id = "TEST101"
    st.session_state.current_page = "doc_manager"
    st.session_state[main._FLASH_KEY] = {"upload": [("success", "done", main.time.time(), "doc_manager")]}
    st.file_uploader.return_value = []
    st.selectbox.return_value = "TEST101"
    monkeypatch.setattr(main, "_render_document_table", lambda *a, **k: None)
    main.render_doc_manager_page()
    st.success.assert_called_once_with("done")
