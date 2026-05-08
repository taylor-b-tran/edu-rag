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
  POST /api/upload            → document upload + indexing
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
    max_retries: int = int(os.getenv("PAEDIA_API_RETRIES", "2"))
    use_fixtures: bool = os.getenv("PAEDIA_USE_FIXTURES", "true").lower() == "true"


# ─── FIXTURE LOADER ──────────────────────────────────────────────────

_fixture_cache: Optional[dict] = None


def _load_fixtures() -> Optional[dict]:
    """Load sample_responses.json as fallback data."""
    global _fixture_cache
    if _fixture_cache is not None:
        return _fixture_cache

    paths = [
        os.path.join(os.path.dirname(__file__), "..", "fixtures", "sample_responses.json"),
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

    def _post(self, endpoint: str, payload: dict) -> Optional[dict]:
        """Make a POST request to the Flask API. Returns None on failure."""
        if not self._check_api():
            return None
        url = f"{self.config.base_url}{endpoint}"
        for attempt in range(self.config.max_retries + 1):
            try:
                resp = requests.post(
                    url,
                    json=payload,
                    headers=self._headers(),
                    timeout=self.config.timeout,
                )
                if resp.status_code == 401 and self._refresh_token:
                    # Try token refresh once
                    if self._refresh_jwt():
                        resp = requests.post(
                            url,
                            json=payload,
                            headers=self._headers(),
                            timeout=self.config.timeout,
                        )
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                logger.warning("API POST %s attempt %d failed: %s", endpoint, attempt + 1, e)
                if attempt < self.config.max_retries:
                    time.sleep(0.5 * (attempt + 1))
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

        # Fixture fallback — validate against demo_users passwords
        if self._fixtures:
            for u in self._fixtures.get("demo_users", []):
                if u.get("email", "").lower() == email.lower():
                    if u.get("password") == password:
                        profile = {k: v for k, v in u.items() if k != "password"}
                        profile.setdefault("name", u.get("username", email))
                        profile["role"] = profile.get("role", "student").capitalize()
                        return {"success": True, "user": profile, "jwt_token": None, "error": None}
                    return {"success": False, "user": {}, "error": "Invalid email or password.", "use_demo_auth": False}
        return {"success": False, "user": {}, "error": "Invalid email or password.", "use_demo_auth": False}

    def query(self, query_text: str, course_id: str, session_id: Optional[str] = None) -> dict:
        """
        Submit a RAG query.

        Live API: POST /api/query { query, course_id, session_id }
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
        result = self._post("/api/query", {
            "query": query_text,
            "course_id": course_id,
            "session_id": session_id,
        })
        if result and "answer" in result:
            result["from_api"] = True
            return result

        # Fixture fallback
        return self._fixture_query(query_text)

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

        Returns: { "success": bool, "document": dict, "error": str|None }
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
                document = data.get("document", data)
                if data.get("job_id") and "indexing_job_id" not in document:
                    document["indexing_job_id"] = data["job_id"]
                return {"success": True, "document": document, "error": None}
            except Exception as e:
                logger.warning("Document upload failed: %s", e)

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
        return {"success": True, "document": mock_doc, "error": None}

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

    def get_indexing_status(self, document_id: str) -> dict:
        """
        Poll indexing job status for a document.

        Live API: GET /api/indexing-jobs/<job_id>
        Fixture fallback: return { "status": "indexed", "progress_percent": 100 }
        """
        result = self._get(f"/api/indexing-jobs/{document_id}")
        if result:
            return result
        return {"status": "indexed", "progress_percent": 100}

    def get_courses(self, user_id: Optional[str] = None) -> list:
        """
        List courses the user is enrolled in.

        Live API: not exposed in the Sprint 3 API spec yet.
        Fixture fallback: return courses from sample_responses.json.
        """
        if self._fixtures:
            return self._fixtures.get("courses", [])
        return []
