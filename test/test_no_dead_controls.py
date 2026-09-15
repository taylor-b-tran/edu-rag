"""No control on screen may do nothing.

Several separate defects were the same mistake: a Streamlit widget rendered as
a bare statement, its return value dropped on the floor. The Session History
course, period and search controls filtered nothing; the Document Manager's
retry button called nothing. Each looked finished and each was inert, which is
the worst kind of defect to ship -- it cannot be seen in a screenshot.

This test reads main.py as a syntax tree and fails on any interactive widget
whose result is discarded, unless the call is explicitly exempt below.
"""
from __future__ import annotations

import ast
from pathlib import Path

MAIN = Path(__file__).resolve().parents[1] / "apps" / "streamlit" / "main.py"

# Widgets that hand back something the caller has to act on.
# download_button is deliberately absent: it performs its action by existing.
# Its return value only says whether it was clicked, and the file downloads
# either way, so discarding it is correct rather than a defect.
INTERACTIVE = {
    "button", "form_submit_button", "checkbox", "toggle",
    "radio", "selectbox", "multiselect", "slider", "select_slider",
    "number_input", "text_input", "text_area", "date_input", "time_input",
    "file_uploader", "color_picker", "camera_input",
}


def _first_literal(call: ast.Call) -> str:
    if call.args and isinstance(call.args[0], ast.Constant):
        return str(call.args[0].value)
    for kw in call.keywords:
        if kw.arg == "label" and isinstance(kw.value, ast.Constant):
            return str(kw.value.value)
    return "<dynamic>"


def _has_kw(call: ast.Call, name: str) -> bool:
    return any(kw.arg == name for kw in call.keywords)


def _is_true_kw(call: ast.Call, name: str) -> bool:
    for kw in call.keywords:
        if kw.arg == name and isinstance(kw.value, ast.Constant):
            return kw.value.value is True
    return False


def discarded_widgets():
    """Every interactive widget call used as a bare statement."""
    tree = ast.parse(MAIN.read_text(encoding="utf-8"))
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call):
            continue
        call = node.value
        if not isinstance(call.func, ast.Attribute) or call.func.attr not in INTERACTIVE:
            continue

        # A disabled control cannot be acted on, so nothing is lost by
        # ignoring what it returns -- it exists to show state.
        if _is_true_kw(call, "disabled"):
            continue
        # A value widget with a key can legitimately be read back later out of
        # st.session_state rather than from its return value. A *button* cannot:
        # its return value is the only signal that it was clicked, so a keyed
        # button whose result is dropped is always dead. The Document Manager's
        # retry button hid behind exactly this exemption.
        if (call.func.attr not in ("button", "form_submit_button")
                and _has_kw(call, "key")):
            continue

        found.append((call.func.attr, _first_literal(call), node.lineno))
    return found


def test_every_interactive_control_does_something():
    dead = discarded_widgets()
    assert not dead, "widgets rendered but never acted on: " + ", ".join(
        f"{kind}({label!r}) at main.py:{line}" for kind, label, line in dead
    )


def test_the_check_would_notice_a_dead_control():
    """Guards the guard: a test that can never fail proves nothing."""
    sample = ast.parse("import streamlit as st\nst.button('Retry')\n")
    node = next(n for n in ast.walk(sample) if isinstance(n, ast.Expr))
    assert isinstance(node.value, ast.Call)
    assert node.value.func.attr in INTERACTIVE
    assert not _has_kw(node.value, "key")
    assert not _is_true_kw(node.value, "disabled")


def test_capabilities_the_client_offers_are_reachable_from_the_ui():
    """A route and a client method with no control calling them is a feature
    that only exists in the test suite. Leaving a course and reactivating a
    course were both in this state."""
    source = MAIN.read_text(encoding="utf-8")
    for method in ("join_course", "leave_course",
                   "deactivate_course", "reactivate_course",
                   "delete_session", "delete_document"):
        assert f"api.{method}(" in source, f"nothing in main.py calls api.{method}()"
