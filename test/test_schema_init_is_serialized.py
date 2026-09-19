"""Schema creation is serialized, and the demo seed runs under the same lock.

These pin the shape of `init_schema`, not its effect on a database: a real
collision needs two processes and a live Postgres. What they catch is the
refactor that quietly puts part of start-up back outside the lock, which is how
the seeding came to race in the first place while the table creation did not.
"""
from __future__ import annotations

import contextlib

import pytest

from src.api import db


class Recorder:
    """A stand-in connection that writes down what start-up does, in order."""

    def __init__(self):
        self.events: list[str] = []
        self.statements: list[str] = []
        self.cursors = 0

    # -- connection ------------------------------------------------------
    @contextlib.contextmanager
    def transaction(self):
        self.events.append("begin")
        yield self
        self.events.append("commit")

    @contextlib.contextmanager
    def cursor(self):
        self.cursors += 1
        self.events.append("cursor")
        yield self

    # -- cursor ----------------------------------------------------------
    def execute(self, statement, params=None):
        text = " ".join(str(statement).split())
        self.statements.append(text)
        self.events.append(text[:40])
        return self

    def fetchone(self):
        return None

    def fetchall(self):
        return []


@pytest.fixture
def started(monkeypatch):
    recorder = Recorder()

    # Password hashing is the slow part of start-up. Record when it happens so
    # the tests can say where it happened relative to the transaction.
    real_hash = db.bcrypt.hashpw

    def timed_hash(password, salt):
        recorder.events.append("hash")
        return real_hash(password, salt)

    monkeypatch.setattr(db.bcrypt, "hashpw", timed_hash)

    @contextlib.contextmanager
    def fake_connect():
        yield recorder

    monkeypatch.setattr(db, "connect", fake_connect)
    db.init_schema()
    return recorder


def test_the_lock_is_taken_before_anything_is_created(started):
    taken = next(i for i, s in enumerate(started.statements)
                 if "pg_advisory_xact_lock" in s)
    created = next(i for i, s in enumerate(started.statements)
                   if "CREATE TABLE" in s)
    assert taken < created
    assert started.events.index("begin") < started.events.index("cursor")


def test_waiting_for_the_lock_is_bounded(started):
    # Without this, a worker that wedges while holding the lock makes every
    # other worker wait with no limit, and each restart waits again.
    bound = next((s for s in started.statements if "lock_timeout" in s), None)
    assert bound is not None, "the wait for the schema lock has no timeout"
    assert started.statements.index(bound) < next(
        i for i, s in enumerate(started.statements) if "pg_advisory_xact_lock" in s)


def test_every_schema_block_runs_while_the_lock_is_held(started):
    blocks = [db.SCHEMA, db.AUTH_SCHEMA, db.SESSION_SCHEMA, db.FEEDBACK_SCHEMA]
    for block in blocks:
        expected = " ".join(block.split())
        assert expected in started.statements

    # Nothing may be created after the transaction ends, because the lock is
    # released with it.
    assert started.events[-1] == "commit"


def test_the_demo_seed_runs_under_the_same_lock(started):
    seeded = [s for s in started.statements if "INSERT INTO users" in s]
    assert seeded, "the demo accounts are no longer seeded during start-up"

    # One cursor, one transaction: the seed shares them with the schema rather
    # than opening its own connection alongside another worker's.
    assert started.cursors == 1
    assert started.events.count("begin") == 1
    for statement in seeded:
        assert started.events.index(statement[:40]) < started.events.index("commit")


def test_the_seed_still_takes_a_cursor_rather_than_making_one():
    # A signature check, so the seed cannot drift back to its own connection
    # without this failing.
    import inspect
    assert list(inspect.signature(db._seed_demo_auth_data).parameters) == ["cur", "rows"]


def test_passwords_are_hashed_before_the_transaction_opens(started):
    # Hashing inside the transaction holds the table locks the schema took for
    # as long as hashing takes, which stalls the other worker's reads.
    assert "hash" in started.events, "the demo passwords are no longer hashed"
    assert started.events.index("begin") > max(
        i for i, e in enumerate(started.events) if e == "hash")


def test_only_the_wait_for_the_schema_lock_is_timed_out(started):
    # The bound belongs to the advisory wait. Leaving it in place over the DDL
    # turns a restart during ordinary traffic into a failed start, reported as
    # an unreachable database.
    timeouts = [i for i, s in enumerate(started.statements) if "lock_timeout" in s]
    assert len(timeouts) == 2, "expected the timeout to be set and then cleared"
    first_ddl = next(i for i, s in enumerate(started.statements) if "CREATE TABLE" in s)
    assert timeouts[1] < first_ddl
    assert "0" in started.statements[timeouts[1]]
