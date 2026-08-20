"""The operational endpoints used to answer anyone (T8-30).

/api/metrics, /api/admin/stats, /api/admin/audit-logs and /api/logs called no
validate_bearer at all, so any unauthenticated caller could read them. They are
now admin-only. /api/health deliberately stays open, because the container
healthcheck calls it without a token.
"""
from __future__ import annotations

import pytest

from src.api.app import create_app


OPS_ENDPOINTS = [
    "/api/metrics",
    "/api/admin/stats",
    "/api/admin/audit-logs",
    "/api/logs",
]


@pytest.fixture
def client():
    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client()


def _token(client, email: str, password: str) -> str:
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"login failed: {resp.get_json()}"
    return resp.get_json()["access_token"]


@pytest.mark.parametrize("endpoint", OPS_ENDPOINTS)
def test_ops_endpoint_rejects_anonymous(client, endpoint):
    assert client.get(endpoint).status_code == 401


@pytest.mark.parametrize("endpoint", OPS_ENDPOINTS)
def test_ops_endpoint_rejects_non_admin(client, endpoint):
    token = _token(client, "student@uow.edu.au", "student123")
    resp = client.get(endpoint, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


@pytest.mark.parametrize("endpoint", OPS_ENDPOINTS)
def test_ops_endpoint_allows_admin(client, endpoint):
    token = _token(client, "admin@uow.edu.au", "admin123")
    resp = client.get(endpoint, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


def test_health_stays_open_for_the_container_healthcheck(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"
