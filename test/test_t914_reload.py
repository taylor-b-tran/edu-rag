"""Faithful reload, selection, identity and legacy metadata regressions."""
import copy
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "streamlit"))

class State(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__

class Params(dict):
    def to_dict(self): return dict(self)
    def from_dict(self, value): self.clear(); self.update(value)

META = {"confidence": "high", "confidence_score": .93, "model_used": "ollama/test",
        "latency_ms": 1234, "is_fallback": False, "backend_mode": "chromadb",
        "retrieval_metadata": {"num_chunks_retrieved": 4}, "token_count": 50,
        "response_style": "concise"}

def saved(sid="a", course="CSIT321", **kw):
    return dict(session_id=sid, course_id=course, messages=[{
        "question": "First question", "answer": "Cited answer [1]", "sources": [{"page": 1}],
        "response_metadata": META, "created_at": "2026-09-10T01:00:00Z"},
        {"question": "Follow up", "answer": "Legacy answer", "sources": []}], **kw)

@pytest.fixture
def ui(monkeypatch):
    import main
    monkeypatch.setattr(main.st, "session_state", State())
    monkeypatch.setattr(main.st, "query_params", Params())
    main.init_session_state()
    main.st.session_state.course_options = ["CSIT321", "CSCI203"]
    fake = Mock(config=SimpleNamespace(use_fixtures=False))
    fake.get_sessions.return_value = [saved(), saved("b", "CSCI203")]
    monkeypatch.setattr(main, "api", fake)
    return main

def test_reload_keeps_selected_conversation_course_order_and_metadata(ui):
    ui.st.query_params.update(chat="b")
    ui._hydrate_sessions_from_server()
    state = ui.st.session_state
    assert state.session_id == state.active_session_id == "b"
    assert state.course_id == state.selected_course_id == "CSCI203"
    assert [m["content"] for m in state.messages] == ["First question", "Cited answer [1]", "Follow up", "Legacy answer"]
    assert all(state.messages[1][k] == v for k,v in META.items())
    assert state.messages[1]["source_references"] == [{"page": 1}]
    assert "confidence" not in state.messages[3] and "is_fallback" not in state.messages[3]
    ui.get_ai_response("Continue the explanation")
    ui.api.query.assert_called_once_with("Continue the explanation", course_id="CSCI203", session_id="b")

@pytest.mark.parametrize("sid", ["foreign", "archived", "unenrolled"])
def test_url_hint_cannot_restore_unowned_archived_or_unenrolled_chat(ui, sid):
    ui.api.get_sessions.return_value += [saved("archived", archived=True), saved("unenrolled", "REMOVED101")]
    ui.st.query_params.update(chat=sid, course="REMOVED101")
    ui._hydrate_sessions_from_server()
    assert ui.st.session_state.session_id is None
    assert ui.st.session_state.messages == []
    assert ui.st.session_state.course_id == "CSIT321"
    assert "chat" not in ui.st.query_params

def test_empty_history_clears_previous_account_data(ui):
    ui.st.session_state.sessions = [saved("private")]
    ui.st.session_state.messages = [{"content": "private"}]
    ui.api.get_sessions.return_value = []
    ui._hydrate_sessions_from_server()
    assert ui.st.session_state.messages == []
    assert all(s["session_id"] != "private" for s in ui.st.session_state.sessions)

def test_switch_and_new_chat_update_url_without_credentials(ui):
    ui._hydrate_sessions_from_server()
    ui.switch_session("b")
    assert ui.st.query_params == {"chat": "b", "course": "CSCI203"}
    ui.create_new_session()
    assert ui.st.query_params == {"course": "CSCI203"}
    assert ui.st.session_state.session_id is None

def test_course_change_starts_separate_chat_and_preserves_old_history(ui):
    ui.st.query_params.update(chat="a")
    ui._hydrate_sessions_from_server()
    previous = ui.get_active_session()
    ui.st.session_state.selected_course_id = "CSCI203"
    ui._change_chat_course()
    assert previous["backend_session_id"] == "a" and len(previous["messages"]) == 4
    assert ui.st.session_state.messages == [] and ui.st.session_state.session_id is None
    assert ui.st.query_params == {"course": "CSCI203"}

@pytest.mark.parametrize("role", ["student", "lecturer", "admin"])
def test_profile_normalization_is_consistent(ui, role):
    login = ui._normalise_user_for_ui(dict(id="u", name="Taylor", username="Taylor", role=role))
    restored = ui._normalise_user_for_ui(dict(user_id="u", username="Taylor", role=role))
    assert (login["id"], login["name"], login["role"]) == (restored["id"], restored["name"], restored["role"])

def test_outage_keeps_cookie_and_requires_retry(ui, monkeypatch):
    from api_client import APIReadError
    cookies = Mock(); cookies.get.return_value = "test-access"
    monkeypatch.setattr(ui, "_cookies", lambda: cookies)
    ui.api.get_current_user.side_effect = APIReadError("/api/auth/me", {"error": "Unavailable", "status_code": 503})
    with pytest.raises(APIReadError): ui._restore_session_from_cookie()
    cookies.remove.assert_not_called()
    assert not ui.st.session_state.authenticated

def test_rejected_cookie_clears_private_state_and_explains_reauthentication(ui, monkeypatch):
    cookies = Mock(); cookies.get.return_value = "rejected-access"
    monkeypatch.setattr(ui, "_cookies", lambda: cookies)
    ui.api.get_current_user.return_value = {"success": False}
    ui.st.session_state.messages = [{"content": "private"}]
    assert not ui._restore_session_from_cookie()
    ui._flush_auth_cookie()
    cookies.remove.assert_called_once_with(ui._AUTH_COOKIE)
    assert ui.st.session_state.messages == []
    assert "sign in again" in ui.st.session_state.login_error

@pytest.fixture
def server(monkeypatch):
    from src.api.app import create_app
    from src.api.routes import query, settings
    app = create_app(); app.config["TESTING"] = True
    state = app.config["EDURAG_API_STATE"]
    state._db_available = False
    query._RATE_STORE.clear()
    monkeypatch.setattr(settings, "effective_settings", lambda cid: {})
    return app.test_client(), state

@pytest.mark.parametrize("fallback", [False, True])
def test_query_response_metadata_reaches_history_api(server, monkeypatch, fallback):
    client, state = server
    user = {"user_id": "owner", "email": "owner@example.invalid", "role": "student", "enrolled_courses": ["CSIT321"]}
    tokens = state.issue_tokens(user)
    headers = {"Authorization": "Bearer " + tokens["access_token"]}
    generated = SimpleNamespace(answer="Saved answer [1]", source_refs=[{"page": 2}],
        confidence="high", confidence_score=.91, model_used="test-model", is_fallback=fallback,
        response_style="concise", retrieval_metadata={"num_chunks_retrieved": 1}, token_count=12)
    monkeypatch.setattr(state, "get_generator", lambda: SimpleNamespace(generate=lambda *a, **k: generated))
    monkeypatch.setattr(state, "is_enrolled", lambda *a: True)
    result = client.post("/api/query", headers=headers, json={"query": "Explain RAG retrieval", "course_id": "CSIT321"})
    assert result.status_code == 200
    answer = result.get_json()
    stored = client.get("/api/sessions/" + answer["session_id"], headers=headers).get_json()["messages"][0]
    assert stored["sources"] == answer["source_references"]
    for key, value in stored["response_metadata"].items(): assert answer[key] == value
    assert stored["response_metadata"]["is_fallback"] is fallback
    assert stored["response_metadata"]["latency_ms"] >= 0

@pytest.mark.parametrize("role", ["student", "lecturer", "admin"])
def test_me_resolves_database_profile_instead_of_token_email(server, monkeypatch, role):
    from src.api import db
    client, state = server
    user = dict(user_id="owner", username="Visible Name", email="owner@example.invalid", role=role, enrolled_courses=[])
    login = state.issue_tokens(user)
    payload = state.access_tokens[login["access_token"]]
    assert "username" not in payload
    state._db_available = True
    monkeypatch.setattr(db, "get_token", lambda *a: payload)
    monkeypatch.setattr(db, "get_user_by_email", lambda email: user)
    me = client.get("/api/auth/me", headers={"Authorization": "Bearer " + login["access_token"]})
    assert me.status_code == 200
    assert me.get_json() == login["user"]

@pytest.mark.parametrize("ended", ["expired", "revoked"])
def test_ended_access_cannot_restore_or_reauthenticate(server, monkeypatch, ended):
    import time
    client, state = server
    issued = state.issue_tokens({"user_id": "u", "email": "u@example.invalid"})
    token = issued["access_token"]
    if ended == "expired":
        state.access_tokens[token]["expires_at"] = time.time() - 1
    else:
        state.revoke_login(token, None)
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer " + token}).status_code == 401


def test_cookie_write_survives_rerun_without_sliding_expiry(ui, monkeypatch):
    from datetime import datetime, timezone
    cookies = Mock()
    monkeypatch.setattr(ui, "_cookies", lambda: cookies)
    ui._remember_session("access-only")
    cookies.set.assert_not_called()
    ui._flush_auth_cookie()
    first = cookies.set.call_args
    assert 3595 < (first.kwargs["expires"] - datetime.now(timezone.utc)).total_seconds() <= 3600
    assert "max_age" not in first.kwargs
    ui._flush_auth_cookie()
    assert cookies.set.call_args == first
    ui._forget_session()
    ui._flush_auth_cookie()
    cookies.remove.assert_called_once_with(ui._AUTH_COOKIE)

@pytest.mark.parametrize("entry", ["login", "restore"])
def test_course_bootstrap_outage_retries_full_initialization(ui, monkeypatch, entry):
    from api_client import APIReadError
    user = {"id": "u", "username": "Taylor", "role": "student", "enrolled_courses": ["CSIT321"]}
    cookies = Mock(); cookies.get.return_value = "access"
    monkeypatch.setattr(ui, "_cookies", lambda: cookies)
    ui.api.login.return_value = {"success": True, "user": user, "jwt_token": "access"}
    ui.api.get_current_user.return_value = {"success": True, "user": user}
    ui.api.get_courses.side_effect = APIReadError("/api/courses", {"error": "Unavailable", "status_code": 503})
    with pytest.raises(APIReadError):
        (ui.handle_login_submit if entry == "login" else ui._restore_session_from_cookie)()
    assert not ui.st.session_state.authenticated
    ui.api.get_courses.side_effect = None
    ui.api.get_courses.return_value = [{"course_code": "CSIT321"}]
    assert ui._restore_session_from_cookie()
    assert ui.st.session_state.authenticated and ui.st.session_state.course_options == ["CSIT321"]


def test_session_store_outage_is_503_not_an_expired_cookie(server, monkeypatch):
    from src.api import db
    client, state = server
    issued = state.issue_tokens({"user_id": "u", "email": "u@example.invalid"})
    state._db_available = True
    monkeypatch.setattr(db, "get_token", Mock(side_effect=ConnectionError("database unavailable")))
    response = client.get("/api/auth/me", headers={"Authorization": "Bearer " + issued["access_token"]})
    assert response.status_code == 503
    # Existing authorization callers still fail closed, and never use RAM credentials.
    assert state.validate_bearer("Bearer " + issued["access_token"]) is None


def test_restored_widget_event_for_same_course_keeps_backend_session(ui):
    ui.st.query_params.update(chat="a")
    ui._hydrate_sessions_from_server()
    ui._change_chat_course()
    assert ui.st.session_state.session_id == "a"
    assert len(ui.st.session_state.messages) == 4
