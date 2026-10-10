"""Tuning does not offer a setting that changes nothing.

The API stores "prompt_strategy" and reports it as in effect, but the answer
pipeline builds its strategy once at start-up and never reads the stored value.
A lecturer could change it, read "Saved. In effect for ...", and see no
difference in any answer. The control is not offered until the value reaches
the pipeline.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "streamlit"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main  # noqa: E402


class State(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


@pytest.fixture
def ui(monkeypatch):
    st = MagicMock()
    st.session_state = State(user={"role": "Lecturer", "name": "L", "enrolled_courses": ["TEST101"]},
                             course_id="TEST101", current_page="settings")
    st.button.return_value = False
    st.checkbox.return_value = False
    made = []

    def columns(spec, **kw):
        cols = [MagicMock() for _ in range(spec if isinstance(spec, int) else len(spec))]
        made.extend(cols)
        return cols

    st.columns.side_effect = columns
    st._made_columns = made
    api = MagicMock()
    api.get_course_settings.return_value = {"settings": {}, "effective": {}}
    api.get_global_settings.return_value = {"settings": {}, "known_models": []}
    monkeypatch.setattr(main, "st", st)
    monkeypatch.setattr(main, "api", api)
    return st, api


def _shown(st):
    """Every markdown string drawn on the page, in the page body or in a column."""
    calls = list(st.markdown.call_args_list)
    for col in st._made_columns:
        calls += col.markdown.call_args_list
    return " ".join(str(c.args[0]) for c in calls if c.args)


def test_the_course_settings_do_not_include_prompt_strategy():
    assert "prompt_strategy" not in main._COURSE_SCOPED_KEYS
    assert "prompt_strategy" not in main._GLOBAL_ONLY_KEYS


def test_the_course_tuning_page_has_no_prompt_strategy_control(ui):
    st, _ = ui
    main._render_course_tuning("TEST101", [], None)
    shown = _shown(st)
    assert "Top K" in shown            # the page did render its settings
    assert "Prompt Strategy" not in shown
    assert not any(c.args and c.args[0] == "Prompt strategy" for c in st.selectbox.call_args_list)


def test_the_other_course_settings_are_still_offered(ui):
    st, _ = ui
    main._render_course_tuning("TEST101", [], None)
    shown = _shown(st)
    for title in ("Top K", "Similarity Threshold", "Response Style"):
        assert title in shown
