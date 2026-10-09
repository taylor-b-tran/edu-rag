"""The sidebar's "Loaded Documents" list must be complete, readable and honest.

It used to show only the first five documents while the line under it said
"10 docs loaded", and a long file name was cut off at the card edge with no
sign that it continued. Now: names end in an ellipsis with
the full name on hover, five documents show by default, and a button shows the
rest. `st.expander` is avoided on purpose: its arrow glyph depends on a web
font that does not load everywhere.
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


def _docs(n, name="Lecture {i}.pdf"):
    return [{"document_id": f"d{i}", "original_filename": name.format(i=i),
             "status": "indexed", "chunks": 10} for i in range(1, n + 1)]


@pytest.fixture
def ui(monkeypatch):
    st = MagicMock()
    st.session_state = State(user={"role": "Student", "name": "Test Student",
                                   "enrolled_courses": ["TEST101"]},
                             course_id="TEST101", course_options=["TEST101"],
                             current_page="chat", sessions=[], active_session_id=None)
    st.button.return_value = False
    st.columns.side_effect = lambda spec, **kwargs: [MagicMock() for _ in range(spec if isinstance(spec, int) else len(spec))]
    api = MagicMock()
    api.get_courses.return_value = [{"course_code": "TEST101", "name": "Test course", "is_active": True}]
    api.get_health.return_value = {}
    api.get_documents.return_value = _docs(8)
    monkeypatch.setattr(main, "st", st)
    monkeypatch.setattr(main, "api", api)
    return st, api


def _cards(st):
    return [c.args[0] for c in st.markdown.call_args_list
            if c.args and "doc-card" in str(c.args[0]) and "<style" not in str(c.args[0])]


def _toggle_buttons(st):
    return [c for c in st.button.call_args_list if c.kwargs.get("key") == "sidebar_docs_toggle"]


def test_five_are_shown_by_default_with_a_button_for_the_rest(ui):
    st, api = ui
    main.render_sidebar()
    assert len(_cards(st)) == 5
    buttons = _toggle_buttons(st)
    assert len(buttons) == 1 and "8" in buttons[0].args[0]


def test_the_button_shows_every_document_and_can_collapse_again(ui):
    st, api = ui
    st.session_state.sidebar_docs_course = "TEST101"
    st.session_state.sidebar_docs_all = True
    main.render_sidebar()
    assert len(_cards(st)) == 8
    assert "fewer" in _toggle_buttons(st)[0].args[0].lower()


def test_pressing_the_button_flips_the_state_and_reruns(ui):
    st, api = ui
    st.button.side_effect = lambda *a, **k: k.get("key") == "sidebar_docs_toggle"
    main.render_sidebar()
    assert st.session_state.sidebar_docs_all is True
    st.rerun.assert_called()


@pytest.mark.parametrize("n", [0, 3, 5])
def test_no_button_when_everything_already_fits(ui, n):
    st, api = ui
    api.get_documents.return_value = _docs(n)
    main.render_sidebar()
    assert len(_cards(st)) == n
    assert not _toggle_buttons(st)


def test_the_list_collapses_again_when_the_course_changes(ui):
    st, api = ui
    st.session_state.sidebar_docs_course = "OTHER"
    st.session_state.sidebar_docs_all = True
    main.render_sidebar()
    assert len(_cards(st)) == 5
    assert st.session_state.sidebar_docs_course == "TEST101"


def test_the_full_name_is_in_a_title_attribute_and_escaped(ui):
    st, api = ui
    api.get_documents.return_value = _docs(1, name='a<b>"c {i}.pdf')
    main.render_sidebar()
    card = _cards(st)[0]
    assert "title='a&lt;b&gt;&quot;c 1.pdf'" in card
    assert "<b>" not in card


def test_the_name_is_styled_to_end_in_an_ellipsis():
    rule = re.search(r"\.doc-card-name\s*\{([^}]*)\}", MAIN_SRC)
    assert rule, ".doc-card-name rule not found"
    css = rule.group(1)
    for needed in ("text-overflow: ellipsis", "overflow: hidden", "white-space: nowrap", "min-width: 0"):
        assert needed in css, needed


def test_the_caption_still_reports_the_true_totals(ui):
    st, api = ui
    main.render_sidebar()
    captions = [c.args[0] for c in st.caption.call_args_list if c.args]
    assert any("8 docs loaded" in c and "8 indexed" in c for c in captions)


def test_six_documents_is_the_first_count_that_needs_the_button(ui):
    st, api = ui
    api.get_documents.return_value = _docs(6)
    main.render_sidebar()
    assert len(_cards(st)) == 5
    assert len(_toggle_buttons(st)) == 1 and "6" in _toggle_buttons(st)[0].args[0]


def test_an_expanded_list_that_shrinks_starts_collapsed_if_it_grows_again(ui):
    st, api = ui
    st.session_state.sidebar_docs_course = "TEST101"
    st.session_state.sidebar_docs_all = True
    api.get_documents.return_value = _docs(3)
    main.render_sidebar()
    assert st.session_state.sidebar_docs_all is False
    api.get_documents.return_value = _docs(8)
    main.render_sidebar()
    assert len(_cards(st)) == 3 + 5
