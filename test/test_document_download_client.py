"""Opening a document has to say which thing went wrong.

The first version returned bare bytes, or None for everything: a 401, a 403, a
timeout and a genuinely missing file were indistinguishable, and the screen
reported all four as "its file is not on the server". That is wrong three times
out of four, and in every one of those cases it sends the reader after a
problem they cannot do anything about. It also skipped the token refresh the
rest of the client performs, so an expired session failed instead of renewing.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "streamlit"))

from api_client import APIConfig, PaediaAPIClient  # noqa: E402


class _Response:
    def __init__(self, status_code, content=b"", body=None):
        self.status_code = status_code
        self.content = content
        self._body = body

    def json(self):
        if self._body is None:
            raise ValueError("no json")
        return self._body


@pytest.fixture
def client():
    c = PaediaAPIClient(APIConfig(base_url="http://test.invalid",
                                  use_fixtures=False, max_retries=0))
    c._jwt_token = "access-token"
    return c


def _answer(monkeypatch, *responses):
    """Serve the given responses in order, recording the calls."""
    calls = []

    def fake_get(url, headers=None, timeout=None):
        calls.append({"url": url, "headers": headers})
        reply = responses[min(len(calls) - 1, len(responses) - 1)]
        if isinstance(reply, Exception):
            raise reply
        return reply

    monkeypatch.setattr(requests, "get", fake_get)
    return calls


# --- the file arrives ---------------------------------------------------

def test_a_successful_read_returns_the_bytes(client, monkeypatch):
    _answer(monkeypatch, _Response(200, b"%PDF-1.4 real file"))
    result = client.download_document("doc-1")
    assert result["success"] is True
    assert result["content"] == b"%PDF-1.4 real file"
    assert result["error"] is None


def test_it_asks_the_file_endpoint_for_that_document(client, monkeypatch):
    calls = _answer(monkeypatch, _Response(200, b"x"))
    client.download_document("doc-42")
    assert calls[0]["url"].endswith("/api/document/doc-42/file")


# --- the failures are told apart ----------------------------------------

def test_a_missing_file_says_the_file_is_missing(client, monkeypatch):
    _answer(monkeypatch, _Response(404, body={
        "error": "file unavailable",
        "message": "This document is listed but its file is not on the server."}))
    result = client.download_document("doc-1")
    assert result["success"] is False
    assert result["status_code"] == 404
    assert "not on the server" in result["error"]


def test_an_expired_session_does_not_look_like_a_missing_file(client, monkeypatch):
    """The whole point: these two were reported identically."""
    client._refresh_token = None
    _answer(monkeypatch, _Response(401, body={"error": "Authentication required."}))
    result = client.download_document("doc-1")
    assert result["status_code"] == 401
    assert "not on the server" not in (result["error"] or "")
    assert "sign in" in result["error"].lower()


def test_a_forbidden_read_says_so(client, monkeypatch):
    _answer(monkeypatch, _Response(403, body={}))
    result = client.download_document("doc-1")
    assert result["status_code"] == 403
    assert "permission" in result["error"].lower()


def test_a_timeout_is_reported_as_a_timeout(client, monkeypatch):
    _answer(monkeypatch, requests.Timeout())
    result = client.download_document("doc-1")
    assert result["success"] is False
    assert result["status_code"] is None
    assert "timed out" in result["error"].lower()
    assert "not on the server" not in result["error"]


def test_an_unreachable_server_is_reported_as_unreachable(client, monkeypatch):
    _answer(monkeypatch, requests.ConnectionError())
    result = client.download_document("doc-1")
    assert result["success"] is False
    assert "reach the server" in result["error"].lower()


def test_a_server_error_asks_for_a_retry_not_a_re_upload(client, monkeypatch):
    _answer(monkeypatch, _Response(503, body={}))
    result = client.download_document("doc-1")
    assert result["status_code"] == 503
    assert "retry" in result["error"].lower()


def test_a_body_that_is_not_json_still_produces_a_usable_message(client, monkeypatch):
    _answer(monkeypatch, _Response(500, content=b"<html>Gateway</html>"))
    result = client.download_document("doc-1")
    assert result["success"] is False
    assert result["error"]


# --- the refresh the first version skipped ------------------------------

def test_a_401_is_retried_once_behind_a_token_refresh(client, monkeypatch):
    client._refresh_token = "refresh-token"
    monkeypatch.setattr(type(client), "_refresh_jwt", lambda self: True)
    calls = _answer(monkeypatch, _Response(401, body={}), _Response(200, b"after refresh"))

    result = client.download_document("doc-1")

    assert len(calls) == 2
    assert result["success"] is True
    assert result["content"] == b"after refresh"


def test_a_refresh_that_fails_reports_the_expired_session(client, monkeypatch):
    client._refresh_token = "refresh-token"
    monkeypatch.setattr(type(client), "_refresh_jwt", lambda self: False)
    calls = _answer(monkeypatch, _Response(401, body={}))

    result = client.download_document("doc-1")

    assert len(calls) == 1
    assert result["status_code"] == 401
    assert "sign in" in result["error"].lower()


# --- fixture mode -------------------------------------------------------

def test_fixture_mode_says_it_needs_the_live_system():
    demo = PaediaAPIClient(APIConfig(use_fixtures=True))
    result = demo.download_document("doc-1")
    assert result["success"] is False
    assert "live system" in result["error"]
