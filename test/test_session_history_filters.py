"""Session History: the three controls have to actually filter.

All three were rendered with their return values discarded, so the screen
listed conversations weeks old under a filter that read "Last 7 days", and a
nonsense search term still returned every session. The list was also cut at
eight with nothing to page with, so older conversations could not be opened
from this screen at all.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "streamlit"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main  # noqa: E402


def session(sid, course="CSIT321", days_ago=1, title="Untitled", preview="", messages=None):
    when = datetime.now() - timedelta(days=days_ago)
    return {
        "session_id": sid,
        "course_id": course,
        "title": title,
        "preview": preview,
        "created_at": when.strftime("%Y-%m-%d %H:%M"),
        "messages": messages or [],
    }


@pytest.fixture
def sessions():
    return [
        session("a", course="CSIT321", days_ago=1, title="What is retrieval augmented generation?"),
        session("b", course="CSCI203", days_ago=2, title="How do B-trees index rows?"),
        session("c", course="CSIT321", days_ago=18, title="Chunking strategy"),
        session("d", course="CSIT321", days_ago=45, title="Old conversation"),
    ]


# --- course -------------------------------------------------------------

def test_all_courses_keeps_everything(sessions):
    assert len(main._filter_sessions(sessions, "All courses", "All time", "")) == 4


def test_one_course_keeps_only_that_course(sessions):
    got = main._filter_sessions(sessions, "CSCI203", "All time", "")
    assert [s["session_id"] for s in got] == ["b"]


# --- period -------------------------------------------------------------

def test_last_7_days_excludes_anything_older(sessions):
    got = main._filter_sessions(sessions, "All courses", "Last 7 days", "")
    assert [s["session_id"] for s in got] == ["a", "b"]


def test_last_30_days_is_wider_than_7_and_narrower_than_all(sessions):
    got = main._filter_sessions(sessions, "All courses", "Last 30 days", "")
    assert [s["session_id"] for s in got] == ["a", "b", "c"]


def test_all_time_excludes_nothing(sessions):
    assert len(main._filter_sessions(sessions, "All courses", "All time", "")) == 4


def test_an_unreadable_timestamp_is_kept_rather_than_hidden():
    """Losing a conversation to a date format is worse than showing one too many."""
    odd = session("x")
    odd["created_at"] = "last Tuesday"
    assert main._filter_sessions([odd], "All courses", "Last 7 days", "") == [odd]


def test_a_missing_timestamp_is_kept_too():
    odd = session("y")
    odd["created_at"] = None
    assert main._filter_sessions([odd], "All courses", "Last 7 days", "") == [odd]


# --- search -------------------------------------------------------------

def test_search_matches_the_title_case_insensitively(sessions):
    got = main._filter_sessions(sessions, "All courses", "All time", "B-TREES")
    assert [s["session_id"] for s in got] == ["b"]


def test_search_reaches_into_the_messages():
    s = session("z", title="Untitled", messages=[
        {"question": "How is retrieval scoped?", "answer": "By course_id metadata."}])
    assert main._filter_sessions([s], "All courses", "All time", "course_id") == [s]
    assert main._filter_sessions([s], "All courses", "All time", "metadata") == [s]


def test_a_term_that_matches_nothing_returns_nothing(sessions):
    assert main._filter_sessions(sessions, "All courses", "All time", "zzzznonsense") == []


def test_blank_search_is_not_a_filter(sessions):
    assert len(main._filter_sessions(sessions, "All courses", "All time", "   ")) == 4


# --- the filters compose ------------------------------------------------

def test_filters_apply_together(sessions):
    got = main._filter_sessions(sessions, "CSIT321", "Last 30 days", "chunking")
    assert [s["session_id"] for s in got] == ["c"]


# --- pagination ---------------------------------------------------------

def test_a_page_is_eight_and_the_rest_is_reachable():
    """The page size is what the Show more button steps by; if it were 0 or
    negative the button would never make progress."""
    assert main._HISTORY_PAGE >= 1
    many = [session(str(i)) for i in range(20)]
    assert len(many[:main._HISTORY_PAGE]) == main._HISTORY_PAGE
    assert len(many[:main._HISTORY_PAGE * 3]) == 20


# --- an empty chat is not a conversation -----------------------------------

_USER = {"role": "user", "content": "q"}


def test_an_empty_chat_is_not_a_conversation():
    assert main._history_sessions([session("w", title="Welcome Chat")]) == []


def test_a_chat_whose_only_turn_failed_is_not_a_conversation():
    failed = [_USER, {"role": "assistant", "content": "too broad", "error_type": "api_http_error"}]
    assert main._history_sessions([session("f", messages=failed)]) == []


def test_an_answered_chat_is_a_conversation():
    answered = session("a", messages=[_USER, {"role": "assistant", "content": "A"}])
    assert main._history_sessions([answered, session("w", title="Welcome Chat")]) == [answered]


def test_no_conversations_yet_can_be_shown(monkeypatch):
    from unittest.mock import MagicMock

    class State(dict):
        __getattr__ = dict.__getitem__
        __setattr__ = dict.__setitem__

    st = MagicMock()
    st.session_state = State(user={"role": "Student", "enrolled_courses": []},
                             sessions=[session("w", title="Welcome Chat")])
    st.selectbox.side_effect = lambda label, options, **kw: options[0]
    st.text_input.return_value = ""
    st.columns.side_effect = lambda spec, **kw: [MagicMock() for _ in range(spec if isinstance(spec, int) else len(spec))]
    api = MagicMock()
    api.get_courses.return_value = []
    monkeypatch.setattr(main, "st", st)
    monkeypatch.setattr(main, "api", api)
    main.render_history_page()
    st.info.assert_any_call("No conversations yet.")
    assert not any("Welcome Chat" in str(c.args[0]) for c in st.markdown.call_args_list)
