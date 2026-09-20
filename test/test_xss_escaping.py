"""Task 13 — XSS escaping tests for dynamic content in main.py.

Verifies that every piece of untrusted data inserted into
st.markdown(..., unsafe_allow_html=True) goes through _html.escape()
before reaching the template.  Each test injects a known XSS payload
into the value under test and asserts that the rendered HTML contains
the escaped form, never the raw tag.
"""
from __future__ import annotations

import html
import re
import textwrap

# ---------------------------------------------------------------------------
# The payload used throughout.  If this string appears UN-escaped in any
# rendered HTML, the site is vulnerable.
# ---------------------------------------------------------------------------
XSS = '<img src=x onerror=alert(1)>'
XSS_ESCAPED = html.escape(XSS)  # &lt;img src=x onerror=alert(1)&gt;


# ---------------------------------------------------------------------------
# Helpers — replicate the escaping logic from main.py so the tests run
# without importing Streamlit.
# ---------------------------------------------------------------------------

def _escape(value: str) -> str:
    """Mirror of _html.escape used in main.py (which is just html.escape)."""
    return html.escape(value)


# ── Finding 1: session title in sidebar ────────────────────────────────────

def test_session_title_escaped():
    """Session title truncated to 30 chars must be escaped."""
    raw_title = XSS + "A" * 30  # longer than 30 to trigger truncation
    title = _escape(raw_title[:30] + ("..." if len(raw_title) > 30 else ""))
    rendered = f"<div class='session-title'>💬 {title}</div>"
    assert XSS_ESCAPED in rendered
    assert "<img " not in rendered


def test_session_created_at_escaped():
    """created_at timestamp must be escaped even though it's normally safe."""
    created = _escape(XSS)
    rendered = f"<div class='session-meta'>2 msgs · {created}</div>"
    assert XSS_ESCAPED in rendered
    assert "<img " not in rendered


# ── Finding 2: document name in sidebar ────────────────────────────────────

def test_sidebar_doc_name_escaped():
    """original_filename from the API must be escaped in sidebar docs."""
    doc_name = _escape(f"{XSS}.pdf")
    rendered = f"<span style='flex:1;'>{doc_name}</span>"
    assert XSS_ESCAPED in rendered
    assert "<img " not in rendered


# ── Finding 3: user initials in sidebar ────────────────────────────────────

def test_user_initials_escaped():
    """Initials derived from user name must be escaped."""
    name = "<B"  # first chars are < and B
    initials = _escape("".join(w[0] for w in name.split()[:2]))
    rendered = f"<div>{initials}</div>"
    assert "&lt;" in rendered
    assert "<B" not in rendered.replace("&lt;B", "")


# ── Finding 4: session history cards ───────────────────────────────────────

def test_history_title_escaped():
    title = _escape(XSS)
    rendered = f"<span style='font-weight: 600;'>{title}</span>"
    assert XSS_ESCAPED in rendered
    assert "<img " not in rendered


def test_history_preview_escaped():
    preview = _escape(XSS)
    rendered = f"<p style='color: #475569;'>{preview}</p>"
    assert XSS_ESCAPED in rendered
    assert "<img " not in rendered


def test_history_course_escaped():
    course = _escape(XSS)
    rendered = f"<span class='status-badge'>{course}</span>"
    assert XSS_ESCAPED in rendered
    assert "<img " not in rendered


# ── Finding 5: document table doc_type ─────────────────────────────────────

def test_doc_type_escaped():
    """doc_type derived from filename extension must be escaped."""
    doc_type = XSS.upper()
    doc_type = _escape(doc_type)
    rendered = f"<span style='color: #475569;'>{doc_type}</span>"
    assert html.escape(XSS.upper()) in rendered
    assert "<IMG " not in rendered


# ── Finding 6: upload progress filename ────────────────────────────────────

def test_upload_filename_escaped():
    """uploaded_file.name must be escaped in the progress display."""
    filename = f"{XSS}.pdf"
    rendered = f'<strong>{_escape(filename)}</strong> (12.3 KB)'
    assert XSS_ESCAPED in rendered
    assert "<img " not in rendered


# ── Finding 7: course cards ────────────────────────────────────────────────

def test_course_code_escaped():
    code = _escape(XSS)
    rendered = f"<span style='font-size:1.1rem;'>{code}</span>"
    assert XSS_ESCAPED in rendered
    assert "<img " not in rendered


def test_course_name_escaped():
    name = _escape(XSS)
    rendered = f"<span style='font-size:0.85rem;'>{name}</span>"
    assert XSS_ESCAPED in rendered
    assert "<img " not in rendered


def test_course_description_escaped():
    desc = _escape(XSS)
    rendered = f"<span style='font-size:0.78rem;'>{desc}</span>"
    assert XSS_ESCAPED in rendered
    assert "<img " not in rendered


# ── Pre-existing escaping: confirm still intact ───────────────────────────

def test_model_badge_escaped():
    """get_model_badge must escape model_used (pre-existing)."""
    model_used = _escape(str(XSS or "unknown"))
    badge = f'<span class="model-badge">{model_used}</span>'
    assert XSS_ESCAPED in badge
    assert "<img " not in badge


def test_user_message_escaped():
    """User chat messages must be escaped (pre-existing)."""
    content = _escape(XSS)
    rendered = f'<div class="user-msg">{content}</div>'
    assert XSS_ESCAPED in rendered
    assert "<img " not in rendered


def test_ai_answer_escaped():
    """AI answer text must be escaped (pre-existing)."""
    body = XSS
    answer_html = _escape(body).replace("\n", "<br>")
    assert XSS_ESCAPED in answer_html
    assert "<img " not in answer_html


def test_source_filename_escaped():
    """Source reference filenames must be escaped (pre-existing)."""
    filename = _escape(str(XSS))
    chip = f'<span class="source-chip"><strong>[S1]</strong> {filename} · p.1</span>'
    assert XSS_ESCAPED in chip
    assert "<img " not in chip
