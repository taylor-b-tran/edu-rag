from __future__ import annotations

import json
import logging
import os
from contextlib import contextmanager
from typing import Any, Iterator

import psycopg
from psycopg.rows import dict_row

logger = logging.getLogger(__name__)


def _conninfo() -> str:
    return (
        f"host={os.environ.get('POSTGRES_HOST', 'postgres')} "
        f"port={os.environ.get('POSTGRES_PORT', '5432')} "
        f"dbname={os.environ.get('POSTGRES_DB', 'edurag')} "
        f"user={os.environ.get('POSTGRES_USER', 'edurag')} "
        f"password={os.environ.get('POSTGRES_PASSWORD', 'edurag_dev_password')}"
    )


@contextmanager
def connect() -> Iterator[psycopg.Connection]:
    conn = psycopg.connect(_conninfo(), row_factory=dict_row, autocommit=True)
    try:
        yield conn
    finally:
        conn.close()


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


def init_schema() -> None:
    try:
        with connect() as conn:
            with conn.cursor() as cur:
                cur.execute(SCHEMA)
        logger.info("Postgres schema initialised (uploaded_documents, indexing_jobs).")
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
