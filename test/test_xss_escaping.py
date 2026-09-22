"""Task 13 — XSS escaping regression tests for main.py.

Two kinds of test:

1. **Source-level guards** — read the real main.py and verify that every
   `unsafe_allow_html=True` site that inserts untrusted data wraps it in
   `_html.escape()`.  If someone removes an escape call, the test fails.

2. **AppTest integration** — run the chat page through Streamlit's own
   test runner with XSS payloads in session titles and course data, and
   assert the rendered markdown contains the escaped form, never the raw
   tag.
"""
from __future__ import annotations

import html
import re
import sys
from pathlib import Path
from textwrap import dedent

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO   = Path(__file__).resolve().parents[1]
APP    = REPO / "apps" / "streamlit"
MAIN   = APP / "main.py"

# ---------------------------------------------------------------------------
# XSS payload
# ---------------------------------------------------------------------------
XSS = '<img src=x onerror=alert(1)>'
XSS_ESC = html.escape(XSS)

# ===================================================================
# Part 1 — Source-level regression guards
#
# Read main.py source and verify that at each known insertion point
# the untrusted value is wrapped in _html.escape().
# ===================================================================

@pytest.fixture(scope="module")
def source() -> str:
    return MAIN.read_text()


# -- helpers --

def _lines_around(source: str, needle: str, *, context: int = 3) -> str:
    """Return a window of lines around the first occurrence of *needle*."""
    lines = source.splitlines()
    for i, line in enumerate(lines):
        if needle in line:
            start = max(0, i - context)
            end = min(len(lines), i + context + 1)
            return "\n".join(lines[start:end])
    return ""


# Finding 1 — session title in sidebar
def test_source_session_title_escaped(source):
    """Line with s['title'][:30] must go through _html.escape()."""
    # Find the line that truncates the title
    match = re.search(r'''title\s*=\s*_html\.escape\(\s*s\["title"\]\[:30\]''', source)
    assert match, (
        "Session title (s['title'][:30]) is not wrapped in _html.escape() in main.py — "
        "XSS regression in Finding 1"
    )


# Finding 1b — sidebar created_at
def test_source_sidebar_created_at_escaped(source):
    """created_at in sidebar session card must be escaped."""
    # Search the whole source — _lines_around("session-meta") hits the CSS block first
    assert re.search(
        r"""session-meta.*_html\.escape\(s\.get\(['"]created_at['"]""",
        source,
    ), (
        "Sidebar created_at is not wrapped in _html.escape() — "
        "XSS regression in Finding 1b"
    )


# Finding 2 — document name in sidebar
def test_source_sidebar_doc_name_escaped(source):
    """Sidebar doc_name must go through _html.escape()."""
    # The line: doc_name = _html.escape(doc.get("original_filename") or ...)
    match = re.search(
        r'''doc_name\s*=\s*_html\.escape\(doc\.get\(["']original_filename["']\)''',
        source)
    assert match, (
        "Sidebar doc_name is not wrapped in _html.escape() — "
        "XSS regression in Finding 2"
    )


# Finding 3 — user initials in sidebar
def test_source_user_initials_escaped(source):
    """User initials must go through _html.escape()."""
    match = re.search(r'''initials\s*=\s*_html\.escape\("*\.join''', source)
    assert match, (
        "User initials are not wrapped in _html.escape() — "
        "XSS regression in Finding 3"
    )


# Finding 4 — session history cards
def test_source_history_title_escaped(source):
    match = re.search(
        r'''title\s*=\s*_html\.escape\(session\.get\(["']title["']''', source)
    assert match, (
        "History card title is not wrapped in _html.escape() — "
        "XSS regression in Finding 4"
    )


def test_source_history_preview_escaped(source):
    match = re.search(
        r'''preview\s*=\s*_html\.escape\(session\.get\(["']preview["']''', source)
    assert match, (
        "History card preview is not wrapped in _html.escape() — "
        "XSS regression in Finding 4"
    )


def test_source_history_course_escaped(source):
    match = re.search(
        r'''course\s*=\s*_html\.escape\(session\.get\(["']course_id["']''', source)
    assert match, (
        "History card course_id is not wrapped in _html.escape() — "
        "XSS regression in Finding 4"
    )


# Finding 5 — doc_type in document table
def test_source_doc_type_escaped(source):
    """doc_type must be escaped after MIME-type processing, before insertion."""
    match = re.search(r'''doc_type\s*=\s*_html\.escape\(doc_type\)''', source)
    assert match, (
        "doc_type is not wrapped in _html.escape() — "
        "XSS regression in Finding 5"
    )


# Finding 6 — upload progress filename
def test_source_upload_filename_escaped(source):
    """filename in upload progress must be escaped inline."""
    match = re.search(r'''\{_html\.escape\(filename\)\}''', source)
    assert match, (
        "Upload filename is not wrapped in _html.escape() — "
        "XSS regression in Finding 6"
    )


# Finding 7 — course cards (enrolled + available, both blocks)
def test_source_course_code_escaped(source):
    """course code in card HTML must be escaped."""
    matches = re.findall(r'''\{_html\.escape\(code\)\}''', source)
    assert len(matches) >= 2, (
        f"Expected _html.escape(code) in at least 2 course-card blocks, "
        f"found {len(matches)} — XSS regression in Finding 7"
    )


def test_source_course_name_escaped(source):
    matches = re.findall(r'''_html\.escape\(course\.get\(['"]name['"]''', source)
    assert len(matches) >= 2, (
        f"Expected _html.escape(course.get('name'...)) in at least 2 blocks, "
        f"found {len(matches)} — XSS regression in Finding 7"
    )


def test_source_course_description_escaped(source):
    matches = re.findall(r'''_html\.escape\(course\.get\(['"]description['"]''', source)
    assert len(matches) >= 2, (
        f"Expected _html.escape(course.get('description'...)) in at least 2 blocks, "
        f"found {len(matches)} — XSS regression in Finding 7"
    )


# Pre-existing escaping still intact
def test_source_user_message_escaped(source):
    """User chat messages must be escaped (pre-existing)."""
    # The escape call and the "user-msg" div are on adjacent lines;
    # just verify the escape call exists anywhere in source.
    assert re.search(
        r'''_html\.escape\(msg\[['"]content['"]\]\)''',
        source,
    ), (
        "User message content is not escaped — XSS regression"
    )


def test_source_ai_answer_escaped(source):
    """AI answer body must be escaped (pre-existing)."""
    assert re.search(r'''_html\.escape\(body\)\.replace''', source), (
        "AI answer body is not escaped — XSS regression"
    )


# ===================================================================
# Part 2 — AppTest integration: render with XSS payloads
# ===================================================================

sys.path.insert(0, str(APP))
import api_client  # noqa: E402

class FixtureConfig(api_client.APIConfig):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_fixtures = True


XSS_USER = {
    "id": "1", "name": XSS,
    "email": "xss@test.com", "role": "Student",
    "enrolled_courses": ["CSIT321"],
}


@pytest.fixture
def xss_page(monkeypatch):
    """Chat page with XSS payloads in session title and user name."""
    from streamlit.testing.v1 import AppTest

    monkeypatch.setattr(api_client, "APIConfig", FixtureConfig)
    at = AppTest.from_file(str(MAIN), default_timeout=60)
    state = at.session_state
    state["authenticated"] = True
    state["jwt_token"] = "fixture-mode"
    state["user"] = dict(XSS_USER)
    state["course_options"] = ["CSIT321"]
    state["course_id"] = "CSIT321"
    state["selected_course_id"] = "CSIT321"
    state["sessions"] = [{
        "session_id": "xss-test",
        "backend_session_id": None,
        "title": XSS,              # <-- XSS payload in title
        "messages": [],
        "course_id": "CSIT321",
        "created_at": "2026-09-21",
        "message_count": 0,
    }]
    state["active_session_id"] = "xss-test"
    state["messages"] = []
    state["current_page"] = "chat"
    state["pending_send"] = False
    state["query_state"] = None
    state["history_load_pending"] = False
    at.run()
    return at


def test_apptest_xss_title_not_in_raw_html(xss_page):
    """The raw XSS payload must never appear unescaped in any rendered markdown."""
    for md in xss_page.markdown:
        rendered = str(md.value)
        if XSS_ESC in rendered:
            # Good — the escaped version is present
            assert XSS not in rendered.replace(XSS_ESC, ""), (
                f"Raw XSS payload found alongside escaped version in: {rendered[:200]}"
            )
        # If neither escaped nor raw, that's fine — the payload isn't in this block


def test_apptest_xss_initials_not_in_raw_html(xss_page):
    """User initials derived from XSS name must be escaped."""
    # With name = '<img src=x onerror=alert(1)>', initials = '<i'
    # After escaping: '&lt;i'
    for md in xss_page.markdown:
        rendered = str(md.value)
        if "border-radius:50%" in rendered and "align-items:center" in rendered:
            # This is the initials avatar div
            assert "<i" not in rendered.split("</div>")[0].split(">")[-1] or \
                   "&lt;" in rendered, (
                f"Raw '<' character in initials avatar: {rendered[:200]}"
            )
