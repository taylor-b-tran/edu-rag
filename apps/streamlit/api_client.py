"""
Paedia API Client — HTTP layer for Flask WebApplication (Module 4)

Authors: Anmoldeep Singh (8443580), Thanh Binh Tran, Tai Huynh

Connects the Streamlit UI to the Flask REST API. Sample data is used only
when PAEDIA_USE_FIXTURES is explicitly enabled. Live failures remain errors.

Endpoints (defined in Assessment 2, Section: WebApplication):
  POST /api/auth/login        → JWT + user profile
  POST /api/auth/refresh      → new JWT from refresh token
  POST /api/query             → RAG pipeline query
  POST /api/documents/upload  → document upload + indexing
  GET  /api/documents         → list documents (course_id scoped)
  GET  /api/sessions          → list chat sessions
  GET  /api/sessions/<id>     → get session messages

Author: Anmoldeep Singh (8443580)
CSIT321 Project 37 · Group 19 — Aletheia's Zetetes
"""

import json
import os
import time
import logging
from typing import Optional
from dataclasses import dataclass, field

# Use requests if available, otherwise stub for fixture-only mode
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

logger = logging.getLogger(__name__)


# ─── CONFIG ──────────────────────────────────────────────────────────

@dataclass
class APIConfig:
    """Configuration for the Flask WebApplication API connection."""
    base_url: str = os.getenv("PAEDIA_API_URL", "http://localhost:5000")
    timeout: int = int(os.getenv("PAEDIA_API_TIMEOUT", "10"))
    # Must stay above the backend's own Ollama generation timeout (240s,
    # src/document_processor/rag_pipeline.py) plus retrieval/Flask overhead,
    # otherwise the frontend gives up before the backend's graceful fallback
    # ever gets a chance to return (T11).
    query_timeout: int = int(os.getenv("PAEDIA_QUERY_TIMEOUT", "260"))
    max_retries: int = int(os.getenv("PAEDIA_API_RETRIES", "2"))
    use_fixtures: bool = os.getenv("PAEDIA_USE_FIXTURES", "false").lower() == "true"


# ─── FIXTURE LOADER ──────────────────────────────────────────────────

_fixture_cache: Optional[dict] = None


def _load_fixtures() -> Optional[dict]:
    """Load sample_responses.json as fallback data."""
    global _fixture_cache
    if _fixture_cache is not None:
        return _fixture_cache

    paths = [
        os.path.join(os.path.dirname(__file__), "..", "..", "fixtures", "sample_responses.json"),
        os.path.join("fixtures", "sample_responses.json"),
    ]
    for path in paths:
        if os.path.exists(path):
            with open(path, "r") as f:
                _fixture_cache = json.load(f)
                logger.info("Loaded fixture data from %s", path)
                return _fixture_cache
    logger.warning("No fixture file found — running without fallback data")
    return None


# ─── API CLIENT ──────────────────────────────────────────────────────

class APIReadError(RuntimeError):
    """A failed read must not masquerade as an empty collection."""

    def __init__(self, endpoint: str, result: dict):
        self.endpoint = endpoint
        self.status_code = result.get("status_code")
        self.error_type = result.get("error_type", "api_error")
        super().__init__(result.get("message") or result.get("error") or "Could not load data. Please retry.")


class PaediaAPIClient:
    """Per-browser bearer credentials; explicit demo mode, recoverable live requests."""

    def __init__(self, config: Optional[APIConfig] = None):
        self.config = config or APIConfig()
        self._jwt_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._api_available: Optional[bool] = None  # None = not checked yet
        self._fixtures = _load_fixtures() if self.config.use_fixtures else None
        self._health_checked_at = 0.0

    # ── Internal helpers ──

    def _headers(self) -> dict:
        """Build request headers with JWT if available."""
        h = {"Content-Type": "application/json"}
        if self._jwt_token:
            h["Authorization"] = f"Bearer {self._jwt_token}"
        return h

    def _check_api(self) -> bool:
        """Short-lived health display cache; never gates real requests."""
        if not HAS_REQUESTS or self.config.use_fixtures:
            return False
        now = time.monotonic()
        if self._api_available is not None and now - self._health_checked_at < 5:
            return self._api_available
        try:
            resp = requests.get(f"{self.config.base_url}/api/health", timeout=3)
            self._api_available = resp.status_code == 200
        except requests.RequestException:
            self._api_available = False
        self._health_checked_at = now
        return self._api_available

    @staticmethod
    def _failure(message="Cannot reach the server. Please retry.", *, status_code=None,
                 error_type="api_unavailable") -> dict:
        return {"_api_error": True, "error": message, "message": message,
                "status_code": status_code, "error_type": error_type}

    def _request(self, method, endpoint, *, timeout=None, max_retries=0, **kwargs):
        if self.config.use_fixtures:
            return None
        if not HAS_REQUESTS:
            return self._failure()
        for attempt in range(max_retries + 1):
            try:
                headers = self._headers()
                if "files" in kwargs:
                    headers.pop("Content-Type", None)
                send = getattr(requests, method.lower())
                resp = send(f"{self.config.base_url}{endpoint}", headers=headers,
                            timeout=timeout or self.config.timeout, **kwargs)
                if resp.status_code == 401 and self._refresh_token and self._refresh_jwt():
                    headers = self._headers()
                    if "files" in kwargs:
                        headers.pop("Content-Type", None)
                    resp = send(f"{self.config.base_url}{endpoint}", headers=headers,
                                timeout=timeout or self.config.timeout, **kwargs)
                self._api_available = True
                self._health_checked_at = 0.0  # a response is not proof of healthy retrieval
                try:
                    data = resp.json()
                except ValueError:
                    data = None
                if resp.status_code >= 400:
                    labels = {401: "Your session has expired. Please sign in again.",
                              403: "You do not have permission to access this resource.",
                              404: "The requested item was not found.",
                              429: "Too many requests. Please try again shortly."}
                    message = labels.get(resp.status_code, "The server could not complete this request. Please retry.")
                    if isinstance(data, dict):
                        message = data.get("message") or data.get("error") or message
                    return self._failure(message, status_code=resp.status_code,
                                         error_type="api_http_error")
                if not isinstance(data, (dict, list)):
                    return self._failure("The server returned an invalid response. Please retry.",
                                         error_type="api_invalid_response")
                return data
            except requests.Timeout:
                result = self._failure("The request timed out. Its outcome could not be confirmed. Please check before retrying.",
                                       error_type="api_timeout")
            except requests.RequestException:
                result = self._failure()
            self._api_available = False
            self._health_checked_at = time.monotonic()
            if attempt < max_retries:
                time.sleep(0.5 * (attempt + 1))
        return result

    def _post(self, endpoint, payload, timeout=None, max_retries=None):
        # Writes are not automatically repeated after an uncertain outcome.
        return self._request("post", endpoint, json=payload, timeout=timeout,
                             max_retries=0 if max_retries is None else max_retries)

    def _patch(self, endpoint, payload):
        return self._request("patch", endpoint, json=payload)

    def _delete(self, endpoint):
        return self._request("delete", endpoint)

    def _get(self, endpoint, params=None):
        return self._request("get", endpoint, params=params)

    def _read_list(self, endpoint, key, params=None):
        result = self._get(endpoint, params)
        if isinstance(result, list):
            return result
        if isinstance(result, dict) and not result.get("_api_error") and isinstance(result.get(key), list):
            return result[key]
        if self.config.use_fixtures:
            return (self._fixtures or {}).get(key, [])
        raise APIReadError(endpoint, result if isinstance(result, dict) and result.get("_api_error")
                           else self._failure("Could not load data. Please retry.", error_type="api_invalid_response"))

    def _refresh_jwt(self) -> bool:
        """Attempt to refresh the JWT using the stored refresh token."""
        if not self._refresh_token or not HAS_REQUESTS:
            return False
        try:
            resp = requests.post(
                f"{self.config.base_url}/api/auth/refresh",
                json={"refresh_token": self._refresh_token},
                timeout=5,
            )
            if resp.status_code == 200:
                data = resp.json()
                self._jwt_token = data.get("access_token")
                self._refresh_token = data.get("refresh_token", self._refresh_token)
                return True
        except Exception as e:
            logger.warning("Token refresh failed: %s", e)
        return False

    # ── Public API methods ──

    @property
    def is_live(self) -> bool:
        """True if the client is connected to a live Flask API."""
        return self._check_api()

    @property
    def mode_label(self) -> str:
        """Human-readable label for the current connection mode."""
        return "Fixture Mode (demo)" if self.config.use_fixtures else ("Live API" if self.is_live else "API unavailable")

    def login(self, email: str, password: str) -> dict:
        """
        Authenticate a user.

        Live API: POST /api/auth/login { email, password }
        Fixture fallback: match against demo_users in sample_responses.json

        Returns: { "success": bool, "user": dict, "error": str|None }
        """
        # Try live API first
        result = self._post("/api/auth/login", {"email": email, "password": password})
        if result and result.get("access_token"):
            self._jwt_token = result["access_token"]
            self._refresh_token = result.get("refresh_token")
            return {
                "success": True,
                "user": result.get("user", {}),
                "jwt_token": self._jwt_token,
                "error": None,
            }

        # Fixture fallback — return None to let main.py handle demo credentials
        if result and result.get("_api_error"):
            return {
                "success": False,
                "user": {},
                "error": result.get("error") or result.get("message") or "Login failed.",
                "status_code": result.get("status_code"),
            }

        # The API did not answer at all. Offering the built-in demo credentials
        # here means that whenever the API is down, the passwords published in
        # this repo let someone into the UI - the same shape of hole that was
        # closed on the server in T8-27. Only offer it when fixture mode is
        # explicitly on.
        if self.config.use_fixtures:
            return {"success": False, "user": {}, "error": None, "use_demo_auth": True}
        return {
            "success": False,
            "user": {},
            "error": "Cannot reach the server. Try again in a moment.",
        }

    def signup(self, email: str, username: str, password: str, role: str = "student") -> dict:
        """
        Register a new user.

        Live API: POST /api/auth/signup { email, username, password, role }
        role must be "student" or "lecturer" — "admin" is rejected server-side.

        On 201 the response mirrors login: access_token, refresh_token, user object.
        A lecturer gets 202 {"status": "pending_approval", "message": ...} and no
        tokens: the account exists but an administrator must approve it first.
        Errors (400 weak password / bad role, 409 duplicate) return
        {"error": ..., "message": ...} where "message" is user-facing.

        Returns: { "success": bool, "user": dict, "jwt_token": str|None, "error": str|None }
        For a pending lecturer: success False, "pending" True, and "error" holds
        the message to show (it is not a failure, but nobody is signed in).
        """
        result = self._post("/api/auth/signup", {
            "email": email,
            "username": username,
            "password": password,
            "role": role,
        })
        if result and result.get("access_token"):
            self._jwt_token = result["access_token"]
            self._refresh_token = result.get("refresh_token")
            return {
                "success": True,
                "user": result.get("user", {}),
                "jwt_token": self._jwt_token,
                "error": None,
            }
        if result and result.get("status") == "pending_approval":
            return {"success": False, "pending": True, "user": {}, "jwt_token": None,
                    "error": result.get("message") or "An administrator must approve your account before you can sign in."}
        # API returned an error — use the message field as-is
        error_msg = (
            result.get("message") or result.get("error") or "Signup failed."
        ) if result else "Cannot reach the server. Try again in a moment."
        return {"success": False, "user": {}, "jwt_token": None, "error": error_msg}

    def get_pending_users(self) -> list:
        """Lecturer accounts waiting for an administrator's decision (admin only).

        Live API: GET /api/admin/users/pending
        """
        return self._read_list("/api/admin/users/pending", "users")

    def approve_user(self, user_id: str) -> dict:
        """Approve a waiting lecturer account (admin only). POST /api/admin/users/<id>/approve"""
        return self._decide_user(user_id, "approve")

    def reject_user(self, user_id: str) -> dict:
        """Reject a lecturer account (admin only). POST /api/admin/users/<id>/reject"""
        return self._decide_user(user_id, "reject")

    def _decide_user(self, user_id: str, action: str) -> dict:
        if self.config.use_fixtures:
            return {"success": False, "error": "Approving accounts needs the live system."}
        result = self._post(f"/api/admin/users/{user_id}/{action}", {})
        if result is None:
            return {"success": False, "error": "Accounts are unavailable right now."}
        if result.get("_api_error"):
            return {"success": False, "error": result.get("message") or result.get("error")}
        return {"success": True, "error": None, "user": result.get("user", {})}

    def query(self, query_text: str, course_id: str, session_id: Optional[str] = None,
              response_style: Optional[str] = None) -> dict:
        """
        Submit a RAG query.

        Live API: POST /api/query { query, course_id, session_id, response_style }
        Fixture fallback: match against responses in sample_responses.json

        Returns: {
            "answer": str,
            "source_references": list,
            "confidence": float,
            "model_used": str,
            "token_count": int,
            "is_fallback": bool,
            "from_api": bool,
        }
        """
        # Try live API
        api_live = self._check_api()
        payload = {
            "query": query_text,
            "course_id": course_id,
            "session_id": session_id,
        }
        if response_style:
            payload["response_style"] = response_style
        result = self._post("/api/query", payload,
                            timeout=self.config.query_timeout, max_retries=0)
        if result and "answer" in result:
            result["from_api"] = True
            return result
        if result and result.get("_api_error"):
            message = result.get("message") or result.get("error") or "The API rejected this request."
            return {
                "answer": message,
                "source_references": [],
                "confidence": "Low",
                "confidence_score": 0.0,
                "model_used": "api_error",
                "token_count": 0,
                "is_fallback": False,
                "from_api": bool(result.get("status_code")),
                "error_type": result.get("error_type") or "api_error",
                "error_message": message,
                "status_code": result.get("status_code"),
            }
        if self.config.use_fixtures:
            return self._fixture_query(query_text)
        return {"answer": "The server returned no answer. Please retry.",
                "error_type": "api_invalid_response", "error_message": "No answer was returned.",
                "is_fallback": False, "from_api": False, "source_references": []}

    def clear_auth(self) -> bool:
        """Sign out: revoke the token on the server, then forget it locally.

        This used to drop the two local variables and nothing else, so the
        token stayed valid until it expired — the server-side revocation built
        in T8-22/T8-24 existed and the UI never called it. That was invisible
        while the token lived only in Streamlit's memory and died with the tab.
        It stopped being invisible once the token moved into a cookie (T9-14):
        signing out cleared the screen, the cookie survived, the token still
        resolved to a user, and the next page load signed you straight back in.

        Keep credentials for a retry if the server cannot confirm revocation.
        """
        if self._jwt_token or self._refresh_token:
            if not HAS_REQUESTS:
                return False
            try:
                response = requests.post(
                    f"{self.config.base_url}/api/auth/logout",
                    json={"refresh_token": self._refresh_token},
                    headers=self._headers(),
                    timeout=self.config.timeout,
                )
                if response.status_code != 200:
                    return False
            except Exception as e:
                logger.warning("Logout could not reach the API: %s", e)
                return False
        self._jwt_token = None
        self._refresh_token = None
        return True

    def _fixture_query(self, query_text: str) -> dict:
        """Match query against fixture responses."""
        if self._fixtures:
            for q, resp in self._fixtures.get("responses", {}).items():
                if query_text.lower().strip("?").strip() in q.lower() or q.lower() in query_text.lower():
                    return {**resp, "from_api": False}
            fallback = self._fixtures.get("fallback_response", {})
            return {**fallback, "from_api": False}
        return {
            "answer": "Running in demo mode — backend not connected. This is a UI prototype.",
            "source_references": [],
            "confidence": 0.0,
            "model_used": "ollama/llama3",
            "token_count": 0,
            "is_fallback": True,
            "from_api": False,
        }

    def upload_document(self, file_bytes: bytes, filename: str, course_id: str) -> dict:
        """
        Upload a document for processing and indexing.

        Live API: POST /api/upload (multipart)
        Fixture fallback: return a mock Document record with status "pending"

        Returns: { "success": bool, "document": dict, "job_id": str|None, "error": str|None }
        """
        if not self.config.use_fixtures:
            result = self._request("post", "/api/upload", files={"file": (filename, file_bytes)},
                                   data={"course_id": course_id}, timeout=30)
            if not isinstance(result, dict) or result.get("_api_error") or not result.get("document"):
                result = result if isinstance(result, dict) else self._failure("Upload was not confirmed.")
                return {"success": False, "document": {}, "job_id": None,
                        "error": result.get("message") or "Upload was not confirmed.",
                        "status_code": result.get("status_code")}
            return {"success": True, "document": result["document"],
                    "job_id": result.get("job_id"), "error": None}

        # Fixture fallback — return mock document record
        import uuid
        mock_doc = {
            "document_id": str(uuid.uuid4()),
            "course_id": course_id,
            "filename": filename,
            "file_type": filename.rsplit(".", 1)[-1] if "." in filename else "unknown",
            "file_size_bytes": len(file_bytes),
            "status": "pending",
            "uploaded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        return {"success": True, "document": mock_doc, "job_id": None, "error": None}

    def delete_document(self, document_id: str) -> dict:
        if self.config.use_fixtures:
            return {"status": "success", "message": "Demo document deleted."}
        result = self._delete(f"/api/document/{document_id}")
        if not isinstance(result, dict) or result.get("_api_error"):
            result = result if isinstance(result, dict) else self._failure("Deletion was not confirmed.")
            return {"success": False, "error": result["message"], "status_code": result.get("status_code")}
        return result

    def download_document(self, document_id: str) -> dict:
        """The original file, for reading.

        Returns {"success", "content", "error", "status_code"} rather than bare
        bytes. The caller has to tell "the file is missing" apart from "your
        session expired" and "the service is unreachable", and a bare None
        cannot: every one of them would be reported to the reader as a missing
        file, which is both wrong and unactionable.

        Binary, so it cannot go through `_request()` -- that parses JSON -- but
        it follows the same policy: one 401 retry behind a token refresh, and
        the same wording for the statuses a reader can act on.
        """
        if self.config.use_fixtures:
            return self._download_failure("Opening a document needs the live system.")
        if not HAS_REQUESTS:
            return self._download_failure("The API client is unavailable.")

        url = f"{self.config.base_url}/api/document/{document_id}/file"
        try:
            response = requests.get(url, headers=self._headers(),
                                    timeout=self.config.timeout)
            if response.status_code == 401 and self._refresh_token and self._refresh_jwt():
                response = requests.get(url, headers=self._headers(),
                                        timeout=self.config.timeout)
        except requests.Timeout:
            return self._download_failure(
                "The request timed out before the file arrived. Please retry.")
        except requests.RequestException:
            return self._download_failure(
                "Could not reach the server. Please check the connection and retry.")

        if response.status_code == 200:
            return {"success": True, "content": response.content,
                    "error": None, "status_code": 200}

        labels = {
            401: "Your session has expired. Please sign in again.",
            403: "You do not have permission to open this document.",
            404: "This document is listed but its file is not on the server.",
            429: "Too many requests. Please try again shortly.",
        }
        message = labels.get(response.status_code,
                             "The server could not return this file. Please retry.")
        try:
            body = response.json()
            if isinstance(body, dict):
                message = body.get("message") or message
        except ValueError:
            pass
        return self._download_failure(message, status_code=response.status_code)

    @staticmethod
    def _download_failure(message: str, status_code: Optional[int] = None) -> dict:
        return {"success": False, "content": None,
                "error": message, "status_code": status_code}

    def get_documents(self, course_id: Optional[str] = None) -> list:
        docs = self._read_list("/api/documents", "documents", {"course_id": course_id} if course_id else {})
        if self.config.use_fixtures and course_id:
            return [d for d in docs if d.get("course_id") == course_id]
        return docs

    def get_sessions(self, user_id: Optional[str] = None) -> list:
        return self._read_list("/api/sessions", "sessions", {"user_id": user_id} if user_id else None)

    def delete_session(self, session_id: str) -> dict:
        """
        Archive / delete a chat session.

        Live API: DELETE /api/sessions/<session_id>
        """
        result = self._delete(f"/api/sessions/{session_id}")
        if result and result.get("_api_error"):
            return {"success": False, "error": result.get("error", "Delete failed.")}
        if result and result.get("status") == "success":
            return {"success": True, "error": None}
        return {"success": False, "error": "Could not delete session."}

    def get_indexing_status(self, job_id: str) -> dict:
        if self.config.use_fixtures:
            return {"status": "completed", "progress_percent": 100}
        result = self._get(f"/api/indexing-jobs/{job_id}")
        if not isinstance(result, dict) or result.get("_api_error") or "status" not in result:
            result = result if isinstance(result, dict) else {}
            return {"status": "unavailable", "error": result.get("message") or "Indexing status is unavailable.",
                    "status_code": result.get("status_code")}
        return result

    def get_admin_stats(self) -> dict:
        result = self._get("/api/admin/stats")
        if isinstance(result, dict) and not result.get("_api_error"):
            # The endpoint's users are fixture counts; sessions/queries are
            # worker-local. Do not present these as system-wide live metrics.
            return {**result, "users": None, "sessions": None, "queries_total": None}
        return {"_offline": True, "error": (result if isinstance(result, dict) else {}).get("message") or "Metrics unavailable in demo mode."}

    def get_courses(self, user_id: Optional[str] = None) -> list:
        return self._read_list("/api/courses", "courses", {"user_id": user_id} if user_id else None)

    def create_course(self, course_code: str, course_name: str,
                       description: Optional[str] = None) -> dict:
        """
        Create a course (admin only).

        Live API: POST /api/courses
        Returns: { "success": bool, "course": dict, "error": str|None }
        """
        result = self._post("/api/courses", {
            "course_code": course_code,
            "course_name": course_name,
            "description": description,
        })
        if result and result.get("_api_error"):
            return {"success": False, "course": {}, "error": result.get("error")}
        if result and "course" in result:
            return {"success": True, "course": result["course"], "error": None}
        return {"success": False, "course": {}, "error": "Course management is unavailable right now."}

    def reactivate_course(self, course_code: str) -> dict:
        """Bring a deactivated course back.

        Live API: PATCH /api/courses/<code> with is_active true. The route has
        accepted this since T8-04; nothing in the client reached it, which made
        deactivation a one-way door from the admin screen.
        """
        if self.config.use_fixtures:
            return {"success": False, "error": "Reactivating a course needs the live system."}
        result = self._patch(f"/api/courses/{course_code}", {"is_active": True})
        if result is None:
            return {"success": False, "error": "Courses are unavailable right now."}
        if result.get("_api_error"):
            return {"success": False, "error": result.get("message") or result.get("error")}
        return {"success": True, "error": None, "course": result.get("course", {})}

    def deactivate_course(self, course_code: str) -> dict:
        """
        Deactivate a course (admin only, soft-delete).

        Live API: DELETE /api/courses/<code>
        """
        result = self._delete(f"/api/courses/{course_code}")
        if result and result.get("_api_error"):
            return {"success": False, "error": result.get("error")}
        if result and "course" in result:
            return {"success": True, "course": result["course"], "error": None}
        return {"success": False, "error": "Course management is unavailable right now."}

    def get_course_members(self, course_code: str) -> list:
        """
        List a course's enrolled members (admin only).

        Live API: GET /api/courses/<code>/members
        """
        return self._read_list(f"/api/courses/{course_code}/members", "members")

    def add_course_member(self, course_code: str, email: str, membership_role: str) -> dict:
        """
        Enroll a user into a course by email (admin only).

        Live API: POST /api/courses/<code>/members
        """
        result = self._post(f"/api/courses/{course_code}/members", {
            "email": email,
            "membership_role": membership_role,
        })
        if result and result.get("_api_error"):
            return {"success": False, "error": result.get("error")}
        if result and result.get("status") == "enrolled":
            return {"success": True, "error": None}
        return {"success": False, "error": "Course management is unavailable right now."}

    def remove_course_member(self, course_code: str, email: str) -> dict:
        """
        Unenroll a user from a course (admin only).

        Live API: DELETE /api/courses/<code>/members/<email>
        """
        result = self._delete(f"/api/courses/{course_code}/members/{email}")
        if result and result.get("_api_error"):
            return {"success": False, "error": result.get("error")}
        if result and result.get("status") == "unenrolled":
            return {"success": True, "error": None}
        return {"success": False, "error": "Course management is unavailable right now."}

    def join_course(self, course_code: str) -> dict:
        """
        Join a course as the signed-in student (T8-05).

        Live API: POST /api/courses/<code>/join
        Returns: { "success": bool, "status": str|None, "enrolled_courses": list|None, "error": str|None }
        On success, enrolled_courses is every course the server now lets this
        student ask about: store it on the session user so the course selector
        offers the new course straight away. It is None when the change was not
        confirmed; keep the list you have and re-read the courses instead.
        """
        return self._join_or_leave("join", course_code, {"enrolled", "already_enrolled"})

    def leave_course(self, course_code: str) -> dict:
        """
        Leave a course as the signed-in student (T8-05).

        Live API: POST /api/courses/<code>/leave
        Returns the same shape as join_course.
        """
        return self._join_or_leave("leave", course_code, {"unenrolled", "not_enrolled"})

    def _join_or_leave(self, action: str, course_code: str, confirmed: set) -> dict:
        if self.config.use_fixtures:
            return {"success": False, "status": None, "enrolled_courses": None,
                    "error": "Joining or leaving a course needs the live system."}
        # Sent once, like every write: after an uncertain outcome the caller
        # re-reads the course list rather than repeating the request.
        result = self._post(f"/api/courses/{course_code}/{action}", {})
        if isinstance(result, dict) and not result.get("_api_error") and result.get("status") in confirmed:
            return {"success": True, "status": result["status"],
                    "enrolled_courses": list(result.get("enrolled_courses") or []), "error": None}
        failure = result if isinstance(result, dict) else {}
        return {"success": False, "status": None, "enrolled_courses": None,
                "error": failure.get("message") or failure.get("error")
                or "The change to your courses was not confirmed. Please retry.",
                "status_code": failure.get("status_code")}

    # ─── Live configuration (T8-08 backend, T8-09 UI) ─────────────────

    def get_global_settings(self) -> dict:
        """
        Global settings as stored, plus what the pipeline would use with
        nothing stored.

        Live API: GET /api/settings
        Fixture fallback: empty, so the UI shows defaults and disables editing.
        """
        result = self._get("/api/settings")
        if result and isinstance(result, dict) and not result.get("_api_error"):
            return result
        return {"scope": "global", "settings": {}, "_unavailable": True}

    def get_course_settings(self, course_code: str) -> dict:
        """
        One course's stored overrides and the values actually in effect for it.

        Live API: GET /api/courses/<code>/settings
        The `effective` block resolves course override -> global -> default,
        which is what the page needs to show provenance honestly.
        """
        result = self._get(f"/api/courses/{course_code}/settings")
        if result and isinstance(result, dict) and not result.get("_api_error"):
            return result
        return {"scope": course_code, "settings": {}, "effective": {}, "_unavailable": True}

    def update_global_settings(self, changes: dict) -> dict:
        """
        Change global settings. Admin only; a null value clears an override.

        Live API: PATCH /api/settings
        """
        result = self._patch("/api/settings", changes)
        if result is None:
            return {"success": False, "error": "Settings are unavailable right now."}
        if result.get("_api_error"):
            return {"success": False, "error": result.get("message") or result.get("error")}
        return {"success": True, "error": None, "settings": result.get("settings", {})}

    def update_course_settings(self, course_code: str, changes: dict) -> dict:
        """
        Change one course's settings. Admin, or the lecturer who owns it.

        Live API: PATCH /api/courses/<code>/settings
        Sending null for a key clears that course's override so the value falls
        back to the global setting rather than to a hardcoded default.
        """
        result = self._patch(f"/api/courses/{course_code}/settings", changes)
        if result is None:
            return {"success": False, "error": "Settings are unavailable right now."}
        if result.get("_api_error"):
            return {"success": False, "error": result.get("message") or result.get("error")}
        return {
            "success": True, "error": None,
            "settings": result.get("settings", {}),
            "effective": result.get("effective", {}),
        }

    def get_response_styles(self) -> dict:
        """
        The five answering styles and which one is the default.

        Live API: GET /api/response-styles
        Kept out of the UI as literals on purpose — T8-07 removed one set of
        hardcoded strings from this app and putting the style names back would
        be the same mistake.
        """
        result = self._get("/api/response-styles")
        if result and isinstance(result, dict) and result.get("styles"):
            return result
        return {"styles": [], "default": None}

    def get_health(self) -> dict:
        """
        What the backend is actually running: retrieval mode and which embedder
        is loaded.

        Live API: GET /api/health  (open — no token needed)
        Fixture fallback: an explicit "unknown" rather than a cheerful default,
        because the caller uses this to tell the user whether semantic search
        is really on.
        """
        result = self._get("/api/health")
        if result and isinstance(result, dict) and not result.get("_api_error"):
            return result
        return {"status": "unknown", "rag_available": False,
                "embedder": {"status": "unknown"}, "_unavailable": True}

    def get_current_user(self, token: Optional[str] = None) -> dict:
        """
        Turn a bearer token back into a user (T9-14).

        Live API: GET /api/auth/me
        Used when restoring a session from the browser cookie after a refresh.
        A dead or expired token returns {"success": False}, which is the signal
        to clear the cookie and show the login form.
        """
        if token:
            self._jwt_token = token
        result = self._get("/api/auth/me")
        if result and isinstance(result, dict) and result.get("email"):
            return {"success": True, "user": result}
        if not self.config.use_fixtures and not (isinstance(result, dict) and result.get("status_code") == 401):
            raise APIReadError("/api/auth/me", result if isinstance(result, dict) else self._failure())
        return {"success": False, "user": None}
