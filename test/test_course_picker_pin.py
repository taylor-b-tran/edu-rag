"""The course picker cannot move a chat to a different course on its own.

These run the chat page through Streamlit's own test runner rather than a stand-in
for `st`, because what is under test is the widget layer itself: the value the
picker reports back on a rerun, and the callback that acts on it.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "apps" / "streamlit"
MAIN = APP / "main.py"
sys.path.insert(0, str(APP))

import api_client  # noqa: E402

# Both are in fixtures/sample_responses.json. PINNED is deliberately not the
# course the resolution rule prefers, so a fall-back is visible when it happens.
PINNED = "CSCI203"
PREFERRED = "CSIT321"

USER = {
    "id": "1",
    "name": "Student",
    "email": "student@uow.edu.au",
    "role": "Student",
    "enrolled_courses": [PREFERRED, PINNED],
}


class FixtureConfig(api_client.APIConfig):
    """Serve courses and answers from the committed fixtures, with no backend.

    `use_fixtures` is a dataclass field read from the environment when the
    module is first imported, so its default is already fixed by the time a
    test runs. The app constructs its config by name, which is what this
    replaces.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_fixtures = True


@pytest.fixture
def chat_page(monkeypatch):
    """The chat page, open on PINNED, with one empty chat and nothing sent yet."""
    monkeypatch.setattr(api_client, "APIConfig", FixtureConfig)
    at = AppTest.from_file(str(MAIN), default_timeout=60)
    state = at.session_state
    state["authenticated"] = True
    state["jwt_token"] = "fixture-mode"
    state["user"] = dict(USER)
    state["course_options"] = [PREFERRED, PINNED]
    state["course_id"] = PINNED
    state["selected_course_id"] = PINNED
    session = {
        "session_id": "abc12345",
        "backend_session_id": None,
        "title": "Welcome Chat",
        "messages": [],
        "course_id": PINNED,
        "created_at": "2026-09-18 06:40",
        "message_count": 0,
    }
    state["sessions"] = [session]
    state["active_session_id"] = "abc12345"
    # The page and the session share one list, as create_new_session leaves them.
    state["messages"] = session["messages"]
    state["current_page"] = "chat"
    state["pending_send"] = False
    state["query_state"] = None
    state["history_load_pending"] = False
    at.run()
    return at


def picker(at):
    return at.selectbox(key="selected_course_id")


def header(at):
    return next(str(c.value) for c in at.caption if "Querying" in str(c.value))


def test_the_picker_opens_on_the_course_the_page_is_using(chat_page):
    # A picker holding nothing is reported as a fresh selection on the next
    # rerun, which is what the rest of this file is about.
    assert picker(chat_page).value == PINNED
    assert PINNED in header(chat_page)


def test_an_empty_picker_value_is_not_a_course_change(chat_page):
    picker(chat_page).set_value(None)
    chat_page.run()

    assert chat_page.session_state["course_id"] == PINNED
    assert PINNED in header(chat_page)
    # No second chat: the empty value must not open one.
    assert len(chat_page.session_state["sessions"]) == 1
    assert chat_page.session_state["sessions"][0]["course_id"] == PINNED


def test_a_first_question_is_asked_of_the_course_on_screen(chat_page):
    picker(chat_page).set_value(None)
    chat_page.run()
    chat_page.chat_input[0].set_value("What is in this week's material?").run()
    for _ in range(3):
        if not chat_page.session_state["pending_send"]:
            break
        chat_page.run()

    assert chat_page.session_state["course_id"] == PINNED
    assert PINNED in header(chat_page)
    sessions = chat_page.session_state["sessions"]
    # The question belongs to the chat that was already open, not to a new one
    # started underneath it in another course.
    assert len(sessions) == 1
    assert sessions[0]["course_id"] == PINNED
    asked = [m["content"] for m in chat_page.session_state["messages"]
             if m["role"] == "user"]
    assert asked == ["What is in this week's material?"]


def test_choosing_another_course_still_opens_a_chat_in_it(chat_page):
    picker(chat_page).set_value(PREFERRED)
    chat_page.run()

    assert chat_page.session_state["course_id"] == PREFERRED
    assert PREFERRED in header(chat_page)
    sessions = chat_page.session_state["sessions"]
    assert len(sessions) == 2
    assert sessions[0]["course_id"] == PINNED      # the first chat is untouched
    assert sessions[1]["course_id"] == PREFERRED


def test_switching_after_a_question_leaves_that_conversation_alone(chat_page):
    """The switch that matters is the one made mid-conversation."""
    chat_page.chat_input[0].set_value("What is in this week's material?").run()
    for _ in range(3):
        if not chat_page.session_state["pending_send"]:
            break
        chat_page.run()
    answered = list(chat_page.session_state["messages"])
    assert answered, "the question was never answered, so the switch proves nothing"

    picker(chat_page).set_value(PREFERRED)
    chat_page.run()

    assert chat_page.session_state["course_id"] == PREFERRED
    assert PREFERRED in header(chat_page)
    sessions = chat_page.session_state["sessions"]
    assert len(sessions) == 2
    # The conversation that was open keeps its course and every message in it.
    assert sessions[0]["course_id"] == PINNED
    assert sessions[0]["messages"] == answered
    # The new one starts empty in the course that was chosen.
    assert sessions[1]["course_id"] == PREFERRED
    assert sessions[1]["messages"] == []
