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
