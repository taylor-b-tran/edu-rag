"""An API worker must not come up without Postgres and still look healthy.

After a reboot Docker starts every container at the same moment and does not
honour depends_on, so gunicorn can import the app before Postgres accepts
connections. APIState used to try once and fall back to in-memory state for the
life of the worker: every login refused, nothing persisted, /api/health 200.

With PAEDIA_DB_STARTUP_TIMEOUT_SECONDS set, the worker waits for the database and
refuses to start without it. Unset, nothing changes - the rest of this suite runs
without a database on purpose.
"""
from __future__ import annotations

import time as real_time
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.api import db as db_mod
from src.api import state as state_mod
from src.api.state import APIState


@pytest.fixture(autouse=True)
def no_warmup_and_no_timeout(monkeypatch):
    monkeypatch.setenv("EDURAG_OLLAMA_WARMUP", "false")
    monkeypatch.delenv("PAEDIA_DB_STARTUP_TIMEOUT_SECONDS", raising=False)


class Clock:
    """Monotonic time that only moves when the code under test sleeps."""

    def __init__(self):
        self.now = 1000.0
        self.sleeps: list[float] = []

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


@pytest.fixture
def clock(monkeypatch):
    fake = Clock()
    monkeypatch.setattr(state_mod, "time", SimpleNamespace(
        monotonic=fake.monotonic, sleep=fake.sleep,
        time=real_time.time, strftime=real_time.strftime, gmtime=real_time.gmtime))
    return fake


class StartingPostgres:
    """Refuses the first `failures` connections, then behaves like an empty store."""

    def __init__(self, failures):
        self.failures = failures
        self.attempts = 0
        self.resets = 0

    def init_schema(self):
        self.attempts += 1
        if self.attempts <= self.failures:
            raise ConnectionRefusedError("the database system is starting up")

    def reset_connection_state(self):
        self.resets += 1


def install(monkeypatch, postgres):
    monkeypatch.setattr(db_mod, "init_schema", postgres.init_schema)
    monkeypatch.setattr(db_mod, "reset_connection_state", postgres.reset_connection_state)
    for loader, empty in (("load_all_documents", list), ("load_all_jobs", dict),
                          ("load_all_access_tokens", dict), ("load_all_refresh_tokens", dict),
                          ("load_all_sessions", dict)):
        monkeypatch.setattr(db_mod, loader, lambda empty=empty: empty())


# --- the default is unchanged --------------------------------------------

def test_without_a_timeout_one_failed_attempt_still_falls_back(monkeypatch, clock):
    postgres = StartingPostgres(failures=1)
    install(monkeypatch, postgres)

    state = APIState()

    assert state.db_available is False
    assert postgres.attempts == 1
    assert clock.sleeps == []


@pytest.mark.parametrize("value", ["0", "", "not-a-number", "-5"])
def test_zero_blank_or_invalid_timeouts_mean_no_wait(monkeypatch, clock, value):
    monkeypatch.setenv("PAEDIA_DB_STARTUP_TIMEOUT_SECONDS", value)
    postgres = StartingPostgres(failures=1)
    install(monkeypatch, postgres)

    assert APIState().db_available is False
    assert postgres.attempts == 1


# --- the reboot race ------------------------------------------------------

def test_a_worker_that_starts_first_waits_for_postgres(monkeypatch, clock):
    monkeypatch.setenv("PAEDIA_DB_STARTUP_TIMEOUT_SECONDS", "120")
    postgres = StartingPostgres(failures=3)
    install(monkeypatch, postgres)

    state = APIState()

    assert state.db_available is True
    assert postgres.attempts == 4
    assert len(clock.sleeps) == 3


def test_each_retry_starts_from_a_fresh_connection(monkeypatch, clock):
    """Otherwise the request-path circuit breaker refuses to probe again for
    twenty seconds, and the pool keeps its own reconnect backoff."""
    monkeypatch.setenv("PAEDIA_DB_STARTUP_TIMEOUT_SECONDS", "120")
    postgres = StartingPostgres(failures=2)
    install(monkeypatch, postgres)

    APIState()

    assert postgres.resets == 2


def test_no_database_within_the_timeout_refuses_to_start(monkeypatch, clock):
    """Raising here makes the gunicorn worker fail to boot, so the container
    exits and Docker's restart policy tries again - instead of a worker that
    looks healthy and cannot log anyone in."""
    monkeypatch.setenv("PAEDIA_DB_STARTUP_TIMEOUT_SECONDS", "10")
    postgres = StartingPostgres(failures=10_000)
    install(monkeypatch, postgres)

    with pytest.raises(RuntimeError, match="refusing to run without it"):
        APIState()

    assert postgres.attempts > 1
    assert sum(clock.sleeps) <= 10


def test_the_deployment_turns_the_wait_on():
    """The wait only protects the shared host if the api service sets it."""
    yaml = pytest.importorskip("yaml")
    compose = yaml.safe_load((Path(__file__).resolve().parents[1] / "docker-compose.yml")
                             .read_text(encoding="utf-8"))
    value = str(compose["services"]["api"]["environment"]["PAEDIA_DB_STARTUP_TIMEOUT_SECONDS"])
    default = value.rsplit(":-", 1)[-1].rstrip("}")
    assert float(default) > 0


# --- and health says which kind of worker answered -----------------------

@pytest.fixture
def api(monkeypatch):
    from src.api.app import create_app
    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client(), app.config["EDURAG_API_STATE"]


@pytest.mark.parametrize("available,expected", [(False, "unavailable"), (True, "connected")])
def test_health_reports_whether_this_worker_has_its_database(api, available, expected):
    client, state = api
    state._db_available = available

    body = client.get("/api/health").get_json()

    assert body["status"] == "ok"
    assert body["database"] == expected
