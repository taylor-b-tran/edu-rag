"""Opt-in real PostgreSQL checks in a disposable schema, never production tables.

Run with PAEDIA_TEST_POSTGRES_HOST=postgres inside the API container. Normal
unit tests leave this unset. Each test uses fresh connections, like workers.
"""
import os
import uuid
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import psycopg
from psycopg.rows import dict_row
import pytest

from src.api import db

pytestmark = pytest.mark.skipif(not os.getenv("PAEDIA_TEST_POSTGRES_HOST"),
                                reason="Opt-in isolated PostgreSQL transaction tests")
PAYLOAD = {"user_id": "qa-transaction", "email": "qa@example.invalid",
           "role": "student", "enrolled_courses": [], "family_id": "family-a"}


@pytest.fixture
def pg(monkeypatch):
    schema = "qa_tokens_" + uuid.uuid4().hex
    config = dict(host=os.environ["PAEDIA_TEST_POSTGRES_HOST"],
                  port=os.getenv("POSTGRES_PORT", "5432"),
                  dbname=os.getenv("POSTGRES_DB", "edurag"),
                  user=os.getenv("POSTGRES_USER", "edurag"),
                  password=os.environ["POSTGRES_PASSWORD"],
                  autocommit=True, row_factory=dict_row)
    with psycopg.connect(**config) as conn:
        conn.execute(psycopg.sql.SQL("CREATE SCHEMA {}").format(psycopg.sql.Identifier(schema)))

    @contextmanager
    def isolated():
        with psycopg.connect(**config, options=f"-c search_path={schema}") as conn:
            yield conn

    monkeypatch.setattr(db, "connect", isolated)
    with isolated() as conn:
        conn.execute(db.SESSION_SCHEMA)
    try:
        yield isolated
    finally:
        # Exact randomly generated test schema only; no production relations.
        with psycopg.connect(**config) as conn:
            conn.execute(psycopg.sql.SQL("DROP SCHEMA {} CASCADE").format(psycopg.sql.Identifier(schema)))


def issue():
    db.insert_token_pair("access-old", "refresh-old", PAYLOAD, 3600, 86400)


def rotate(i=0):
    return db.rotate_token_pair("refresh-old", f"access-{i}", f"refresh-{i}", PAYLOAD, 3600, 86400)


def count(pg, table):
    with pg() as conn:
        return conn.execute(f"SELECT count(*) AS n FROM {table}").fetchone()["n"]


def test_same_refresh_concurrently_mints_exactly_one_pair(pg):
    issue()
    with ThreadPoolExecutor(max_workers=12) as pool:
        assert sum(pool.map(rotate, range(24))) == 1
    assert count(pg, "refresh_tokens") == 1
    assert count(pg, "access_tokens") == 2  # original access remains a logout handle


def test_logout_wins_before_rotation(pg):
    issue()
    db.revoke_login("access-old", None)
    assert not rotate()
    assert count(pg, "access_tokens") == count(pg, "refresh_tokens") == 0


def test_logout_waits_for_inflight_rotation_and_revokes_new_pair(pg, monkeypatch):
    issue()
    entered, release, logout_started = Event(), Event(), Event()
    insert = db._insert_pair

    def paused(*args):
        entered.set()
        assert release.wait(10)
        return insert(*args)

    def logout():
        logout_started.set()
        db.revoke_login("access-old", None)

    monkeypatch.setattr(db, "_insert_pair", paused)
    with ThreadPoolExecutor(max_workers=2) as pool:
        renewal = pool.submit(rotate)
        assert entered.wait(10)
        revocation = pool.submit(logout)
        assert logout_started.wait(10)
        release.set()
        assert renewal.result(timeout=10)
        revocation.result(timeout=10)
    assert count(pg, "access_tokens") == count(pg, "refresh_tokens") == 0


def test_uncontrolled_refresh_logout_races_leave_no_credentials(pg):
    for _ in range(20):
        issue()
        with ThreadPoolExecutor(max_workers=2) as pool:
            renewal = pool.submit(rotate)
            revocation = pool.submit(db.revoke_login, "access-old", None)
            renewal.result(timeout=10)
            revocation.result(timeout=10)
        assert count(pg, "access_tokens") == count(pg, "refresh_tokens") == 0


def test_failed_rotation_rolls_back_consumption(pg, monkeypatch):
    issue()
    def fail(*args):
        raise RuntimeError("injected insert failure")
    monkeypatch.setattr(db, "_insert_pair", fail)
    with pytest.raises(RuntimeError):
        rotate()
    assert db.get_token("refresh_tokens", "refresh-old") is not None
    assert count(pg, "access_tokens") == 1


@pytest.mark.parametrize("access,refresh", [("access-old", None), (None, "refresh-old")])
def test_either_credential_revokes_its_family_only(pg, access, refresh):
    issue()
    db.insert_token_pair("other-access", "other-refresh", {**PAYLOAD, "family_id": "other"}, 3600, 86400)
    db.revoke_login(access, refresh)
    assert db.get_token("access_tokens", "access-old") is None
    assert db.get_token("refresh_tokens", "refresh-old") is None
    assert db.get_token("access_tokens", "other-access") is not None


def test_expired_access_still_revokes_its_refresh(pg):
    db.insert_token_pair("access-old", "refresh-old", PAYLOAD, -1, 86400)
    db.revoke_login("access-old", None)
    assert count(pg, "refresh_tokens") == 0


def test_schema_invalidates_only_legacy_credentials_idempotently(pg):
    issue()
    with pg() as conn:
        for table in ("access_tokens", "refresh_tokens"):
            conn.execute(f"INSERT INTO {table} (token, user_id, expires_at) VALUES ('legacy', 'qa', NOW() + INTERVAL '1 day')")
        conn.execute(db.SESSION_SCHEMA)
        conn.execute(db.SESSION_SCHEMA)
    assert count(pg, "access_tokens") == count(pg, "refresh_tokens") == 1
    assert db.get_token("refresh_tokens", "refresh-old") is not None


# --- pruning expired credentials ----------------------------------------------

def _pair(access, refresh, family, access_ttl, refresh_ttl):
    db.insert_token_pair(access, refresh, {**PAYLOAD, "family_id": family},
                         access_ttl, refresh_ttl)


def test_prune_removes_a_login_whose_credentials_have_all_expired(pg):
    _pair("access-dead", "refresh-dead", "family-dead", -120, -60)
    assert db.prune_expired_tokens() == 2
    assert count(pg, "access_tokens") == count(pg, "refresh_tokens") == 0


def test_prune_keeps_live_credentials(pg):
    issue()
    assert db.prune_expired_tokens() == 0
    assert count(pg, "access_tokens") == count(pg, "refresh_tokens") == 1


def test_prune_keeps_an_expired_access_token_while_its_refresh_token_lives(pg):
    # The access token is the logout handle: revoke_login finds the family
    # through it, so removing it would leave the live refresh token unrevokable.
    _pair("access-lapsed", "refresh-live", "family-live", -120, 86400)
    assert db.prune_expired_tokens() == 0
    assert db.get_token("access_tokens", "access-lapsed") is not None


def test_logout_through_a_lapsed_access_token_still_works_after_pruning(pg):
    _pair("access-lapsed", "refresh-live", "family-live", -120, 86400)
    db.prune_expired_tokens()
    db.revoke_login("access-lapsed", None)
    assert count(pg, "access_tokens") == count(pg, "refresh_tokens") == 0


def test_prune_touches_only_the_dead_family(pg):
    _pair("access-dead", "refresh-dead", "family-dead", -120, -60)
    _pair("access-live", "refresh-live", "family-live", 3600, 86400)
    assert db.prune_expired_tokens() == 2
    assert db.get_token("access_tokens", "access-live") is not None
    assert db.get_token("refresh_tokens", "refresh-live") is not None
    assert db.get_token("access_tokens", "access-dead") is None


def test_an_expired_refresh_token_goes_even_if_its_access_token_does_not_exist(pg):
    _pair("access-dead", "refresh-dead", "family-dead", -120, -60)
    with pg() as conn:
        conn.execute("DELETE FROM access_tokens")
    assert db.prune_expired_tokens() == 1
    assert count(pg, "refresh_tokens") == 0
