"""Real SQL round trips in disposable schemas, never production chat rows."""
import os
import pytest
from src.api import db
from test.test_token_transactions_postgres import pg
from test.test_t914_reload import META

pytestmark = pytest.mark.skipif(not os.getenv("PAEDIA_TEST_POSTGRES_HOST"), reason="Opt-in isolated PostgreSQL tests")

def test_metadata_round_trip_and_message_order_across_reads(pg):
    db.upsert_chat_session("chat", "owner", "CSCI203")
    for i in range(3):
        db.insert_chat_message("chat", {"message_id": str(i), "question": f"Question {i}",
            "answer": f"Answer {i}", "sources": [{"filename": "lecture.pdf", "page": i}], "response_metadata": META})
    all_messages = db.load_all_sessions()["chat"]["messages"]
    single = db.get_chat_session("chat")["messages"]
    assert all_messages == single
    assert [m["question"] for m in single] == ["Question 0", "Question 1", "Question 2"]
    assert all(m["response_metadata"] == META for m in single)
    assert db.get_chat_session("chat", message_limit=2)["messages"] == single[-2:]

def test_legacy_migration_preserves_text_and_leaves_unknown_metadata(pg):
    with pg() as conn:
        conn.execute("ALTER TABLE chat_messages DROP COLUMN response_metadata")
        conn.execute("INSERT INTO chat_sessions(session_id) VALUES ('legacy')")
        conn.execute("INSERT INTO chat_messages(message_id, session_id, question, answer) VALUES ('old', 'legacy', 'Old question', 'Old answer')")
        conn.execute(db.SESSION_SCHEMA)
        conn.execute(db.SESSION_SCHEMA)
    message = db.get_chat_session("legacy")["messages"][0]
    assert message["answer"] == "Old answer" and message["response_metadata"] == {}

def test_state_persists_exact_available_metadata_and_updates_recency(pg):
    from src.api.state import APIState
    state = object.__new__(APIState)
    state.sessions = {}; state._db_available = True
    sid = state.record_session_message(None, "owner", "CSIT321", "Question one", {
        "answer": "Answer one", "source_references": [{"page": 2}], **META})
    with pg() as conn:
        conn.execute("UPDATE chat_sessions SET updated_at = '2000-01-01' WHERE session_id = %s", (sid,))
    state.record_session_message(sid, "owner", "CSIT321", "Question two", {"answer": "Answer two"})
    restored = db.get_chat_session(sid)
    assert restored["messages"][0]["response_metadata"] == META
    assert restored["messages"][1]["response_metadata"] == {}
    assert not restored["updated_at"].startswith("2000")
