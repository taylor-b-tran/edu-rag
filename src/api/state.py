from __future__ import annotations

import json
import secrets
import time
import uuid
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


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

    @property
    def fixture_loaded(self) -> bool:
        return bool(self.fixtures)

    def issue_tokens(self, user: dict[str, Any]) -> dict[str, Any]:
        access_token = f"dev_access_{secrets.token_urlsafe(24)}"
        refresh_token = f"dev_refresh_{secrets.token_urlsafe(24)}"
        payload = {
            "user_id": user.get("user_id") or user.get("id"),
            "email": user.get("email"),
            "role": user.get("role", "student"),
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
            documents = [
                doc for doc in documents
                if doc.get("course_id") == course_id or doc.get("course_code") == course_id
            ]
        return documents

    def queue_upload(self, filename: str, file_size: int, course_id: str) -> dict[str, Any]:
        document_id = str(uuid.uuid4())
        job_id = str(uuid.uuid4())
        extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "unknown"
        document = {
            "document_id": document_id,
            "id": document_id,
            "course_id": course_id,
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
        return {"document": document, "indexing_job": job, "job_id": job_id}
