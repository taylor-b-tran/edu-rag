"""Demo account seeding against a real PostgreSQL schema — opt-in, disposable, never production tables.

Run with PAEDIA_TEST_POSTGRES_HOST pointing at a throwaway server. Seeding relies on
INSERT ... ON CONFLICT ... RETURNING to know whether it created an account, which only a real
server can confirm.
"""
import logging
import os
import uuid
from contextlib import contextmanager

import bcrypt
import psycopg
from psycopg.rows import dict_row
import pytest

from src.api import db

pytestmark = pytest.mark.skipif(not os.getenv("PAEDIA_TEST_POSTGRES_HOST"),
                                reason="Opt-in isolated PostgreSQL seeding tests")
ENV_KEYS = ("PAEDIA_DEMO_ADMIN_PASSWORD", "PAEDIA_DEMO_LECTURER_PASSWORD",
            "PAEDIA_DEMO_STUDENT_PASSWORD")
LITERALS = ("admin123", "lecturer123", "student123")


@pytest.fixture
def pg(monkeypatch):
    schema = "qa_seed_" + uuid.uuid4().hex
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
        with psycopg.connect(**config, options=f"-c search_path={schema},public") as conn:
            yield conn

    monkeypatch.setattr(db, "connect", isolated)
    for key in ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    try:
        yield isolated
    finally:
        with psycopg.connect(**config) as conn:
            conn.execute(psycopg.sql.SQL("DROP SCHEMA {} CASCADE").format(psycopg.sql.Identifier(schema)))


def _hashes(pg):
    with pg() as conn:
        return {r["email"]: r["password_hash"] for r in
                conn.execute("SELECT email, password_hash FROM users").fetchall()}


def test_unset_passwords_create_accounts_nobody_can_sign_into(pg, caplog):
    with caplog.at_level(logging.WARNING, logger="src.api.db"):
        db.init_schema()
    hashes = _hashes(pg)
    assert set(hashes) == {"admin@uow.edu.au", "lecturer@uow.edu.au", "student@uow.edu.au"}
    for stored in hashes.values():
        for literal in LITERALS:
            assert not bcrypt.checkpw(literal.encode(), stored.encode())
    warned = " ".join(r.getMessage() for r in caplog.records)
    for key in ENV_KEYS:
        assert key in warned


def test_a_restart_without_passwords_changes_nothing_and_says_nothing(pg, caplog):
    db.init_schema()
    before = _hashes(pg)
    caplog.clear()
    with caplog.at_level(logging.WARNING, logger="src.api.db"):
        db.init_schema()
    assert _hashes(pg) == before
    assert not [r for r in caplog.records if "random password" in r.getMessage()]


def test_setting_a_password_later_makes_the_account_usable(pg, monkeypatch):
    db.init_schema()
    monkeypatch.setenv("PAEDIA_DEMO_STUDENT_PASSWORD", "operator-chosen-secret")
    db.init_schema()
    stored = _hashes(pg)["student@uow.edu.au"]
    assert bcrypt.checkpw(b"operator-chosen-secret", stored.encode())
