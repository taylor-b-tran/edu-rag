"""Nothing that cannot be clicked may look clickable.

A source chip is a label, and a sidebar chat card is a block of text above a
real "Switch" button. Both used to carry `cursor: pointer` and a hover
highlight, so the pointer turned into a hand over something that did nothing
when pressed, which reads as a broken control.

These are source-level guards in the style of test_xss_escaping.py: they read
the CSS and the markup in main.py.
"""
from __future__ import annotations

import re
from pathlib import Path

MAIN = Path(__file__).resolve().parents[1] / "apps" / "streamlit" / "main.py"
SRC = MAIN.read_text(encoding="utf-8")


def _rule(selector: str) -> str:
    match = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", SRC)
    assert match, f"CSS rule {selector} not found in main.py"
    return match.group(1)


def test_source_chips_do_not_look_clickable():
    assert "cursor: pointer" not in _rule(".source-chip")
    assert ".source-chip:hover" not in SRC


def test_session_cards_do_not_look_clickable():
    assert "cursor: pointer" not in _rule(".session-card")
    assert ".session-card:hover" not in SRC


def test_source_chips_are_still_numbered_spans():
    # Guards against "fixing" the affordance by removing the chips.
    assert '<span class="source-chip">' in SRC
    assert "[S{position}]" in SRC


def test_session_cards_are_still_rendered_with_a_switch_button():
    # Guards against "fixing" the affordance by removing the card or its button.
    assert "session-card session-card-active" in SRC
    assert 'key=f"switch_{s[\'session_id\']}"' in SRC
