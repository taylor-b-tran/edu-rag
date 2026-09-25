from datetime import datetime
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "streamlit"))
from test.test_t914_reload import ui  # noqa: F401


@pytest.mark.parametrize("stamp, expected", [
    ("2026-09-25T06:00:00Z", "04:00 PM"),
    ("2026-10-05T06:00:00Z", "05:00 PM"),
    (datetime(2026, 9, 25, 6), "04:00 PM"),
    ("2026-09-25T08:00:00+02:00", "04:00 PM"),
])
def test_local_time_uses_sydney_dst(monkeypatch, stamp, expected):
    import main
    monkeypatch.delenv("PAEDIA_TIMEZONE", raising=False)
    assert main._local(stamp).strftime("%I:%M %p") == expected


def test_timezone_can_be_overridden(monkeypatch):
    import main
    monkeypatch.setenv("PAEDIA_TIMEZONE", "UTC")
    assert main._local("2026-09-25T06:00:00Z").strftime("%I:%M %p") == "06:00 AM"


def test_reload_keeps_server_message_and_session_times(ui):
    ui.st.query_params.update(chat="a")
    saved = ui.api.get_sessions.return_value[0]
    saved["created_at"] = "2026-09-25T06:00:00Z"
    saved["messages"][0]["created_at"] = "2026-09-25T06:00:00Z"
    for _ in range(2):
        ui._hydrate_sessions_from_server()
        assert [m["timestamp"] for m in ui.st.session_state.messages[:2]] == ["04:00 PM"] * 2
        assert ui.get_active_session()["created_at"] == "2026-09-25 16:00"
        assert ui.st.session_state.messages[2]["timestamp"] == ""


def test_materials_caption_does_not_claim_semantic_search():
    source = (Path(__file__).resolve().parents[1] / "apps/streamlit/main.py").read_text()
    assert "chunks · Semantic search ON" not in source
