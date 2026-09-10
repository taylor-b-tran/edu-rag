"""T8-07: failed live operations never become demo data or empty success."""
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "streamlit"))
from api_client import APIConfig, APIReadError, PaediaAPIClient
import api_client


@pytest.fixture
def client():
    return PaediaAPIClient(APIConfig(base_url="http://test.invalid", use_fixtures=False, max_retries=0))


def response(status, body):
    return Mock(status_code=status, json=Mock(return_value=body))


@pytest.fixture(params=["connection", "timeout", 401, 403, 500])
def fault(request, monkeypatch):
    kind = request.param
    for method in ("get", "post", "delete", "patch"):
        if kind in ("connection", "timeout"):
            error = api_client.requests.Timeout if kind == "timeout" else api_client.requests.ConnectionError
            fake = Mock(side_effect=error())
        else:
            fake = Mock(return_value=response(kind, {"error": "Request rejected"}))
        monkeypatch.setattr(api_client.requests, method, fake)
    return kind


@pytest.mark.parametrize("method,args", [
    ("get_courses", ()), ("get_documents", ("CSIT321",)),
    ("get_sessions", ()), ("get_course_members", ("CSIT321",)),
])
def test_failed_lists_are_not_empty_or_fixtures(client, fault, method, args):
    with pytest.raises(APIReadError) as raised:
        getattr(client, method)(*args)
    assert raised.value.status_code == (fault if isinstance(fault, int) else None)


def test_failed_operations_are_never_success_or_grounded_fallback(client, fault):
    answer = client.query("What is RAG?", "CSIT321")
    assert answer["error_type"]
    assert answer["is_fallback"] is False
    assert answer["source_references"] == []
    uploaded = client.upload_document(b"probe", "probe.txt", "CSIT321")
    assert uploaded["success"] is False and uploaded["job_id"] is None
    assert client.delete_document("probe")["success"] is False
    job = client.get_indexing_status("probe")
    assert job["status"] == "unavailable" and "progress_percent" not in job
    assert client.get_admin_stats()["_offline"]
    assert "users" not in client.get_admin_stats()
    assert client.get_global_settings()["_unavailable"]
    assert client.get_course_settings("CSIT321")["_unavailable"]
    assert client.get_health()["_unavailable"]


def test_recovers_with_same_client_after_outage(client, monkeypatch):
    get = Mock(side_effect=[api_client.requests.ConnectionError(), response(200, {"courses": [{"course_code": "NEW101"}]})])
    monkeypatch.setattr(api_client.requests, "get", get)
    with pytest.raises(APIReadError):
        client.get_courses()
    assert client.get_courses() == [{"course_code": "NEW101"}]
    assert get.call_count == 2


@pytest.mark.parametrize("body", [[], {"courses": []}])
def test_successful_empty_list_is_valid(client, monkeypatch, body):
    monkeypatch.setattr(api_client.requests, "get", Mock(return_value=response(200, body)))
    assert client.get_courses() == []


def test_explicit_fixture_mode_never_requests_network(monkeypatch):
    for method in ("get", "post", "delete", "patch"):
        monkeypatch.setattr(api_client.requests, method, Mock(side_effect=AssertionError("Demo sent live request")))
    demo = PaediaAPIClient(APIConfig(use_fixtures=True))
    assert demo.get_courses()
    assert demo.query("What is RAG?", "CSIT321")["from_api"] is False
    assert demo.upload_document(b"demo", "demo.txt", "CSIT321")["success"]
    assert demo.get_indexing_status("demo")["status"] == "completed"
    assert "demo" in demo.mode_label


def test_live_mode_does_not_load_fixture_file(monkeypatch):
    monkeypatch.setattr(api_client, "_load_fixtures", Mock(side_effect=AssertionError("Fixtures loaded")))
    assert PaediaAPIClient(APIConfig(use_fixtures=False))._fixtures is None


def test_timeout_write_is_not_replayed(client, monkeypatch):
    post = Mock(side_effect=api_client.requests.Timeout())
    monkeypatch.setattr(api_client.requests, "post", post)
    assert client.signup("probe@example.invalid", "probe", "irrelevant")["success"] is False
    assert post.call_count == 1


def test_unavailable_is_not_labeled_demo(client, monkeypatch):
    monkeypatch.setattr(api_client.requests, "get", Mock(side_effect=api_client.requests.ConnectionError()))
    assert client.mode_label == "API unavailable"


def test_empty_live_courses_do_not_create_seeded_enrollment(monkeypatch):
    import main
    monkeypatch.setattr(main, "_all_courses", lambda: [])
    assert main._course_options_for_user({"role": "Student", "enrolled_courses": []}) == []
    assert main._course_options_for_user({"role": "Admin"}) == []


def test_live_query_preserves_success_and_rag_fallback(client, monkeypatch):
    for fallback in (True, False):
        payload = {"answer": "Actual server answer", "is_fallback": fallback, "session_id": "real"}
        monkeypatch.setattr(api_client.requests, "post", Mock(return_value=response(200, payload)))
        result = client.query("What is RAG?", "CSIT321")
        assert result["is_fallback"] == fallback and result["from_api"]
        assert "error_type" not in result


def test_restore_outage_does_not_look_like_revoked_credentials(client, monkeypatch):
    monkeypatch.setattr(api_client.requests, "get", Mock(return_value=response(503, {})))
    with pytest.raises(APIReadError):
        client.get_current_user("existing-token")
    assert client._jwt_token == "existing-token"
    monkeypatch.setattr(api_client.requests, "get", Mock(return_value=response(401, {})))
    assert client.get_current_user()["success"] is False


def test_stats_do_not_present_fixture_users_or_worker_totals_as_live(client, monkeypatch):
    monkeypatch.setattr(api_client.requests, "get", Mock(return_value=response(200, {
        "users": 3, "sessions": 10, "queries_total": 50, "documents": 7,
    })))
    stats = client.get_admin_stats()
    assert stats["users"] is None and stats["sessions"] is None and stats["queries_total"] is None
    assert stats["documents"] == 7
