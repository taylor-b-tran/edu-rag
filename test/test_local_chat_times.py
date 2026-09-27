from datetime import datetime, timezone, timedelta
import logging
import time
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock

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


@pytest.mark.parametrize("zone", ["Bogus/Zone", "", "   "])
def test_invalid_zone_uses_sydney_and_warns_once(monkeypatch, caplog, zone):
    import main
    monkeypatch.setenv("PAEDIA_TIMEZONE", zone)
    resolver = getattr(main, "_display_zone", None)
    if resolver:
        resolver.cache_clear()
    with caplog.at_level(logging.WARNING):
        for _ in range(2):
            assert main._local("2026-10-01T06:00:00Z").strftime("%I:%M %p") == "04:00 PM"
    assert len([r for r in caplog.records if "PAEDIA_TIMEZONE" in r.message]) == 1


def test_zone_override_is_trimmed(monkeypatch):
    import main
    monkeypatch.setenv("PAEDIA_TIMEZONE", "  UTC  ")
    assert main._local("2026-10-01T06:00:00Z").hour == 6


def test_invalid_timestamp_remains_unknown():
    import main
    assert main._local("garbage") is None


def test_naive_utc_is_independent_of_host_timezone(monkeypatch):
    import main
    if not hasattr(time, "tzset"):
        pytest.skip("tzset is required for the host-timezone check")
    try:
        with monkeypatch.context() as patch:
            patch.setenv("TZ", "Pacific/Honolulu")
            patch.delenv("PAEDIA_TIMEZONE", raising=False)
            time.tzset()
            assert main._local(datetime(2026, 10, 1, 6)).strftime("%I:%M %p") == "04:00 PM"
    finally:
        time.tzset()


@pytest.mark.parametrize("day, expected_hour", [(1, 16), (4, 17)])
def test_chat_sites_and_history_cutoff_use_local_clock(ui, monkeypatch, day, expected_hour):
    class Frozen(datetime):
        @classmethod
        def now(cls, tz=None):
            value = cls(2026, 10, day, 6, tzinfo=timezone.utc)
            return value.astimezone(tz) if tz else value.replace(tzinfo=None)
    monkeypatch.setattr(ui, "datetime", Frozen)
    monkeypatch.delenv("PAEDIA_TIMEZONE", raising=False)
    monkeypatch.setattr(ui, "get_ai_response", lambda _: {"answer": "A response", "from_api": True})
    ui.create_new_session()
    assert ui.get_active_session()["created_at"] == f"2026-10-{day:02} {expected_hour}:00"
    ui._submit_query("Explain decision trees")
    ui._send_message("Explain decision trees", append_user=False)
    ui._send_message("Explain the next point", append_user=True)
    assert [m["timestamp"] for m in ui.st.session_state.messages] == [f"0{expected_hour - 12}:00 PM"] * 4
    cutoff = datetime(2026, 10, day, expected_hour) - timedelta(days=7)
    sessions = [{"session_id": "old", "created_at": (cutoff-timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M")},
                {"session_id": "new", "created_at": cutoff.strftime("%Y-%m-%d %H:%M")}]
    assert [s["session_id"] for s in ui._filter_sessions(sessions, "All courses", "Last 7 days", "")] == ["new"]


@pytest.mark.parametrize("stamp, expected", [
    ("2026-09-30T23:30:00Z", "2026-10-01"),
    ("2026-10-04T13:30:00Z", "2026-10-05"),
    ("garbage", "—"),
])
def test_materials_render_local_upload_date_and_honest_caption(monkeypatch, stamp, expected):
    import main
    from test.test_active_course_resolution import make_ui
    st, api = make_ui(monkeypatch, enrolled=["CSIT321"], course_id="CSIT321")
    columns = [MagicMock() for _ in range(6)]
    for col in columns:
        col.button.return_value = False
    st.columns.return_value = columns
    st.columns.side_effect = None
    api.get_documents.return_value = [{"document_id": "one", "filename": "notes.pdf",
        "uploaded_at": stamp, "chunks": 2, "status": "indexed"}]
    main._render_document_table(student_view=True)
    assert expected in columns[4].markdown.call_args.args[0]
    st.caption.assert_called_once_with("1 documents · 1 indexed · 2 chunks")
