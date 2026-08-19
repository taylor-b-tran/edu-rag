from __future__ import annotations

import json
import logging
import os
import secrets
import time
import uuid
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _fixture_auth_allowed() -> bool:
    """Whether the demo accounts in fixtures/ may be used to log in.

    Off unless explicitly enabled, so the committed passwords cannot become a
    way in on a deployed instance. Tests and offline development set
    PAEDIA_ALLOW_FIXTURE_AUTH=1.
    """
    return os.environ.get("PAEDIA_ALLOW_FIXTURE_AUTH", "").strip().lower() in {"1", "true", "yes"}

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = REPO_ROOT / "fixtures" / "sample_responses.json"


def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load_fixtures() -> dict[str, Any]:
    if not FIXTURE_PATH.exists():
        return {}
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


@dataclass
class APIState:
    """In-memory Sprint 4 API state backed by the shared fixture file."""

    fixtures: dict[str, Any] = field(default_factory=_load_fixtures)
    access_tokens: dict[str, dict[str, Any]] = field(default_factory=dict)
    refresh_tokens: dict[str, dict[str, Any]] = field(default_factory=dict)
    sessions: dict[str, dict[str, Any]] = field(default_factory=dict)
    indexing_jobs: dict[str, dict[str, Any]] = field(default_factory=dict)
    uploaded_documents: list[dict[str, Any]] = field(default_factory=list)
    _retriever: Any = field(default=None, init=False, repr=False)
    _generator: Any = field(default=None, init=False, repr=False)
    _backend_mode: str = field(default="not_initialized", init=False, repr=False)
    _db_available: bool = field(default=False, init=False, repr=False)
    warmup_status: dict[str, Any] = field(default_factory=lambda: {"status": "pending"},
                                          init=False, repr=False)

    def __post_init__(self) -> None:
        try:
            from src.api import db
            db.init_schema()
            self.uploaded_documents = db.load_all_documents()
            self.indexing_jobs = db.load_all_jobs()
            self._db_available = True
            logger.info(
                "APIState hydrated from Postgres: %d documents, %d jobs.",
                len(self.uploaded_documents), len(self.indexing_jobs),
            )
        except Exception as exc:
            logger.warning(
                "Postgres unavailable (%s: %s). Upload metadata will be in-memory only.",
                type(exc).__name__, exc,
            )
            self._db_available = False

        try:
            from src.api import warmup
            warmup.warmup_async(self)
        except Exception as exc:
            logger.warning("Failed to schedule Ollama warm-up: %s", exc)
            self.warmup_status = {"status": "failed",
                                  "error": f"{type(exc).__name__}: {exc}"}

    @property
    def fixture_loaded(self) -> bool:
        return bool(self.fixtures)

    @property
    def backend_mode(self) -> str:
        return self._backend_mode

    @property
    def rag_available(self) -> bool:
        return self._backend_mode == "chromadb"

    @property
    def db_available(self) -> bool:
        return self._db_available

    def get_generator(self):
        if self._generator is None:
            try:
                from src.document_processor.rag_pipeline import VectorRetriever, LLMResponseGeneration
                self._retriever = VectorRetriever()
                self._generator = LLMResponseGeneration(retriever=self._retriever)
                self._backend_mode = "chromadb"
                print("  [APIState] RAG pipeline initialised (ChromaDB mode).")
            except Exception as exc:
                print(f"  [APIState] RAG pipeline unavailable ({type(exc).__name__}: {exc}). Falling back to fixture mode.")
                self._generator = _FixtureGenerator(self)
                self._backend_mode = "fixture"
        return self._generator

    def issue_tokens(self, user: dict[str, Any]) -> dict[str, Any]:
        access_token = f"dev_access_{secrets.token_urlsafe(24)}"
        refresh_token = f"dev_refresh_{secrets.token_urlsafe(24)}"
        payload = {
            "user_id": user.get("user_id") or user.get("id"),
            "email": user.get("email"),
            "role": user.get("role", "student"),
            "enrolled_courses": user.get("enrolled_courses", []),
            "issued_at": _utc_now(),
        }
        self.access_tokens[access_token] = payload
        self.refresh_tokens[refresh_token] = payload
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": 3600,
            "user": {
                "id": payload["user_id"],
                "name": user.get("name") or user.get("username") or user.get("email"),
                "username": user.get("username"),
                "email": user.get("email"),
                "role": payload["role"],
                "enrolled_courses": user.get("enrolled_courses", []),
            },
        }

    def validate_bearer(self, authorization: str | None) -> dict[str, Any] | None:
        if not authorization:
            return None
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            return None
        return self.access_tokens.get(token)

    def find_demo_user(self, email: str) -> dict[str, Any] | None:
        users = self.fixtures.get("demo_users", [])
        for user in users:
            if user.get("email", "").lower() == email.lower():
                return user
        return None

    def authenticate_user(self, email: str, password: str) -> dict[str, Any] | None:
        """Authenticate against Postgres when it is available, fixtures otherwise.

        The two are never both consulted for the same login. Postgres returning
        None means the password was wrong, and that answer is final - previously
        it fell through to _authenticate_via_fixture, so the plaintext demo
        passwords committed in fixtures/sample_responses.json kept working as an
        admin login no matter what the database said.
        """
        if self._db_available:
            try:
                return self._authenticate_via_postgres(email, password)
            except Exception as exc:
                # The database is the credential store. If it errors we refuse the
                # login rather than reaching for the committed demo passwords,
                # which would let anyone who can disrupt Postgres log in as admin.
                logger.error(
                    "Postgres auth failed for %s (%s: %s); refusing the login.",
                    email, type(exc).__name__, exc,
                )
                return None

        if not _fixture_auth_allowed():
            logger.error(
                "No database is configured and fixture auth is disabled; refusing "
                "the login for %s. Set PAEDIA_ALLOW_FIXTURE_AUTH=1 only for tests "
                "and offline development.",
                email,
            )
            return None
        return self._authenticate_via_fixture(email, password)

    def _authenticate_via_postgres(self, email: str, password: str) -> dict[str, Any] | None:
        import bcrypt

        from src.api import db

        record = db.get_user_by_email(email)
        if record is None:
            return None
        if not bcrypt.checkpw(password.encode("utf-8"), record["password_hash"].encode("utf-8")):
            return None
        db.touch_last_login(record["user_id"])
        return {
            "user_id": record["user_id"],
            "username": record["username"],
            "email": record["email"],
            "role": record["role"],
            "enrolled_courses": db.get_enrolled_course_codes(record["user_id"]),
        }

    def _authenticate_via_fixture(self, email: str, password: str) -> dict[str, Any] | None:
        user = self.find_demo_user(email)
        if not user:
            return None
        stored = user.get("password")
        # A fixture entry with no password used to authenticate against anything,
        # because the comparison was skipped when `stored` was falsy.
        if not stored or not secrets.compare_digest(str(stored), password):
            return None
        return user

    def find_user_any_source(self, email: str) -> dict[str, Any] | None:
        """Look up a user for token refresh — no password check, tries
        Postgres first (same reasoning as authenticate_user) then fixtures.
        """
        if self._db_available:
            try:
                from src.api import db
                record = db.get_user_by_email(email)
                if record is not None:
                    return {
                        "user_id": record["user_id"],
                        "username": record["username"],
                        "email": record["email"],
                        "role": record["role"],
                        "enrolled_courses": db.get_enrolled_course_codes(record["user_id"]),
                    }
                return None
            except Exception as exc:
                logger.error(
                    "Postgres lookup failed for %s during refresh (%s: %s); refusing.",
                    email, type(exc).__name__, exc,
                )
                return None
        if not _fixture_auth_allowed():
            return None
        return self.find_demo_user(email)

    def is_enrolled(self, user: dict[str, Any], course_id: str) -> bool:
        if user.get("role") == "admin":
            return True
        enrolled = user.get("enrolled_courses", [])
        if course_id in enrolled:
            return True
        for course in self.fixtures.get("courses", []):
            if course.get("course_code") == course_id or course.get("course_id") == course_id:
                if course["course_id"] in enrolled or course.get("course_code") in enrolled:
                    return True
        return False

    def list_courses(self) -> list[dict[str, Any]]:
        """Courses for the subject selector — Postgres when available (T03),
        else the fixture course list, in the same normalized shape."""
        if self._db_available:
            try:
                from src.api import db
                return [
                    {
                        "course_code": row["course_code"],
                        "name": row["course_name"],
                        "description": row.get("description"),
                        "is_active": row.get("is_active", True),
                    }
                    for row in db.list_courses()
                ]
            except Exception as exc:
                logger.warning(
                    "Postgres course list failed (%s: %s); falling back to fixtures.",
                    type(exc).__name__, exc,
                )
        return [
            {
                "course_code": course.get("course_code"),
                "name": course.get("name"),
                "description": course.get("description"),
                "is_active": True,
            }
            for course in self.fixtures.get("courses", [])
        ]

    def resolve_course(self, course_ref: str | None) -> tuple[str | None, str | None]:
        """Resolve a course code or UUID to (course_id_uuid, course_code).

        Returns (None, None) if not found. If the ref is unknown but truthy,
        returns it back unchanged in the code slot so callers can still filter.
        """
        if not course_ref:
            return None, None
        for course in self.fixtures.get("courses", []):
            if course.get("course_code") == course_ref or course.get("course_id") == course_ref:
                return course.get("course_id"), course.get("course_code")
        return None, course_ref

    def query_fixture(self, question: str) -> dict[str, Any]:
        responses = self.fixtures.get("responses", {})
        fallback = self.fixtures.get("fallback_response", {})
        best_score = 0.0
        best_response: dict[str, Any] | None = None
        q_lower = question.lower().strip("?").strip()
        stop_words = {
            "what", "is", "the", "a", "an", "how", "does", "do", "can", "you",
            "me", "and", "or", "in", "of", "to", "for", "on", "at", "with", "are",
        }
        q_words = set(q_lower.split()) - stop_words

        for key, response in responses.items():
            k_lower = key.lower().strip("?").strip()
            sequence_score = SequenceMatcher(None, q_lower, k_lower).ratio()
            k_words = set(k_lower.split()) - stop_words
            keyword_score = len(q_words & k_words) / len(q_words) if q_words else 0.0
            score = 0.55 * sequence_score + 0.45 * keyword_score
            if score > best_score:
                best_score = score
                best_response = response

        if best_response and best_score >= 0.28:
            result = dict(best_response)
            result["confidence"] = round(min(best_score * 1.5, 0.97), 3)
        else:
            result = dict(fallback)

        result.setdefault("source_references", result.get("sources", []))
        result.setdefault("sources", result.get("source_references", []))
        result.setdefault("is_fallback", bool(result.get("fallback_used", False)))
        result.setdefault("fallback_used", bool(result.get("is_fallback", False)))
        return result

    def record_session_message(
        self,
        session_id: str | None,
        user_id: str | None,
        course_id: str,
        question: str,
        answer: dict[str, Any],
    ) -> str:
        if not session_id:
            session_id = str(uuid.uuid4())
        session = self.sessions.setdefault(
            session_id,
            {
                "session_id": session_id,
                "user_id": user_id,
                "course_id": course_id,
                "created_at": _utc_now(),
                "updated_at": _utc_now(),
                "messages": [],
            },
        )
        session["messages"].append(
            {
                "message_id": str(uuid.uuid4()),
                "question": question,
                "answer": answer.get("answer", ""),
                "sources": answer.get("source_references", []),
                "created_at": _utc_now(),
            }
        )
        session["updated_at"] = _utc_now()
        return session_id

    def list_documents(self, course_id: str | None = None) -> list[dict[str, Any]]:
        documents = list(self.fixtures.get("documents", [])) + self.uploaded_documents
        if course_id:
            uuid_form, code_form = self.resolve_course(course_id)
            targets = {course_id}
            if uuid_form:
                targets.add(uuid_form)
            if code_form:
                targets.add(code_form)
            documents = [
                doc for doc in documents
                if doc.get("course_id") in targets or doc.get("course_code") in targets
            ]
        return documents

    def queue_upload(self, filename: str, file_size: int, course_id: str) -> dict[str, Any]:
        document_id = str(uuid.uuid4())
        job_id = str(uuid.uuid4())
        extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "unknown"
        uuid_form, code_form = self.resolve_course(course_id)
        document = {
            "document_id": document_id,
            "id": document_id,
            "course_id": code_form or course_id,
            "course_code": code_form or course_id,
            "course_uuid": uuid_form,
            "original_filename": filename,
            "filename": filename,
            "file_type": extension,
            "file_size_bytes": file_size,
            "status": "queued",
            "indexing_status": "queued",
            "uploaded_at": _utc_now(),
            "indexing_job_id": job_id,
        }
        job = {
            "job_id": job_id,
            "id": job_id,
            "document_id": document_id,
            "status": "queued",
            "progress_percent": 0,
            "created_at": _utc_now(),
        }
        self.uploaded_documents.append(document)
        self.indexing_jobs[job_id] = job
        if self._db_available:
            try:
                from src.api import db
                db.insert_document(document)
                db.insert_job(job)
            except Exception as exc:
                logger.warning("Failed to persist upload %s to Postgres: %s",
                               document_id, exc)
        return {"document": document, "indexing_job": job, "job_id": job_id}

    def update_document_status(self, document_id: str, status: str,
                               chunks: int | None = None) -> None:
        for doc in self.uploaded_documents:
            if doc.get("document_id") == document_id:
                doc["status"] = status
                doc["indexing_status"] = status
                if chunks is not None:
                    doc["chunks"] = chunks
                break
        if self._db_available:
            try:
                from src.api import db
                db.update_document_status(document_id, status, chunks)
            except Exception as exc:
                logger.warning("Failed to update document %s status in Postgres: %s",
                               document_id, exc)

    def update_job(self, job_id: str, status: str | None = None,
                   progress_percent: int | None = None,
                   error: str | None = None) -> None:
        job = self.indexing_jobs.get(job_id)
        if job is not None:
            if status is not None:
                job["status"] = status
            if progress_percent is not None:
                job["progress_percent"] = progress_percent
            if error is not None:
                job["error"] = error
        if self._db_available:
            try:
                from src.api import db
                db.update_job(job_id, status=status,
                              progress_percent=progress_percent, error=error)
            except Exception as exc:
                logger.warning("Failed to update job %s in Postgres: %s",
                               job_id, exc)

    def delete_uploaded_document(self, document_id: str) -> bool:
        before = len(self.uploaded_documents)
        self.uploaded_documents = [
            doc for doc in self.uploaded_documents
            if doc.get("document_id") != document_id and doc.get("id") != document_id
        ]
        removed = len(self.uploaded_documents) != before
        if removed and self._db_available:
            try:
                from src.api import db
                db.delete_document(document_id)
            except Exception as exc:
                logger.warning("Failed to delete document %s from Postgres: %s",
                               document_id, exc)
        return removed

class _FixtureResponse:
    def __init__(self, data: dict):
        self.answer           = data.get("answer", "")
        self.source_refs      = data.get("source_references", data.get("sources", []))
        self.is_fallback      = bool(data.get("is_fallback", data.get("fallback_used", False)))
        self.model_used       = "fixture"
        self.top_chunks       = []
        self.confidence       = "Medium"
        self.confidence_score = data.get("confidence", 0.5)


class _FixtureGenerator:
    """Fallback used when ChromaDB or generation is unavailable."""
    def __init__(self, state):
        self._state = state

    def generate(self, query: str, course_id: str = "CSIT321", **_kwargs) -> _FixtureResponse:
        data = self._state.query_fixture(query)
        return _FixtureResponse(data)
