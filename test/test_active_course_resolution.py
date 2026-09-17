"""Course selection, shared screen state and conversation ownership."""
from __future__ import annotations

import ast
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

APP = Path(__file__).resolve().parents[1] / "apps" / "streamlit"
sys.path.insert(0, str(APP))
import main  # noqa: E402


class State(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


def make_ui(monkeypatch, *, role="Student", enrolled=(), course_id=""):
    st = MagicMock()
    st.session_state = State(
        user={"role": role, "name": "T", "enrolled_courses": list(enrolled)},
        course_id=course_id, selected_course_id=course_id, current_page="chat",
        sessions=[], active_session_id=None, messages=[], session_id=None,
        course_options=list(enrolled),
        # The chat page reads these directly; State raises on a missing key.
        pending_send=False, query_state=None, response_style=None,
    )
    st.button.return_value = False
    # No typed question on these reruns. Left as a MagicMock it is truthy, and
    # the page sends a query, which is not what any test here is about.
    st.chat_input.return_value = None
    st.columns.side_effect = lambda spec, **kw: [
        MagicMock() for _ in range(spec if isinstance(spec, int) else len(spec))]
    api = MagicMock()
    api.get_courses.return_value = [
        {"course_code": "CSIT321", "name": "Project", "is_active": True},
        {"course_code": "CSCI203", "name": "Algorithms", "is_active": True},
    ]
    api.get_documents.return_value = []
    api.get_health.return_value = {}
    monkeypatch.setattr(main, "st", st)
    monkeypatch.setattr(main, "api", api)
    return st, api


def _courses_asked_for(api):
    return [c.args[0] for c in api.get_documents.call_args_list if c.args]


# --- the resolution rule itself -----------------------------------------

def test_a_stored_course_the_user_may_open_is_kept(monkeypatch):
    make_ui(monkeypatch, enrolled=["CSCI203"], course_id="CSCI203")
    assert main._active_course() == "CSCI203"


def test_a_blank_course_resolves_to_the_one_course_the_user_has(monkeypatch):
    make_ui(monkeypatch, enrolled=["CSCI203"], course_id="")
    assert main._active_course() == "CSCI203"


def test_a_stale_course_the_user_left_is_not_trusted(monkeypatch):
    """Stored CSIT321, enrolled only in CSCI203 -- e.g. after leaving a course."""
    make_ui(monkeypatch, enrolled=["CSCI203"], course_id="CSIT321")
    assert main._active_course() == "CSCI203"


def test_no_course_resolves_to_nothing_rather_than_a_default(monkeypatch):
    make_ui(monkeypatch, enrolled=[], course_id="")
    assert main._active_course() == ""


def test_the_preferred_course_still_wins_when_the_user_is_in_it(monkeypatch):
    """Preferring CSIT321 is fine -- among courses they may actually open."""
    make_ui(monkeypatch, enrolled=["CSCI203", "CSIT321"], course_id="")
    assert main._active_course() == "CSIT321"


# --- the screens ---------------------------------------------------------

def test_the_chat_page_never_asks_for_a_course_the_student_is_not_in(monkeypatch):
    st, api = make_ui(monkeypatch, enrolled=["CSCI203"], course_id="")
    main.render_chat_page()
    asked = _courses_asked_for(api)
    assert "CSIT321" not in asked, f"fell back to the demo course: {asked}"


def test_the_document_table_without_a_course_asks_for_nothing(monkeypatch):
    st, api = make_ui(monkeypatch, role="Lecturer", enrolled=[], course_id="")
    main._render_document_table()
    assert _courses_asked_for(api) == []


def test_the_document_manager_without_a_course_says_so(monkeypatch):
    st, api = make_ui(monkeypatch, role="Lecturer", enrolled=[], course_id="")
    main.render_doc_manager_page()
    assert _courses_asked_for(api) == []
    st.info.assert_called_once()


# --- enrollment and local chat lifecycle --------------------------------

def test_starting_a_chat_before_joining_then_joining_scopes_to_the_real_course(monkeypatch):
    """A local chat can acquire the course joined after its creation."""
    st, api = make_ui(monkeypatch, enrolled=[], course_id="")
    monkeypatch.setattr(main, "_remember_chat_selection", lambda: None)

    session = main.create_new_session()
    assert session["course_id"] == ""

    st.session_state.user["enrolled_courses"] = ["CSCI203"]
    st.session_state.course_options = ["CSCI203"]
    st.session_state.course_id = "CSCI203"
    main.switch_session(session["session_id"])
    assert st.session_state.course_id == "", "the blank course must survive the round trip"

    api.get_documents.reset_mock()
    main.render_chat_page()
    asked = _courses_asked_for(api)
    assert asked, "the chat page fetched nothing at all"
    assert "CSIT321" not in asked, f"scoped a CSCI203 student to CSIT321: {asked}"


def test_a_query_from_that_chat_goes_to_the_real_course(monkeypatch):
    st, api = make_ui(monkeypatch, enrolled=["CSCI203"], course_id="")
    main.get_ai_response("what is a heap")
    assert api.query.call_args.kwargs["course_id"] == "CSCI203"


# --- the class stays closed ----------------------------------------------

def test_no_module_level_course_code_is_used_as_a_fallback():
    """The preference may be read in exactly one function.

    Spelling it `or _PREFERRED_COURSE` anywhere else recreates the defect this
    file exists for, in a form that reads as harmless.
    """
    tree = ast.parse((APP / "main.py").read_text(encoding="utf-8"))
    allowed = "_preferred_from"
    offenders = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for inner in ast.walk(node):
                if isinstance(inner, ast.Name) and inner.id == "_PREFERRED_COURSE":
                    if node.name != allowed:
                        offenders.append(f"{node.name}:{inner.lineno}")
    assert not offenders, (
        "_PREFERRED_COURSE must only be read inside "
        f"{allowed}(); also read in: {offenders}")


def test_the_old_constant_has_not_come_back():
    source = (APP / "main.py").read_text(encoding="utf-8")
    assert "DEFAULT_COURSE_ID" not in source, (
        "DEFAULT_COURSE_ID is back; use _active_course() instead")


# --- resolving is not enough: the app has to agree with itself -----------

def test_reconciling_writes_the_resolved_course_back(monkeypatch):
    """Readers that take session_state raw must see what the resolvers see."""
    st, api = make_ui(monkeypatch, enrolled=["CSCI203"], course_id="")
    assert main._reconcile_active_course() == "CSCI203"
    assert st.session_state.course_id == "CSCI203"
    # Moves together, or the picker's on-change handler reads this as the
    # user selecting a new course and resets the chat.
    assert st.session_state.selected_course_id == "CSCI203"


def test_the_conversation_survives_the_first_answer(monkeypatch):
    """The rerun after an answer preserves its conversation and messages."""
    st, api = make_ui(monkeypatch, enrolled=["CSCI203"], course_id="")
    monkeypatch.setattr(main, "_remember_chat_selection", lambda: None)
    session = main.create_new_session()
    original = session["session_id"]
    st.session_state.active_session_id = original

    session["course_id"] = main._active_course()      # what _send_message does
    session["backend_session_id"] = "backend-1"
    st.session_state.session_id = "backend-1"
    st.session_state.messages = [{"role": "user", "content": "q"},
                                 {"role": "assistant", "content": "a"}]

    main.render_chat_page()

    assert st.session_state.active_session_id == original
    assert st.session_state.session_id == "backend-1"
    assert [m["content"] for m in st.session_state.messages] == ["q", "a"]


def test_a_follow_up_keeps_the_same_backend_conversation(monkeypatch):
    st, api = make_ui(monkeypatch, enrolled=["CSCI203"], course_id="")
    monkeypatch.setattr(main, "_remember_chat_selection", lambda: None)
    session = main.create_new_session()
    st.session_state.active_session_id = session["session_id"]
    session["course_id"] = main._active_course()
    session["backend_session_id"] = "backend-1"
    st.session_state.session_id = "backend-1"
    st.session_state.messages = [{"role": "user", "content": "q"}]

    main.render_chat_page()
    main.render_chat_page()      # a second rerun, as a follow-up produces

    assert st.session_state.session_id == "backend-1"
    assert st.session_state.active_session_id == session["session_id"]


def test_changing_course_still_starts_a_fresh_chat(monkeypatch):
    """The reset behaviour is deliberate -- do not let the fix above remove it.

    One backend conversation must never be rebound to another course.
    """
    st, api = make_ui(monkeypatch, enrolled=["CSCI203", "CSIT321"],
                      course_id="CSIT321")
    monkeypatch.setattr(main, "_remember_chat_selection", lambda: None)
    session = main.create_new_session()
    st.session_state.active_session_id = session["session_id"]
    session["course_id"] = "CSCI203"          # chat belongs to the other course
    session["backend_session_id"] = "backend-1"

    main.render_chat_page()

    assert st.session_state.active_session_id != session["session_id"], (
        "a chat from another course was kept when the course changed")


def test_materials_asks_for_the_course_the_student_joined(monkeypatch):
    st, api = make_ui(monkeypatch, enrolled=["CSCI203"], course_id="")
    main.render_uploads_page()
    assert _courses_asked_for(api) == ["CSCI203"]


def test_the_sidebar_agrees_with_the_chat_header(monkeypatch):
    """The sidebar uses the same available course as the chat header."""
    st, api = make_ui(monkeypatch, enrolled=["CSCI203"], course_id="")
    main.render_sidebar()
    assert _courses_asked_for(api) == ["CSCI203"]


@pytest.mark.parametrize("role", ["Student", "Lecturer", "Admin"])
def test_an_uncached_available_course_is_kept(monkeypatch, role):
    st, api = make_ui(monkeypatch, role=role, enrolled=["CSCI203", "NEW101"],
                      course_id="NEW101")
    st.session_state.course_options = ["CSCI203"]
    api.get_courses.return_value.append(
        {"course_code": "NEW101", "name": "New course", "is_active": True})

    assert main._reconcile_active_course() == "NEW101"
    assert "NEW101" in st.session_state.course_options
    assert st.session_state.course_id == "NEW101"


def test_failed_refresh_preserves_selection_without_caching_failure(monkeypatch):
    st, api = make_ui(monkeypatch, enrolled=["CSCI203"], course_id="NEW101")
    api.get_courses.side_effect = RuntimeError("Courses unavailable")

    assert main._active_course() == "NEW101"
    assert st.session_state.course_options == ["CSCI203"]


def test_persisted_chat_without_course_is_not_rebound(monkeypatch):
    st, api = make_ui(monkeypatch, enrolled=["CSCI203"])
    monkeypatch.setattr(main, "_remember_chat_selection", lambda: None)
    original = main.create_new_session()
    original["backend_session_id"] = "legacy-backend"
    original["messages"] = [{"role": "user", "content": "Existing question"}]
    main.switch_session(original["session_id"])

    main.render_chat_page()
    main.get_ai_response("New question")

    assert original["course_id"] == ""
    assert original["backend_session_id"] == "legacy-backend"
    assert original["messages"][0]["content"] == "Existing question"
    assert st.session_state.active_session_id != original["session_id"]
    assert main.get_active_session()["course_id"] == "CSCI203"
    assert api.query.call_args.kwargs["session_id"] is None
    st.info.assert_called_once()


def test_app_reconciles_before_sidebar_and_page(monkeypatch):
    st, api = make_ui(monkeypatch, enrolled=["CSCI203"])
    st.session_state.authenticated = True
    events = []
    reconcile = main._reconcile_active_course

    def record_reconcile():
        events.append("reconcile")
        return reconcile()

    def record_render(name):
        def render():
            assert st.session_state.course_id == "CSCI203"
            assert st.session_state.selected_course_id == "CSCI203"
            events.append(name)
        return render

    monkeypatch.setattr(main, "_reconcile_active_course", record_reconcile)
    monkeypatch.setattr(main, "render_sidebar", record_render("sidebar"))
    monkeypatch.setattr(main, "render_chat_page", record_render("page"))

    main._render_app()

    assert events == ["reconcile", "sidebar", "page"]


def test_course_transition_notice_survives_rerun_until_dismissed(monkeypatch):
    st, api = make_ui(monkeypatch, enrolled=["CSCI203"], course_id="CSCI203")
    monkeypatch.setattr(main, "_remember_chat_selection", lambda: None)
    original = main.create_new_session()
    original["course_id"] = ""
    original["backend_session_id"] = "legacy-backend"

    main.render_chat_page()
    replacement = main.get_active_session()
    assert replacement["course_transition_notice"] is True
    st.info.reset_mock()

    main.render_chat_page()
    st.info.assert_called_once()
    assert main.get_active_session() is replacement

    st.button.side_effect = lambda *args, **kwargs: kwargs.get("key") == "dismiss_course_transition"
    main.render_chat_page()
    assert replacement["course_transition_notice"] is False
    st.button.side_effect = None
    st.button.return_value = False
    st.info.reset_mock()
    main.render_chat_page()
    st.info.assert_not_called()


def test_transition_notice_exists_before_url_update(monkeypatch):
    st, api = make_ui(monkeypatch, enrolled=["CSCI203"], course_id="CSCI203")

    def check_notice():
        session = main.get_active_session()
        assert session["course_transition_notice"] is True

    monkeypatch.setattr(main, "_remember_chat_selection", check_notice)
    main.create_new_session(course_transition=True)
