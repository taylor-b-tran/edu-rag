"""
Paedia API Client — HTTP layer for Flask WebApplication (Module 4)

Connects the Streamlit UI to the Flask REST API. When the API is
unreachable (e.g. Task 2 not yet deployed), every method falls back
to fixture data from sample_responses.json so the UI remains fully
functional for Sprint demos.

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

class PaediaAPIClient:
    """
    HTTP client for the Flask WebApplication REST API.

    Design rationale:
    - Every public method tries the live API first, then falls back to
      fixture data if the API is unreachable or `use_fixtures` is True.
    - The `_api_available` flag is set on the first successful request
      and cached for the session to avoid repeated timeouts.
    - JWT token is stored in-memory and attached to every request via
      the Authorization header.
    """

    def __init__(self, config: Optional[APIConfig] = None):
        self.config = config or APIConfig()
        self._jwt_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._api_available: Optional[bool] = None  # None = not checked yet
        self._fixtures = _load_fixtures()

    # ── Internal helpers ──

    def _headers(self) -> dict:
        """Build request headers with JWT if available."""
        h = {"Content-Type": "application/json"}
        if self._jwt_token:
            h["Authorization"] = f"Bearer {self._jwt_token}"
        return h

    def _check_api(self) -> bool:
        """Ping the API health endpoint to determine availability."""
        if self._api_available is not None:
            return self._api_available
        if not HAS_REQUESTS or self.config.use_fixtures:
            self._api_available = False
            return False
        try:
            resp = requests.get(
                f"{self.config.base_url}/api/health",
                timeout=3,
            )
            self._api_available = resp.status_code == 200
        except Exception:
            self._api_available = False
        logger.info("API availability: %s", self._api_available)
        return self._api_available

    def _post(
        self,
        endpoint: str,
        payload: dict,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
    ) -> Optional[dict]:
        """Make a POST request to the Flask API. Returns None on failure."""
        if not self._check_api():
            return None
        url = f"{self.config.base_url}{endpoint}"
        attempts = self.config.max_retries if max_retries is None else max_retries
        request_timeout = timeout or self.config.timeout
        for attempt in range(attempts + 1):
            try:
                resp = requests.post(
                    url,
                    json=payload,
                    headers=self._headers(),
                    timeout=request_timeout,
                )
                if resp.status_code == 401 and self._refresh_token:
                    # Try token refresh once
                    if self._refresh_jwt():
                        resp = requests.post(
                            url,
                            json=payload,
                            headers=self._headers(),
                            timeout=request_timeout,
                        )
                if resp.status_code >= 400:
                    try:
                        error = resp.json()
                    except Exception:
                        error = {"error": resp.text or resp.reason}
                    error["_api_error"] = True
                    error["status_code"] = resp.status_code
                    return error
                return resp.json()
            except Exception as e:
                logger.warning("API POST %s attempt %d failed: %s", endpoint, attempt + 1, e)
                if attempt < attempts:
                    time.sleep(0.5 * (attempt + 1))
        return None

    def _patch(self, endpoint: str, payload: dict) -> Optional[dict]:
        """Make a PATCH request to the Flask API. Returns None on failure."""
        if not self._check_api() or not HAS_REQUESTS:
            return None
        try:
            resp = requests.patch(
                f"{self.config.base_url}{endpoint}",
                json=payload,
                headers=self._headers(),
                timeout=self.config.timeout,
            )
            if resp.status_code >= 400:
                try:
                    error = resp.json()
                except Exception:
                    error = {"error": resp.text or resp.reason}
                error["_api_error"] = True
                error["status_code"] = resp.status_code
                return error
            return resp.json()
        except Exception as e:
            logger.warning("API PATCH %s failed: %s", endpoint, e)
            return None

    def _delete(self, endpoint: str) -> Optional[dict]:
        """Make a DELETE request to the Flask API. Returns None on failure."""
        if not self._check_api() or not HAS_REQUESTS:
            return None
        try:
            resp = requests.delete(
                f"{self.config.base_url}{endpoint}",
                headers=self._headers(),
                timeout=self.config.timeout,
            )
            if resp.status_code >= 400:
                try:
                    error = resp.json()
                except Exception:
                    error = {"error": resp.text or resp.reason}
                error["_api_error"] = True
                error["status_code"] = resp.status_code
                return error
            return resp.json()
        except Exception as e:
            logger.warning("API DELETE %s failed: %s", endpoint, e)
            return None

    def _get(self, endpoint: str, params: Optional[dict] = None) -> Optional[dict]:
        """Make a GET request to the Flask API. Returns None on failure."""
        if not self._check_api():
            return None
        url = f"{self.config.base_url}{endpoint}"
        try:
            resp = requests.get(
                url,
                params=params,
                headers=self._headers(),
                timeout=self.config.timeout,
            )
            if resp.status_code == 401 and self._refresh_token:
                if self._refresh_jwt():
                    resp = requests.get(
                        url,
                        params=params,
                        headers=self._headers(),
                        timeout=self.config.timeout,
                    )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.warning("API GET %s failed: %s", endpoint, e)
            return None

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
        return "Live API" if self.is_live else "Fixture Mode (demo)"

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
        Errors (400 weak password / bad role, 409 duplicate) return
        {"error": ..., "message": ...} where "message" is user-facing.

        Returns: { "success": bool, "user": dict, "jwt_token": str|None, "error": str|None }
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
        # API returned an error — use the message field as-is
        error_msg = (
            result.get("message") or result.get("error") or "Signup failed."
        ) if result else "Cannot reach the server. Try again in a moment."
        return {"success": False, "user": {}, "jwt_token": None, "error": error_msg}

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
                "is_fallback": True,
                "from_api": True,
                "error_type": result.get("error"),
                "error_message": message,
                "status_code": result.get("status_code"),
            }
        if api_live:
            return {
                "answer": "The live API did not return a response before the query timeout.",
                "source_references": [],
                "confidence": "Low",
                "confidence_score": 0.0,
                "model_used": "api_timeout",
                "token_count": 0,
                "is_fallback": True,
                "from_api": True,
                "error_type": "api_timeout",
                "error_message": "The live API request timed out.",
            }

        # Fixture fallback
        return self._fixture_query(query_text)

    def clear_auth(self) -> None:
        """Sign out: revoke the token on the server, then forget it locally.

        This used to drop the two local variables and nothing else, so the
        token stayed valid until it expired — the server-side revocation built
        in T8-22/T8-24 existed and the UI never called it. That was invisible
        while the token lived only in Streamlit's memory and died with the tab.
        It stopped being invisible once the token moved into a cookie (T9-14):
        signing out cleared the screen, the cookie survived, the token still
        resolved to a user, and the next page load signed you straight back in.

        Best effort on the network call. If revocation cannot be reached the
        local state is still cleared, which is no worse than the old behaviour.
        """
        if self._jwt_token and HAS_REQUESTS:
            try:
                requests.post(
                    f"{self.config.base_url}/api/auth/logout",
                    json={"refresh_token": self._refresh_token},
                    headers=self._headers(),
                    timeout=self.config.timeout,
                )
            except Exception as e:
                logger.warning("Logout could not reach the API: %s", e)
        self._jwt_token = None
        self._refresh_token = None

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
        if self._check_api() and HAS_REQUESTS:
            try:
                resp = requests.post(
                    f"{self.config.base_url}/api/upload",
                    files={"file": (filename, file_bytes)},
                    data={"course_id": course_id},
                    headers={"Authorization": f"Bearer {self._jwt_token}"} if self._jwt_token else {},
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()
                return {
                    "success": True,
                    "document": data.get("document", {}),
                    "job_id": data.get("job_id"),
                    "error": None
                }
            except Exception as e:
                logger.warning("Document upload failed: %s", e)
                return {"success": False, "document": {}, "job_id": None, "error": str(e)}

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
        """
        Delete a document.

        Live API: DELETE /api/document/<id>
        """
        if self._check_api() and HAS_REQUESTS:
            try:
                resp = requests.delete(
                    f"{self.config.base_url}/api/document/{document_id}",
                    headers={"Authorization": f"Bearer {self._jwt_token}"} if self._jwt_token else {},
                    timeout=15,
                )
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                logger.warning("Document deletion failed: %s", e)
                return {"success": False, "error": str(e)}
        return {"status": "success", "message": "Document deleted."}

    def get_documents(self, course_id: Optional[str] = None) -> list:
        """
        List documents, optionally scoped by course_id.

        Live API: GET /api/documents?course_id=<id>
        Fixture fallback: return documents from sample_responses.json
        """
        params = {"course_id": course_id} if course_id else {}
        result = self._get("/api/documents", params)
        if result and isinstance(result, list):
            return result
        if result and "documents" in result:
            return result["documents"]

        # Fixture fallback
        if self._fixtures:
            docs = self._fixtures.get("documents", [])
            if course_id:
                docs = [d for d in docs if d.get("course_id") == course_id]
            return docs
        return []

    def get_sessions(self, user_id: Optional[str] = None) -> list:
        """
        List chat sessions for the current user.

        Live API: GET /api/sessions
        Fixture fallback: return empty list (sessions are transient)
        """
        result = self._get("/api/sessions", {"user_id": user_id} if user_id else None)
        if result and isinstance(result, list):
            return result
        if result and "sessions" in result:
            return result["sessions"]
        return []

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
        """
        Poll indexing job status for a document.

        Live API: GET /api/indexing-jobs/<job_id>
        Fixture fallback: return { "status": "indexed", "progress_percent": 100 }
        """
        result = self._get(f"/api/indexing-jobs/{job_id}")
        if result:
            return result
        return {"status": "indexed", "progress_percent": 100}

    def get_admin_stats(self) -> dict:
        """
        Live admin/metrics snapshot.

        Live API: GET /api/admin/stats
        Fixture fallback: zeros so the UI still renders.
        """
        result = self._get("/api/admin/stats")
        if result and isinstance(result, dict):
            return result
        return {
            "documents": 0, "uploaded_documents": 0, "indexing_jobs": 0,
            "sessions": 0, "queries_total": 0, "users": 0, "courses": 0,
            "mode": "fixture", "warmup": {"status": "unknown"},
            "_offline": True,
        }

    def get_courses(self, user_id: Optional[str] = None) -> list:
        """
        List courses the user is enrolled in.

        Live API: GET /api/courses
        Fixture fallback: return courses from sample_responses.json
        """
        result = self._get("/api/courses", {"user_id": user_id} if user_id else None)
        if result and isinstance(result, list):
            return result
        if result and "courses" in result:
            return result["courses"]

        # Fixture fallback
        if self._fixtures:
            return self._fixtures.get("courses", [])
        return []

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
        result = self._get(f"/api/courses/{course_code}/members")
        if result and "members" in result:
            return result["members"]
        return []

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

    # ─── Live configuration (T8-08 backend, T8-09 UI) ─────────────────

    def get_global_settings(self) -> dict:
        """
        Global settings as stored, plus what the pipeline would use with
        nothing stored.

        Live API: GET /api/settings
        Fixture fallback: empty, so the UI shows defaults and disables editing.
        """
        result = self._get("/api/settings")
        if result and isinstance(result, dict):
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
        if result and isinstance(result, dict):
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
        if result and isinstance(result, dict):
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
        return {"success": False, "user": None}
