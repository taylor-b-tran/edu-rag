"""The Admin Dashboard says how the model warm-up went, in words.

The warm-up status used to be passed to st.metric as its third argument, which
is the delta. Streamlit draws any delta that does not start with a minus sign
as a green up arrow, so "failed", "degraded" and "unknown" all looked healthy.
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
def admin_page(monkeypatch):
    st = MagicMock()
    st.session_state = State(user={"role": "Administrator", "name": "Admin", "enrolled_courses": []},
                             course_id="", current_page="admin", sessions=[], active_session_id=None)
    st.button.return_value = False
    cols = [MagicMock() for _ in range(4)]
    st.columns.side_effect = lambda spec, **kw: (
        cols if spec == 4 else [MagicMock() for _ in range(spec if isinstance(spec, int) else len(spec))])
    api = MagicMock()
    monkeypatch.setattr(main, "st", st)
    monkeypatch.setattr(main, "api", api)
    monkeypatch.setattr(main, "render_course_management", lambda *a, **k: None)
    monkeypatch.setattr(main, "render_pending_lecturers", lambda *a, **k: None)
    return st, api, cols


def _stats(warmup):
    return {"courses": 3, "documents": 5, "uploaded_documents": 2, "indexing_jobs": 2,
            "mode": "chromadb", "warmup": warmup}


def test_warmup_is_not_drawn_as_a_metric_delta(admin_page):
    st, api, cols = admin_page
    api.get_admin_stats.return_value = _stats({"status": "failed", "error": "boom"})
    main.render_admin_page()
    call = cols[3].metric.call_args
    assert len(call.args) == 2 and "delta" not in call.kwargs
    captions = " ".join(str(c.args[0]) for c in cols[3].caption.call_args_list)
    assert "Failed" in captions and "boom" in captions


@pytest.mark.parametrize("warmup, word", [
    ({"status": "ok", "model": "gemma4:12b", "elapsed_ms": 2300}, "Ready"),
    ({"status": "degraded", "error": "generate_failed: timeout"}, "Degraded"),
    ({"status": "failed", "error": "RuntimeError: x"}, "Failed"),
    ({"status": "running"}, "Running"),
    ({"status": "pending"}, "Not started"),
    ({"skipped": True}, "Skipped"),
    ({}, "Unknown"),
    (None, "Unknown"),
])
def test_warmup_summary_names_each_state(warmup, word):
    assert word in main._warmup_summary(warmup)


def test_ready_summary_names_the_model_and_time():
    text = main._warmup_summary({"status": "ok", "model": "gemma4:12b", "elapsed_ms": 2300})
    assert "gemma4:12b" in text and "2.3 s" in text


def test_warmup_error_detail_is_bounded():
    text = main._warmup_summary({"status": "failed", "error": "E" * 500})
    assert text.count("E") <= 120 and len(text) < 200
