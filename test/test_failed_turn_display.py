"""A turn the server refused is not shown as a saved message, and does not name the chat.

A 422 (question too broad) or a 503 (generation unavailable) stores nothing on
the server, but the UI still appended the failed turn, so the sidebar read
"2 msgs" and the chat took the failed question as its name. After a reload the
conversation was gone. The fallback banner also ran into the first words of the
answer because it was drawn as an inline box.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "streamlit"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main  # noqa: E402
from test.test_t914_reload import ui as reload_ui  # noqa: E402,F401

USER = {"role": "user", "content": "q"}
GOOD = {"role": "assistant", "content": "answer"}
FAILED = {"role": "assistant", "content": "too broad", "error_type": "api_http_error"}


def test_fallback_banner_is_a_block_of_its_own():
    src = Path(main.__file__).read_text(encoding="utf-8")
    rule = re.search(r"\.fallback-label\s*\{([^}]*)\}", src).group(1)
    assert "inline" not in rule
    assert "display: flex" in rule


@pytest.mark.parametrize("messages, expected", [
    ([], 0),
    (None, 0),
    ([USER, GOOD], 2),
    ([USER, FAILED], 0),
    ([USER, GOOD, USER, FAILED], 2),
])
def test_saved_count_ignores_a_failed_turn(messages, expected):
    assert main._saved_message_count(messages) == expected


def test_sidebar_counts_only_saved_messages(monkeypatch):
    st = MagicMock()
    st.session_state = {"user": {"role": "Student", "name": "T", "enrolled_courses": []},
                        "course_id": "", "current_page": "chat", "active_session_id": "s1",
                        "sessions": [{"session_id": "s1", "title": "New Chat", "created_at": "2026-10-09 10:00",
                                      "messages": [USER, FAILED]}]}

    class State(dict):
        __getattr__ = dict.__getitem__
        __setattr__ = dict.__setitem__

    st.session_state = State(st.session_state)
    st.button.return_value = False
    st.columns.side_effect = lambda spec, **kw: [MagicMock() for _ in range(spec if isinstance(spec, int) else len(spec))]
    api = MagicMock()
    api.get_courses.return_value = []
    api.get_health.return_value = {}
    monkeypatch.setattr(main, "st", st)
    monkeypatch.setattr(main, "api", api)
    main.render_sidebar()
    cards = [c.args[0] for c in st.markdown.call_args_list if "session-meta" in str(c.args[0])]
    assert cards and ">0 msgs" in cards[0]


def test_a_failed_first_question_does_not_name_the_chat(reload_ui, monkeypatch):
    ui = reload_ui
    monkeypatch.setattr(ui, "get_ai_response", lambda text: {
        "answer": "Your question is too broad...", "error_type": "api_http_error", "status_code": 422})
    ui.create_new_session()
    ui._submit_query("help")
    ui._send_message("help", append_user=False)
    assert ui.get_active_session()["title"] == "New Chat"


def test_the_first_answered_question_names_the_chat(reload_ui, monkeypatch):
    ui = reload_ui
    monkeypatch.setattr(ui, "get_ai_response", lambda text: {
        "answer": "Your question is too broad...", "error_type": "api_http_error", "status_code": 422})
    ui.create_new_session()
    ui._submit_query("help")
    ui._send_message("help", append_user=False)
    monkeypatch.setattr(ui, "get_ai_response", lambda text: {"answer": "RAG retrieves...", "from_api": True})
    ui._submit_query("What is retrieval augmented generation?")
    ui._send_message("What is retrieval augmented generation?", append_user=False)
    assert ui.get_active_session()["title"] == "What is retrieval augmented generation?"
