from __future__ import annotations

import json
import logging
import os
import time
from contextlib import contextmanager
from typing import Any, Iterator

import bcrypt
import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool, PoolTimeout

logger = logging.getLogger(__name__)


def _conninfo() -> str:
    return (
        f"host={os.environ.get('POSTGRES_HOST', 'postgres')} "
        f"port={os.environ.get('POSTGRES_PORT', '5432')} "
        f"dbname={os.environ.get('POSTGRES_DB', 'edurag')} "
        f"user={os.environ.get('POSTGRES_USER', 'edurag')} "
        f"password={os.environ.get('POSTGRES_PASSWORD', 'edurag_dev_password')}"
    )

_POOL: ConnectionPool | None = None

_pg_last_failure: float = 0.0
_PG_CIRCUIT_COOLDOWN = float(os.environ.get("POSTGRES_CIRCUIT_COOLDOWN", "20"))


def _pool() -> ConnectionPool:
    global _POOL
    if _POOL is None:
        min_size = int(os.environ.get("POSTGRES_POOL_MIN_SIZE", "2"))
        max_size = int(os.environ.get("POSTGRES_POOL_MAX_SIZE", "10"))
        
        acquire_timeout = float(os.environ.get("POSTGRES_POOL_TIMEOUT", "3"))
        _POOL = ConnectionPool(
            conninfo=_conninfo(),
            min_size=min_size,
            max_size=max_size,
            timeout=acquire_timeout,
            kwargs={"row_factory": dict_row, "autocommit": True},
            open=True,
        )
        logger.info("Postgres connection pool opened (min=%d, max=%d, timeout=%.1fs).",
                    min_size, max_size, acquire_timeout)
    return _POOL


class PostgresCircuitOpenError(RuntimeError):
    """Raised instead of re-probing the pool while the circuit breaker is
    open. Behaves like any other connection failure to existing callers —
    everything that catches Exception around connect() (APIState, db.init_schema)
    already handles this the same way it handled a real connection error."""


@contextmanager
def connect() -> Iterator[psycopg.Connection]:
    global _pg_last_failure
    if _pg_last_failure and (time.monotonic() - _pg_last_failure) < _PG_CIRCUIT_COOLDOWN:
        raise PostgresCircuitOpenError(
            f"Postgres marked unreachable {round(time.monotonic() - _pg_last_failure, 1)}s ago; "
            f"not retrying for another {round(_PG_CIRCUIT_COOLDOWN - (time.monotonic() - _pg_last_failure), 1)}s."
        )
    try:
        with _pool().connection() as conn:
            _pg_last_failure = 0.0
            yield conn
    except (PoolTimeout, psycopg.OperationalError):
        _pg_last_failure = time.monotonic()
        raise


SCHEMA = """
CREATE TABLE IF NOT EXISTS uploaded_documents (
    document_id      TEXT PRIMARY KEY,
    course_id        TEXT NOT NULL,
    course_code      TEXT,
    course_uuid      TEXT,
    filename         TEXT NOT NULL,
    original_filename TEXT,
    file_type        TEXT,
    file_size_bytes  BIGINT,
    status           TEXT NOT NULL DEFAULT 'queued',
    indexing_status  TEXT NOT NULL DEFAULT 'queued',
    indexing_job_id  TEXT,
    chunks           INTEGER,
    uploaded_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    extra            JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS uploaded_documents_course_idx
    ON uploaded_documents (course_id);

CREATE TABLE IF NOT EXISTS indexing_jobs (
    job_id          TEXT PRIMARY KEY,
    document_id     TEXT NOT NULL REFERENCES uploaded_documents(document_id) ON DELETE CASCADE,
    status          TEXT NOT NULL DEFAULT 'queued',
    progress_percent INTEGER NOT NULL DEFAULT 0,
    error           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS indexing_jobs_document_idx
    ON indexing_jobs (document_id);
"""

# Sprint 7 (T02): the auth tables from db/migrations/001_initial_schema.sql,
# applied here rather than by a migration runner (none exists yet). Only the
# non-colliding tables — users/courses/course_memberships — are included.
# documents/indexing_jobs from that file are deliberately left out: they'd
# collide with the simpler, already-live uploaded_documents/indexing_jobs
# shape above.
AUTH_SCHEMA = """
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    role TEXT NOT NULL CHECK (role IN ('student', 'lecturer', 'admin')),
    password_hash VARCHAR(60) NOT NULL,
    last_login_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS courses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_code VARCHAR(32) NOT NULL UNIQUE,
    course_name VARCHAR(255) NOT NULL,
    description TEXT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS course_memberships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    membership_role TEXT NOT NULL CHECK (membership_role IN ('student', 'lecturer')),
    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, course_id)
);

-- Sprint 8 (T8-04): course ownership. Added as an ALTER rather than a column
-- in the CREATE above so an existing database picks it up too; there is still
-- no migration runner, and this file is replayed on every start.
-- Nullable on purpose: courses that predate this own nobody, and stay
-- admin-only until an owner is set. ON DELETE SET NULL keeps a course alive
-- when its lecturer's account goes away.
ALTER TABLE courses ADD COLUMN IF NOT EXISTS owner_id UUID NULL
    REFERENCES users(id) ON DELETE SET NULL;

-- Sprint 8 (T8-08): live-reloadable configuration. Scope is either the string
-- 'global' or a course_code, so one table covers both tiers and a per-course
-- row simply shadows the global one.
CREATE TABLE IF NOT EXISTS settings (
    scope      TEXT NOT NULL,
    key        TEXT NOT NULL,
    value      JSONB NOT NULL,
    updated_by TEXT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (scope, key)
);

CREATE INDEX IF NOT EXISTS idx_courses_owner_id ON courses(owner_id);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_course_memberships_user_id ON course_memberships(user_id);
CREATE INDEX IF NOT EXISTS idx_course_memberships_course_id ON course_memberships(course_id);
"""

# T8-24: tokens, chat sessions/messages, and rate-limit hits were all
# in-memory dicts on APIState (access_tokens, refresh_tokens, sessions) or a
# module-level dict in routes/query.py (_RATE_STORE). Every one of those was
# lost on restart — a routine gunicorn worker recycle (T8-23) or a
# deployment would silently log the whole class out and forget every open
# chat. Moving them to Postgres, the same store everything else already
# survives a restart in, fixes that.
SESSION_SCHEMA = """
CREATE TABLE IF NOT EXISTS access_tokens (
    token             TEXT PRIMARY KEY,
    user_id           TEXT NOT NULL,
    email             TEXT,
    role              TEXT,
    enrolled_courses  JSONB NOT NULL DEFAULT '[]'::jsonb,
    issued_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at        TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS refresh_tokens (
    token             TEXT PRIMARY KEY,
    user_id           TEXT NOT NULL,
    email             TEXT,
    role              TEXT,
    enrolled_courses  JSONB NOT NULL DEFAULT '[]'::jsonb,
    issued_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at        TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS chat_sessions (
    session_id  TEXT PRIMARY KEY,
    user_id     TEXT,
    course_id   TEXT,
    archived    BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chat_messages (
    message_id  TEXT PRIMARY KEY,
    session_id  TEXT NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
    question    TEXT,
    answer      TEXT,
    sources     JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS chat_messages_session_idx ON chat_messages(session_id);

-- One row per request that counted toward the caller's rate limit. Old rows
-- are pruned in check_and_record_rate() rather than by a cron job — simplest
-- thing that works at class-sized traffic.
CREATE TABLE IF NOT EXISTS rate_limit_hits (
    id        BIGSERIAL PRIMARY KEY,
    rate_key  TEXT NOT NULL,
    hit_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS rate_limit_hits_key_idx ON rate_limit_hits (rate_key, hit_at);
"""

# Same three demo accounts the fixture file has always used, now with a
# distinct real bcrypt hash per password instead of one shared placeholder.
# Demo account passwords come from the environment. They used to be literals
# here, printed on the login screen and listed in the README, which made every
# one of them public knowledge - including the admin. The fallbacks keep a
# local checkout usable; any instance more than one person can reach must set
# these in its own .env.
def _demo_password(env_key: str, fallback: str) -> tuple[str, bool]:
    """Return (password, came_from_env). Only an explicitly configured password
    is written over an existing account - otherwise every restart would reset
    whatever the instance had been changed to."""
    value = (os.environ.get(env_key) or "").strip()
    return (value, True) if value else (fallback, False)


_DEMO_USERS = [
    ("admin_demo", "admin@uow.edu.au", "admin",
     *_demo_password("PAEDIA_DEMO_ADMIN_PASSWORD", "admin123")),
    ("lecturer_demo", "lecturer@uow.edu.au", "lecturer",
     *_demo_password("PAEDIA_DEMO_LECTURER_PASSWORD", "lecturer123")),
    ("student_demo", "student@uow.edu.au", "student",
     *_demo_password("PAEDIA_DEMO_STUDENT_PASSWORD", "student123")),
]
_DEMO_COURSES = [
    ("CSIT321", "Project"),
    ("CSIT214", "Database Systems"),
]


def _seed_demo_auth_data() -> None:
    with connect() as conn:
        with conn.cursor() as cur:
            for username, email, role, password, from_env in _DEMO_USERS:
                password_hash = bcrypt.hashpw(
                    password.encode("utf-8"), bcrypt.gensalt()
                ).decode("utf-8")
                conflict = (
                    "DO UPDATE SET password_hash = EXCLUDED.password_hash, updated_at = NOW()"
                    if from_env else "DO NOTHING"
                )
                cur.execute(
                    f"""
                    INSERT INTO users (username, email, role, password_hash)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (email) {conflict}
                    """,
                    (username, email, role, password_hash),
                )
            for course_code, course_name in _DEMO_COURSES:
                cur.execute(
                    """
                    INSERT INTO courses (course_code, course_name)
                    VALUES (%s, %s)
                    ON CONFLICT (course_code) DO NOTHING
                    """,
                    (course_code, course_name),
                )
            # Student and lecturer are enrolled in both demo courses, matching
            # fixtures/sample_responses.json so behaviour doesn't change
            # depending on which backend actually answered the login.
            cur.execute(
                """
                INSERT INTO course_memberships (user_id, course_id, membership_role)
                SELECT u.id, c.id, u.role
                  FROM users u
                  CROSS JOIN courses c
                 WHERE u.role IN ('student', 'lecturer')
                ON CONFLICT (user_id, course_id) DO NOTHING
                """
            )


def init_schema() -> None:
    try:
        with connect() as conn:
            with conn.cursor() as cur:
                cur.execute(SCHEMA)
                cur.execute(AUTH_SCHEMA)
                cur.execute(SESSION_SCHEMA)
        _seed_demo_auth_data()
        logger.info(
            "Postgres schema initialised (uploaded_documents, indexing_jobs, "
            "users, courses, course_memberships, access_tokens, refresh_tokens, "
            "chat_sessions, chat_messages, rate_limit_hits)."
        )
    except Exception as exc:
        logger.warning(
            "Postgres schema init failed (%s: %s). API will fall back to in-memory state.",
            type(exc).__name__, exc,
        )
        raise


def insert_document(doc: dict[str, Any]) -> None:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO uploaded_documents
                  (document_id, course_id, course_code, course_uuid, filename,
                   original_filename, file_type, file_size_bytes,
                   status, indexing_status, indexing_job_id, chunks, extra)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (document_id) DO NOTHING
                """,
                (
                    doc.get("document_id"),
                    doc.get("course_id"),
                    doc.get("course_code"),
                    doc.get("course_uuid"),
                    doc.get("filename"),
                    doc.get("original_filename"),
                    doc.get("file_type"),
                    doc.get("file_size_bytes"),
                    doc.get("status", "queued"),
                    doc.get("indexing_status", "queued"),
                    doc.get("indexing_job_id"),
                    doc.get("chunks"),
                    json.dumps({k: v for k, v in doc.items() if k not in {
                        "document_id", "course_id", "course_code", "course_uuid",
                        "filename", "original_filename", "file_type", "file_size_bytes",
                        "status", "indexing_status", "indexing_job_id", "chunks",
                        "uploaded_at", "id",
                    }}),
                ),
            )


def insert_job(job: dict[str, Any]) -> None:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO indexing_jobs
                  (job_id, document_id, status, progress_percent, error)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (job_id) DO NOTHING
                """,
                (
                    job.get("job_id"),
                    job.get("document_id"),
                    job.get("status", "queued"),
                    int(job.get("progress_percent", 0) or 0),
                    job.get("error"),
                ),
            )


def update_document_status(document_id: str, status: str, chunks: int | None = None) -> None:
    with connect() as conn:
        with conn.cursor() as cur:
            if chunks is not None:
                cur.execute(
                    """
                    UPDATE uploaded_documents
                       SET status = %s, indexing_status = %s, chunks = %s
                     WHERE document_id = %s
                    """,
                    (status, status, chunks, document_id),
                )
            else:
                cur.execute(
                    """
                    UPDATE uploaded_documents
                       SET status = %s, indexing_status = %s
                     WHERE document_id = %s
                    """,
                    (status, status, document_id),
                )


def update_job(job_id: str, status: str | None = None,
               progress_percent: int | None = None, error: str | None = None) -> None:
    fields: list[str] = []
    params: list[Any] = []
    if status is not None:
        fields.append("status = %s")
        params.append(status)
    if progress_percent is not None:
        fields.append("progress_percent = %s")
        params.append(int(progress_percent))
    if error is not None:
        fields.append("error = %s")
        params.append(error)
    if not fields:
        return
    fields.append("updated_at = NOW()")
    params.append(job_id)
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE indexing_jobs SET {', '.join(fields)} WHERE job_id = %s",
                params,
            )


def delete_document(document_id: str) -> None:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM uploaded_documents WHERE document_id = %s",
                        (document_id,))


def load_all_documents() -> list[dict[str, Any]]:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT document_id, course_id, course_code, course_uuid,
                       filename, original_filename, file_type, file_size_bytes,
                       status, indexing_status, indexing_job_id, chunks,
                       uploaded_at, extra
                  FROM uploaded_documents
                 ORDER BY uploaded_at ASC
                """
            )
            rows = cur.fetchall()
    docs: list[dict[str, Any]] = []
    for row in rows:
        extra = row.pop("extra", {}) or {}
        # Mirror the in-memory shape that callers expect.
        row["id"] = row["document_id"]
        if row.get("uploaded_at") is not None:
            row["uploaded_at"] = row["uploaded_at"].strftime("%Y-%m-%dT%H:%M:%SZ")
        row.update({k: v for k, v in extra.items() if k not in row})
        docs.append(row)
    return docs


def load_all_jobs() -> dict[str, dict[str, Any]]:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT job_id, document_id, status, progress_percent, error,
                       created_at
                  FROM indexing_jobs
                """
            )
            rows = cur.fetchall()
    jobs: dict[str, dict[str, Any]] = {}
    for row in rows:
        row["id"] = row["job_id"]
        if row.get("created_at") is not None:
            row["created_at"] = row["created_at"].strftime("%Y-%m-%dT%H:%M:%SZ")
        jobs[row["job_id"]] = row
    return jobs


# ─── Auth (Sprint 7, T02) ────────────────────────────────────────────────

def get_user_by_email(email: str) -> dict[str, Any] | None:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, username, email, role, password_hash
                  FROM users
                 WHERE email = %s
                """,
                (email,),
            )
            row = cur.fetchone()
    if row is None:
        return None
    return {
        "user_id": str(row["id"]),
        "username": row["username"],
        "email": row["email"],
        "role": row["role"],
        "password_hash": row["password_hash"],
    }


def get_user_by_id(user_id: str) -> dict[str, Any] | None:
    """Look a user up by id. Used when authorizing course ownership, where the
    owner is known by id rather than by email. Returns None for an id that is
    not a well-formed UUID rather than raising, so a bad request body cannot
    turn into a 500."""
    with connect() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    """
                    SELECT id, username, email, role
                      FROM users
                     WHERE id = %s
                    """,
                    (user_id,),
                )
            except Exception:
                return None
            row = cur.fetchone()
    if row is None:
        return None
    return {
        "user_id": str(row["id"]),
        "username": row["username"],
        "email": row["email"],
        "role": row["role"],
    }


def create_user(username: str, email: str, role: str,
                password: str) -> tuple[dict[str, Any] | None, str | None]:
    """Create an account.

    Returns (user, None) on success, or (None, reason) where reason is
    "email" or "username" if that field is already taken. The uniqueness is
    enforced by the table, not by the check below - the lookup afterwards only
    exists to say which field collided, so two simultaneous signups still
    cannot both succeed.
    """
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (username, email, role, password_hash)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT DO NOTHING
                RETURNING id, username, email, role
                """,
                (username, email, role, password_hash),
            )
            row = cur.fetchone()
            if row is not None:
                return {
                    "user_id": str(row["id"]),
                    "username": row["username"],
                    "email": row["email"],
                    "role": row["role"],
                    "enrolled_courses": [],
                }, None

            cur.execute("SELECT 1 FROM users WHERE email = %s", (email,))
            taken = "email" if cur.fetchone() else "username"
    return None, taken


def get_enrolled_course_codes(user_id: str) -> list[str]:
    """Course codes (e.g. "CSIT321"), not Postgres UUIDs — the rest of the
    system (resolve_course, course-scoped retrieval) already keys off codes
    from the fixture course list, so returning codes here keeps that path
    unchanged regardless of whether the login came from Postgres or fixtures.
    """
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.course_code
                  FROM course_memberships cm
                  JOIN courses c ON c.id = cm.course_id
                 WHERE cm.user_id = %s
                """,
                (user_id,),
            )
            rows = cur.fetchall()
    return [row["course_code"] for row in rows]


def touch_last_login(user_id: str) -> None:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET last_login_at = NOW() WHERE id = %s",
                (user_id,),
            )


# ─── Courses & enrollments (Sprint 7, T03) ──────────────────────────────

# Every course read returns the same shape, so the owner travels with the
# course and callers never have to make a second query to authorize a write.
_COURSE_COLUMNS = "id, course_code, course_name, description, is_active, owner_id, created_at"


def _normalize_course_row(row: dict[str, Any]) -> dict[str, Any]:
    row["id"] = str(row["id"])
    if row.get("owner_id") is not None:
        row["owner_id"] = str(row["owner_id"])
    if row.get("created_at") is not None:
        row["created_at"] = row["created_at"].strftime("%Y-%m-%dT%H:%M:%SZ")
    return row


def list_courses(active_only: bool = False) -> list[dict[str, Any]]:
    query = f"""
        SELECT {_COURSE_COLUMNS}
          FROM courses
    """
    if active_only:
        query += " WHERE is_active = TRUE"
    query += " ORDER BY course_code"
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()
    return [_normalize_course_row(row) for row in rows]


def get_course_by_code(course_code: str) -> dict[str, Any] | None:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT {_COURSE_COLUMNS}
                  FROM courses
                 WHERE course_code = %s
                """,
                (course_code,),
            )
            row = cur.fetchone()
    return _normalize_course_row(row) if row is not None else None


def create_course(course_code: str, course_name: str,
                   description: str | None = None,
                   owner_id: str | None = None) -> dict[str, Any] | None:
    """Returns None if course_code already exists.

    owner_id is the lecturer who may manage the course afterwards. Left None
    for an admin-created course, which keeps it admin-only.
    """
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                INSERT INTO courses (course_code, course_name, description, owner_id)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (course_code) DO NOTHING
                RETURNING {_COURSE_COLUMNS}
                """,
                (course_code, course_name, description, owner_id),
            )
            row = cur.fetchone()
    return _normalize_course_row(row) if row is not None else None


def update_course(course_code: str, course_name: str | None = None,
                   description: str | None = None,
                   is_active: bool | None = None) -> dict[str, Any] | None:
    """Returns None if course_code doesn't exist. With no fields set, returns
    the course unchanged."""
    fields: list[str] = []
    params: list[Any] = []
    if course_name is not None:
        fields.append("course_name = %s")
        params.append(course_name)
    if description is not None:
        fields.append("description = %s")
        params.append(description)
    if is_active is not None:
        fields.append("is_active = %s")
        params.append(is_active)
    if not fields:
        return get_course_by_code(course_code)
    fields.append("updated_at = NOW()")
    params.append(course_code)
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                UPDATE courses SET {', '.join(fields)}
                 WHERE course_code = %s
                RETURNING {_COURSE_COLUMNS}
                """,
                params,
            )
            row = cur.fetchone()
    return _normalize_course_row(row) if row is not None else None


def set_course_owner(course_code: str, owner_id: str | None) -> dict[str, Any] | None:
    """Transfer a course to another lecturer, or pass None to make it
    admin-only again. Returns None if the course does not exist."""
    with connect() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    f"""
                    UPDATE courses SET owner_id = %s, updated_at = NOW()
                     WHERE course_code = %s
                    RETURNING {_COURSE_COLUMNS}
                    """,
                    (owner_id, course_code),
                )
            except Exception:
                return None
            row = cur.fetchone()
    return _normalize_course_row(row) if row is not None else None


def list_course_members(course_code: str) -> list[dict[str, Any]]:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT u.id AS user_id, u.username, u.email, u.role AS account_role,
                       cm.membership_role, cm.joined_at
                  FROM course_memberships cm
                  JOIN users u ON u.id = cm.user_id
                  JOIN courses c ON c.id = cm.course_id
                 WHERE c.course_code = %s
                 ORDER BY u.email
                """,
                (course_code,),
            )
            rows = cur.fetchall()
    members = []
    for row in rows:
        row["user_id"] = str(row["user_id"])
        if row.get("joined_at") is not None:
            row["joined_at"] = row["joined_at"].strftime("%Y-%m-%dT%H:%M:%SZ")
        members.append(row)
    return members


def add_course_membership(course_code: str, email: str,
                           membership_role: str) -> dict[str, Any] | None:
    """Enroll a user (by email) into a course by code. Returns None if the
    course or user doesn't exist. Re-enrolling an existing member updates
    their membership_role instead of erroring."""
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO course_memberships (user_id, course_id, membership_role)
                SELECT u.id, c.id, %s
                  FROM users u, courses c
                 WHERE u.email = %s AND c.course_code = %s
                ON CONFLICT (user_id, course_id)
                DO UPDATE SET membership_role = EXCLUDED.membership_role, updated_at = NOW()
                RETURNING user_id, course_id, membership_role
                """,
                (membership_role, email, course_code),
            )
            row = cur.fetchone()
    return row


def remove_course_membership(course_code: str, email: str) -> bool:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM course_memberships cm
                 USING users u, courses c
                 WHERE cm.user_id = u.id AND cm.course_id = c.id
                   AND u.email = %s AND c.course_code = %s
                """,
                (email, course_code),
            )
            return cur.rowcount > 0


# ─── Tokens, sessions, rate limits (Sprint 8, T8-24) ────────────────────

def _insert_token(table: str, token: str, payload: dict[str, Any],
                   expires_in_seconds: int) -> None:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                INSERT INTO {table}
                  (token, user_id, email, role, enrolled_courses, expires_at)
                VALUES (%s, %s, %s, %s, %s, NOW() + %s * INTERVAL '1 second')
                ON CONFLICT (token) DO NOTHING
                """,
                (
                    token,
                    str(payload.get("user_id")),
                    payload.get("email"),
                    payload.get("role"),
                    json.dumps(payload.get("enrolled_courses", [])),
                    expires_in_seconds,
                ),
            )


def insert_access_token(token: str, payload: dict[str, Any],
                         expires_in_seconds: int = 3600) -> None:
    _insert_token("access_tokens", token, payload, expires_in_seconds)


def insert_refresh_token(token: str, payload: dict[str, Any],
                          expires_in_seconds: int = 60 * 60 * 24 * 30) -> None:
    _insert_token("refresh_tokens", token, payload, expires_in_seconds)


def update_enrolled_courses_for_user(user_id: str, courses: list[str]) -> None:
    """Write a user's new enrollment list onto every token they hold.

    T8-24 moved tokens into Postgres and reloads them at startup, so updating
    only the in-memory copy would survive until the next restart and no
    further - a lecturer would silently lose access to the course they had
    just created. Both tables are updated because a refresh issues a new
    access token from the stored refresh payload.
    """
    payload = json.dumps(list(courses))
    with connect() as conn:
        with conn.cursor() as cur:
            for table in ("access_tokens", "refresh_tokens"):
                cur.execute(
                    f"UPDATE {table} SET enrolled_courses = %s WHERE user_id = %s",
                    (payload, user_id),
                )


def _load_all_tokens(table: str) -> dict[str, dict[str, Any]]:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT token, user_id, email, role, enrolled_courses, issued_at, "
                f"       EXTRACT(EPOCH FROM expires_at) AS expires_at "
                f"FROM {table}"
            )
            rows = cur.fetchall()
    tokens: dict[str, dict[str, Any]] = {}
    for row in rows:
        token = row.pop("token")
        row["enrolled_courses"] = row.get("enrolled_courses") or []
        if row.get("expires_at") is not None:
            row["expires_at"] = float(row["expires_at"])
        if row.get("issued_at") is not None:
            row["issued_at"] = row["issued_at"].strftime("%Y-%m-%dT%H:%M:%SZ")
        tokens[token] = row
    return tokens


def get_settings(scope: str) -> dict[str, Any]:
    """Every stored setting for one scope ('global' or a course code)."""
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT key, value FROM settings WHERE scope = %s", (scope,))
            rows = cur.fetchall()
    return {r["key"]: r["value"] for r in rows}


def set_setting(scope: str, key: str, value: Any, updated_by: str | None = None) -> None:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO settings (scope, key, value, updated_by, updated_at)
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT (scope, key)
                DO UPDATE SET value = EXCLUDED.value,
                              updated_by = EXCLUDED.updated_by,
                              updated_at = NOW()
                """,
                (scope, key, json.dumps(value), updated_by),
            )


def delete_setting(scope: str, key: str) -> None:
    """Remove an override so the next tier down applies again."""
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM settings WHERE scope = %s AND key = %s", (scope, key))


def get_token(table: str, token: str) -> dict[str, Any] | None:
    """Look up one token. Postgres is the source of truth for validation:
    gunicorn runs more than one worker, each with its own APIState, so a token
    issued by one worker is not in another worker's dictionary."""
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT user_id, email, role, enrolled_courses, issued_at,
                       EXTRACT(EPOCH FROM expires_at) AS expires_at
                  FROM {table}
                 WHERE token = %s
                """,
                (token,),
            )
            row = cur.fetchone()
    if row is None:
        return None
    row["enrolled_courses"] = row.get("enrolled_courses") or []
    if row.get("expires_at") is not None:
        row["expires_at"] = float(row["expires_at"])
    if row.get("issued_at") is not None:
        row["issued_at"] = row["issued_at"].strftime("%Y-%m-%dT%H:%M:%SZ")
    return row


def delete_token(table: str, token: str) -> None:
    """Retire a token everywhere, not just in the worker that handled the
    request - otherwise logout leaves it valid on every other worker."""
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(f"DELETE FROM {table} WHERE token = %s", (token,))


def load_all_access_tokens() -> dict[str, dict[str, Any]]:
    return _load_all_tokens("access_tokens")


def load_all_refresh_tokens() -> dict[str, dict[str, Any]]:
    return _load_all_tokens("refresh_tokens")


def upsert_chat_session(session_id: str, user_id: str | None,
                         course_id: str | None) -> None:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO chat_sessions (session_id, user_id, course_id)
                VALUES (%s, %s, %s)
                ON CONFLICT (session_id)
                DO UPDATE SET updated_at = NOW()
                """,
                (session_id, user_id, course_id),
            )


def insert_chat_message(session_id: str, message: dict[str, Any]) -> None:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO chat_messages
                  (message_id, session_id, question, answer, sources)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (message_id) DO NOTHING
                """,
                (
                    message.get("message_id"),
                    session_id,
                    message.get("question"),
                    message.get("answer"),
                    json.dumps(message.get("sources", [])),
                ),
            )


def archive_chat_session(session_id: str) -> None:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE chat_sessions SET archived = TRUE, updated_at = NOW() "
                "WHERE session_id = %s",
                (session_id,),
            )


def load_all_sessions() -> dict[str, dict[str, Any]]:
    """Returns the same shape APIState.sessions already used in memory:
    {session_id: {session_id, user_id, course_id, created_at, updated_at,
                  messages: [...]}}
    """
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT session_id, user_id, course_id, archived,
                       created_at, updated_at
                  FROM chat_sessions
                """
            )
            session_rows = cur.fetchall()
            cur.execute(
                """
                SELECT message_id, session_id, question, answer, sources, created_at
                  FROM chat_messages
                 ORDER BY created_at ASC
                """
            )
            message_rows = cur.fetchall()

    sessions: dict[str, dict[str, Any]] = {}
    for row in session_rows:
        sid = row["session_id"]
        sessions[sid] = {
            "session_id": sid,
            "user_id": row.get("user_id"),
            "course_id": row.get("course_id"),
            "archived": row.get("archived", False),
            "created_at": row["created_at"].strftime("%Y-%m-%dT%H:%M:%SZ")
                if row.get("created_at") else None,
            "updated_at": row["updated_at"].strftime("%Y-%m-%dT%H:%M:%SZ")
                if row.get("updated_at") else None,
            "messages": [],
        }
    for row in message_rows:
        sid = row["session_id"]
        if sid not in sessions:
            continue
        sessions[sid]["messages"].append({
            "message_id": row["message_id"],
            "question": row.get("question", ""),
            "answer": row.get("answer", ""),
            "sources": row.get("sources") or [],
            "created_at": row["created_at"].strftime("%Y-%m-%dT%H:%M:%SZ")
                if row.get("created_at") else None,
        })
    return sessions


def get_chat_session(session_id: str, message_limit: int | None = None) -> dict[str, Any] | None:
    """One session with its messages, or None if there is no such session.

    Same reason as `get_token`: gunicorn runs more than one worker and each
    has its own APIState, so a session created on one worker is absent from
    the other's dictionary. `load_all_sessions` only runs at start-up, so
    without a per-session read the follow-up turn sees no history roughly
    half the time — and non-deterministically, which is the worst way for it
    to fail.

    `message_limit` returns the most recent N messages, still in chronological
    order, because the prompt only renders the last few turns.
    """
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT session_id, user_id, course_id, archived,
                       created_at, updated_at
                  FROM chat_sessions
                 WHERE session_id = %s
                """,
                (session_id,),
            )
            row = cur.fetchone()
            if row is None:
                return None

            # Newest first for the LIMIT, then reversed below, so a long
            # session does not have to come back in full to read three turns.
            cur.execute(
                """
                SELECT message_id, question, answer, sources, created_at
                  FROM chat_messages
                 WHERE session_id = %s
                 ORDER BY created_at DESC
                 LIMIT %s
                """,
                (session_id, message_limit if message_limit else None),
            )
            message_rows = cur.fetchall()

    session = {
        "session_id": row["session_id"],
        "user_id": row.get("user_id"),
        "course_id": row.get("course_id"),
        "archived": row.get("archived", False),
        "created_at": row["created_at"].strftime("%Y-%m-%dT%H:%M:%SZ")
            if row.get("created_at") else None,
        "updated_at": row["updated_at"].strftime("%Y-%m-%dT%H:%M:%SZ")
            if row.get("updated_at") else None,
        "messages": [],
    }
    for message_row in reversed(message_rows):
        session["messages"].append({
            "message_id": message_row["message_id"],
            "question": message_row.get("question", ""),
            "answer": message_row.get("answer", ""),
            "sources": message_row.get("sources") or [],
            "created_at": message_row["created_at"].strftime("%Y-%m-%dT%H:%M:%SZ")
                if message_row.get("created_at") else None,
        })
    return session


def check_and_record_rate(rate_key: str, window_seconds: int, max_hits: int) -> bool:
    """Atomically: prune hits older than the window, count what's left, and
    — only if under the limit — record this hit. Returns True if the caller
    is allowed through, False if they're over the limit.

    Pruning inline (rather than a separate cleanup job) keeps this a single
    round trip and means the table never grows past what a small class
    produces in one rate-limit window.
    """
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM rate_limit_hits "
                "WHERE rate_key = %s AND hit_at <= NOW() - %s * INTERVAL '1 second'",
                (rate_key, window_seconds),
            )
            cur.execute(
                "SELECT COUNT(*) AS n FROM rate_limit_hits WHERE rate_key = %s",
                (rate_key,),
            )
            count = cur.fetchone()["n"]
            if count >= max_hits:
                return False
            cur.execute(
                "INSERT INTO rate_limit_hits (rate_key) VALUES (%s)",
                (rate_key,),
            )
            return True
