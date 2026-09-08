"""
T8-26 — Unit coverage for scripts/loadtest_query.py's aggregation logic.

This does NOT exercise the real HTTP flow (signup/enroll/query against a
live stack) - that needs Postgres + a running API, which CI and this repo's
usual pytest environment don't provide. What it does verify, with the
network layer mocked out, is that the percentile/latency/throughput math
and status-code bucketing are correct, so a real run's numbers can be
trusted.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import loadtest_query as lt


def test_percentile_matches_known_values():
    values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    assert lt._percentile(values, 50) in (50, 60)  # median-ish, index-based
    assert lt._percentile(values, 100) == 100
    assert lt._percentile([], 95) == 0.0


def test_percentile_single_value():
    assert lt._percentile([42.0], 95) == 42.0


def _fake_fire_one(elapsed_by_call):
    """Returns a _fire_one replacement that yields the next canned result."""
    calls = iter(elapsed_by_call)

    def _inner(base_url, token, course_code, question):
        return next(calls)

    return _inner


def test_run_level_aggregates_success_latencies_only():
    """Errors and non-200s must not pollute the latency percentiles, but
    must still be counted in status_counts and total_requests."""
    canned = [
        {"status_code": 200, "elapsed_ms": 100.0, "server_latency_ms": 90, "error": None},
        {"status_code": 200, "elapsed_ms": 200.0, "server_latency_ms": 180, "error": None},
        {"status_code": 429, "elapsed_ms": 5.0, "server_latency_ms": None, "error": None},
        {"status_code": None, "elapsed_ms": 300.0, "server_latency_ms": None, "error": "timeout"},
    ]
    users = [{"email": "a@x.com", "access_token": "t1"}, {"email": "b@x.com", "access_token": "t2"}]

    with patch.object(lt, "_fire_one", side_effect=_fake_fire_one(canned)):
        result = lt._run_level(
            base_url="http://fake",
            users=users,
            course_code="CSIT321",
            concurrency=2,
            requests_per_user=2,
            questions=["irrelevant question text here"],
        )

    assert result["total_requests"] == 4
    assert result["success_count"] == 2
    assert result["status_counts"]["200"] == 2
    assert result["status_counts"]["429"] == 1
    assert result["status_counts"]["connection_error"] == 1
    assert result["latency_ms"]["mean"] == 150.0
    assert result["latency_ms"]["max"] == 200.0


def test_run_level_all_errors_reports_none_latencies_not_crash():
    canned = [
        {"status_code": 503, "elapsed_ms": 10.0, "server_latency_ms": None, "error": None},
        {"status_code": 503, "elapsed_ms": 12.0, "server_latency_ms": None, "error": None},
    ]
    users = [{"email": "a@x.com", "access_token": "t1"}]

    with patch.object(lt, "_fire_one", side_effect=_fake_fire_one(canned)):
        result = lt._run_level(
            base_url="http://fake",
            users=users,
            course_code="CSIT321",
            concurrency=1,
            requests_per_user=2,
            questions=["irrelevant question text here"],
        )

    assert result["success_count"] == 0
    assert result["latency_ms"]["mean"] is None
    assert result["latency_ms"]["p95"] is None


def test_default_questions_are_not_ambiguous():
    """None of the built-in sample questions should trip
    src/api/routes/query.py's _is_ambiguous() check (>=2 words, no
    ambiguous-pattern substring), or every real run would get 422s."""
    from src.api.routes.query import _is_ambiguous

    for question in lt.DEFAULT_QUESTIONS:
        assert not _is_ambiguous(question), f"question would be rejected as ambiguous: {question!r}"
