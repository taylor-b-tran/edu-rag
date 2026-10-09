"""A new question scrolls the chat to its latest message.

Streamlit keeps a chat pinned to the bottom only while the reader is already
at the bottom. A reader who had scrolled up to re-read an answer, then asked
the next question, stayed at the top: the new question and the "Generating
response..." line were off screen, and the finished answer too, so the page
looked frozen on the previous answer.

So the chat scrolls to its end twice per question: before the model is called,
so the question and the waiting line are on screen, and when the answer has
been drawn. The script finds the scrolling element by the class `stMain`,
which is on the page whether or not it also carries the chat's own test id.
"""
import re
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "streamlit"))
import main

MAIN_SRC = (Path(__file__).resolve().parents[1] / "apps" / "streamlit" / "main.py").read_text(encoding="utf-8")


class State(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


@pytest.fixture
def ui(monkeypatch):
    st = MagicMock()
    session = {"session_id": "s1", "backend_session_id": None, "title": "Chat", "messages": [],
               "course_id": "TEST101", "created_at": "2026-10-08 10:00", "message_count": 0}
    st.session_state = State(user={"role": "Student", "name": "Test Student", "enrolled_courses": ["TEST101"]},
                             course_id="TEST101", course_options=["TEST101"], selected_course_id="TEST101",
                             current_page="chat", sessions=[session], active_session_id="s1",
                             messages=session["messages"], pending_send=False, query_state=None,
                             response_styles_cache={"styles": []}, response_style=None)
    st.button.return_value = False
    st.chat_input.return_value = None
    st.columns.side_effect = lambda spec, **kwargs: [MagicMock() for _ in range(spec if isinstance(spec, int) else len(spec))]
    api = MagicMock()
    api.get_courses.return_value = [{"course_code": "TEST101", "name": "Test course", "is_active": True}]
    api.get_documents.return_value = []
    api.is_live = True
    events = []
    components = MagicMock()
    components.html.side_effect = lambda *a, **k: events.append(("scroll", a, k))
    monkeypatch.setattr(main, "st", st)
    monkeypatch.setattr(main, "api", api)
    monkeypatch.setattr(main, "components", components)
    monkeypatch.setattr(main, "_remember_chat_selection", lambda: None)
    monkeypatch.setattr(main, "_send_message", lambda text, append_user=True: events.append(("send", text)))
    return st, api, events, components


def _scrolls(events):
    return [e for e in events if e[0] == "scroll"]


def test_the_helper_emits_a_script_that_scrolls_the_main_container(ui):
    st, api, events, components = ui
    main._scroll_to_latest()
    main._scroll_to_latest()
    first, second = (e[1][0] for e in _scrolls(events))
    assert "section.stMain" in first and "scrollTo" in first and "scrollHeight" in first
    assert _scrolls(events)[0][2].get("height") == 0
    assert first != second, "an identical element would not run its script again"


def test_the_script_cannot_break_the_page_if_the_parent_is_unreachable(ui):
    st, api, events, components = ui
    main._scroll_to_latest()
    script = _scrolls(events)[0][1][0]
    assert "try" in script and "catch" in script


def test_a_pending_question_scrolls_before_the_model_is_called(ui):
    st, api, events, components = ui
    st.session_state.messages.append({"role": "user", "content": "What is x?", "timestamp": "10:00 AM"})
    st.session_state.pending_send = True
    st.session_state.query_state = "What is x?"
    main.render_chat_page()
    order = [e[0] for e in events]
    assert "send" in order and "scroll" in order
    assert order.index("scroll") < order.index("send")


def test_the_answer_run_scrolls_once_and_only_once(ui):
    st, api, events, components = ui
    st.session_state.messages.append({"role": "user", "content": "What is x?", "timestamp": "10:00 AM"})
    st.session_state.messages.append({"role": "assistant", "content": "x is y", "timestamp": "10:00 AM"})
    st.session_state.scroll_after_answer = True
    main.render_chat_page()
    assert len(_scrolls(events)) == 1
    assert not st.session_state.get("scroll_after_answer")
    main.render_chat_page()
    assert len(_scrolls(events)) == 1, "the flag is spent after one scroll"


class Rerun(Exception):
    """Streamlit's st.rerun() stops the script run by raising; so does this stand-in."""


def test_finishing_an_answer_asks_for_the_scroll_on_the_next_run(ui):
    st, api, events, components = ui
    st.rerun.side_effect = Rerun
    st.session_state.pending_send = True
    st.session_state.query_state = "What is x?"
    with pytest.raises(Rerun):
        main.render_chat_page()
    assert st.session_state.scroll_after_answer is True
    # Only the pre-model scroll has happened in this run; the answer scroll is for the next one.
    assert len(_scrolls(events)) == 1


def test_an_idle_page_never_scrolls(ui):
    st, api, events, components = ui
    st.session_state.messages.append({"role": "user", "content": "What is x?", "timestamp": "10:00 AM"})
    main.render_chat_page()
    assert _scrolls(events) == []


def test_the_scroll_call_comes_after_the_waiting_line_in_the_source():
    block = MAIN_SRC[MAIN_SRC.index("if st.session_state.pending_send:"):]
    waiting = block.index("Generating response")
    scroll = block.index("_scroll_to_latest()")
    send = block.index("_send_message(pending_query")
    assert waiting < scroll < send


def test_the_request_is_spent_even_when_the_run_leaves_early(ui):
    st, api, events, components = ui
    st.session_state.scroll_after_answer = True
    st.session_state.user = {"role": "Student", "name": "Test Student", "enrolled_courses": []}
    st.session_state.course_options = []
    main.render_chat_page()
    assert not st.session_state.get("scroll_after_answer")
    assert _scrolls(events) == []
