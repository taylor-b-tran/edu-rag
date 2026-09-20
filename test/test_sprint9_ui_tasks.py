"""Tests for Sprint 9 UI tasks: session delete (T9-13), response-style
picker (T8-11), and course join (T8-05).

The backend tests hit the Flask routes via the test client (same style
as test_sessions_across_workers.py). The Streamlit helpers are tested
by calling them directly with monkeypatched session_state and api.
"""
from __future__ import annotations

import pytest

from src.api.app import create_app

STUDENT = {
    "user_id": "u-stu",
    "email": "stu@uow.edu.au",
    "role": "student",
    "enrolled_courses": ["CSIT321"],
}
OTHER = {
    "user_id": "u-other",
    "email": "other@uow.edu.au",
    "role": "student",
    "enrolled_courses": [],
}
AUTH = {"Authorization": "Bearer stub"}

SESSION_A = {
    "session_id": "sess-a",
    "user_id": STUDENT["user_id"],
    "course_id": "CSIT321",
    "archived": False,
    "messages": [{"message_id": "m1", "question": "hi", "answer": "hello",
                  "sources": [], "created_at": None}],
}


@pytest.fixture
def current():
    return {"user": STUDENT}


@pytest.fixture
def client(monkeypatch, current):
    app = create_app()
    app.config.update(TESTING=True)
    state = app.config["EDURAG_API_STATE"]

    monkeypatch.setattr(type(state), "validate_bearer",
                        lambda self, authorization: current["user"])

    state.sessions["sess-a"] = dict(SESSION_A)

    c = app.test_client()
    c.state = state
    return c


# ═══════════════════════════════════════════════════════════════════════
# T9-13 — DELETE /api/sessions/<id>
# ═══════════════════════════════════════════════════════════════════════

class TestSessionDelete:

    def test_owner_can_delete(self, client):
        resp = client.delete("/api/sessions/sess-a", headers=AUTH)
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["status"] == "success"
        assert body["session_id"] == "sess-a"

    def test_delete_twice_does_not_crash(self, client):
        """Archiving the same session twice should succeed or 404, never 500."""
        resp1 = client.delete("/api/sessions/sess-a", headers=AUTH)
        assert resp1.status_code == 200
        resp2 = client.delete("/api/sessions/sess-a", headers=AUTH)
        assert resp2.status_code in (200, 404)

    def test_other_user_cannot_delete(self, client, current):
        current["user"] = OTHER
        resp = client.delete("/api/sessions/sess-a", headers=AUTH)
        assert resp.status_code == 403

    def test_anonymous_cannot_delete(self, client, current):
        current["user"] = None
        resp = client.delete("/api/sessions/sess-a", headers=AUTH)
        assert resp.status_code == 401

    def test_missing_session_returns_404(self, client):
        resp = client.delete("/api/sessions/nope", headers=AUTH)
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════
# T8-11 — GET /api/response-styles
# ═══════════════════════════════════════════════════════════════════════

class TestResponseStyles:

    def test_returns_list_with_default(self, client):
        resp = client.get("/api/response-styles", headers=AUTH)
        assert resp.status_code == 200
        body = resp.get_json()
        assert isinstance(body["styles"], list)
        assert len(body["styles"]) > 0
        assert body["default"] is not None

    def test_each_style_has_id(self, client):
        body = client.get("/api/response-styles", headers=AUTH).get_json()
        for s in body["styles"]:
            assert "id" in s, f"style missing id: {s}"

    def test_default_is_in_styles(self, client):
        body = client.get("/api/response-styles", headers=AUTH).get_json()
        ids = [s["id"] for s in body["styles"]]
        assert body["default"] in ids

    def test_query_accepts_valid_response_style(self, client):
        """POST /api/query with a valid response_style should not be
        rejected with 400 (the query itself will fail because no
        pipeline is loaded in test mode, but the parameter should be
        accepted)."""
        styles = client.get("/api/response-styles", headers=AUTH).get_json()
        style_id = styles["styles"][0]["id"]
        resp = client.post("/api/query", headers=AUTH, json={
            "query": "test",
            "course_id": "CSIT321",
            "response_style": style_id,
        })
        # Should NOT be 400 "invalid response_style"
        assert resp.status_code != 400 or "response_style" not in resp.get_json().get("error", "")

    def test_query_rejects_invalid_response_style(self, client):
        resp = client.post("/api/query", headers=AUTH, json={
            "query": "test",
            "course_id": "CSIT321",
            "response_style": "nonexistent_style",
        })
        assert resp.status_code == 400
        assert "response_style" in resp.get_json().get("error", "")


# ═══════════════════════════════════════════════════════════════════════
# T8-05 — POST /api/courses/<code>/join  (when backend lands)
# For now: test that the old /enrol endpoint is removed.
# ═══════════════════════════════════════════════════════════════════════

class TestCourseJoin:

    def test_old_enrol_endpoint_is_gone(self, client):
        """The /enrol route was removed per Taylor's review."""
        resp = client.post("/api/courses/CSIT321/enrol", headers=AUTH, json={})
        assert resp.status_code in (404, 405), \
            f"/enrol should be gone, got {resp.status_code}"


# ═══════════════════════════════════════════════════════════════════════
# api_client unit tests (no live server)
# ═══════════════════════════════════════════════════════════════════════

class TestAPIClientMethods:
    """Test the PaediaAPIClient wrappers by mocking _delete / _post."""

    def _make_client(self):
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__),
                                        "..", "apps", "streamlit"))
        from api_client import PaediaAPIClient, APIConfig
        cfg = APIConfig(base_url="http://localhost:5000", timeout=5, use_fixtures=False)
        return PaediaAPIClient(config=cfg)

    def test_delete_session_success(self, monkeypatch):
        c = self._make_client()
        monkeypatch.setattr(c, "_delete",
                            lambda ep: {"status": "success", "session_id": "s1"})
        result = c.delete_session("s1")
        assert result["success"] is True

    def test_delete_session_api_error(self, monkeypatch):
        c = self._make_client()
        monkeypatch.setattr(c, "_delete",
                            lambda ep: {"_api_error": True, "error": "not found",
                                        "status_code": 404})
        result = c.delete_session("s1")
        assert result["success"] is False

    def test_delete_session_network_failure(self, monkeypatch):
        c = self._make_client()
        monkeypatch.setattr(c, "_delete", lambda ep: None)
        result = c.delete_session("s1")
        assert result["success"] is False

    def test_join_course_success(self, monkeypatch):
        c = self._make_client()
        monkeypatch.setattr(c, "_post",
                            lambda ep, body: {"status": "enrolled",
                                              "enrolled_courses": ["CSIT321", "CSIT214"]})
        result = c.join_course("CSIT214")
        assert result["success"] is True
        assert result["enrolled_courses"] == ["CSIT321", "CSIT214"]

    def test_join_course_api_error(self, monkeypatch):
        c = self._make_client()
        monkeypatch.setattr(c, "_post",
                            lambda ep, body: {"_api_error": True,
                                              "error": "course not found",
                                              "status_code": 404})
        result = c.join_course("NOPE")
        assert result["success"] is False
        assert result["enrolled_courses"] is None

    def test_join_course_network_failure(self, monkeypatch):
        c = self._make_client()
        monkeypatch.setattr(c, "_post", lambda ep, body: None)
        result = c.join_course("CSIT214")
        assert result["success"] is False

    def test_query_passes_response_style(self, monkeypatch):
        c = self._make_client()
        captured = {}

        def fake_post(ep, payload, **kw):
            captured.update(payload)
            return {"answer": "ok", "source_references": []}

        monkeypatch.setattr(c, "_check_api", lambda: True)
        monkeypatch.setattr(c, "_post", fake_post)
        c.query("test", "CSIT321", response_style="concise")
        assert captured.get("response_style") == "concise"

    def test_query_omits_response_style_when_none(self, monkeypatch):
        c = self._make_client()
        captured = {}

        def fake_post(ep, payload, **kw):
            captured.update(payload)
            return {"answer": "ok", "source_references": []}

        monkeypatch.setattr(c, "_check_api", lambda: True)
        monkeypatch.setattr(c, "_post", fake_post)
        c.query("test", "CSIT321", response_style=None)
        assert "response_style" not in captured
