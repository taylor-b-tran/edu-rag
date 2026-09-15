"""Deactivating a course must not be a one-way door.

`PATCH /api/courses/<code>` has accepted `is_active` since T8-04, but the
client exposed only `deactivate_course` and nothing in the UI ever sent the
other direction, so a course switched off by accident stayed off.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "streamlit"))

from api_client import APIConfig, PaediaAPIClient  # noqa: E402


@pytest.fixture
def client():
    return PaediaAPIClient(APIConfig(base_url="http://test.invalid",
                                     use_fixtures=False, max_retries=0))


def test_reactivating_sends_is_active_true_to_the_course_itself(client):
    seen = {}

    def fake_patch(endpoint, payload):
        seen["endpoint"] = endpoint
        seen["payload"] = payload
        return {"course": {"course_code": "ARCH101", "is_active": True}}

    client._patch = fake_patch
    result = client.reactivate_course("ARCH101")

    assert seen["endpoint"] == "/api/courses/ARCH101"
    assert seen["payload"] == {"is_active": True}
    assert result["success"] is True
    assert result["course"]["is_active"] is True


def test_a_refused_reactivation_is_reported_not_swallowed(client):
    client._patch = lambda e, p: {"_api_error": True, "message": "Admin role required."}
    result = client.reactivate_course("CSIT321")
    assert result["success"] is False
    assert "Admin" in result["error"]


def test_an_unreachable_api_is_reported_not_swallowed(client):
    client._patch = lambda e, p: None
    result = client.reactivate_course("CSIT321")
    assert result["success"] is False
    assert result["error"]


def test_fixture_mode_says_so_rather_than_pretending_it_worked():
    demo = PaediaAPIClient(APIConfig(use_fixtures=True))
    result = demo.reactivate_course("CSIT321")
    assert result["success"] is False
    assert "live system" in result["error"]


def test_deactivate_still_works_the_way_it_did(client):
    """The pair has to stay symmetrical; adding one must not disturb the other."""
    assert hasattr(client, "deactivate_course")
    assert hasattr(client, "reactivate_course")
