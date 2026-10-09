from __future__ import annotations

import json
import logging
import os
import secrets
import time
import threading
import uuid
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any
from functools import wraps
from werkzeug.exceptions import ServiceUnavailable

logger = logging.getLogger(__name__)


# Opaque tokens, held server-side rather than self-describing JWTs. That is a
# deliberate choice, not an accident of history: because the server holds them,
# logout genuinely revokes and an account can be cut off immediately, which a
# stateless JWT cannot do without a denylist. api_spec.yaml used to advertise
# JWT and has been corrected. T8-24 moves this store into Postgres, which suits
# opaque tokens and would fight a stateless design.
ACCESS_TOKEN_TTL_SECONDS = int(os.environ.get("PAEDIA_ACCESS_TOKEN_TTL", "3600"))
REFRESH_TOKEN_TTL_SECONDS = int(os.environ.get("PAEDIA_REFRESH_TOKEN_TTL", str(14 * 24 * 3600)))


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


def _auth_synchronized(fn):
    @wraps(fn)
    def run(self, *args, **kwargs):
        with self._auth_lock:
            return fn(self, *args, **kwargs)
    return run


@dataclass
class APIState:
    """In-memory Sprint 4 API state backed by the shared fixture file."""

    fixtures: dict[str, Any] = field(default_factory=_load_fixtures)
    access_tokens: dict[str, dict[str, Any]] = field(default_factory=dict)
    refresh_tokens: dict[str, dict[str, Any]] = field(default_factory=dict)
    sessions: dict[str, dict[str, Any]] = field(default_factory=dict)
     # T9-05: {message_id: {user_id: "up" | "down"}}. Fallback store for when
    # there is no database, same role as `sessions` above — mutated locally
    # only, and rebuilt on restart from whatever Postgres holds.
    message_feedback: dict[str, dict[str, str]] = field(default_factory=dict)
    indexing_jobs: dict[str, dict[str, Any]] = field(default_factory=dict)
    uploaded_documents: list[dict[str, Any]] = field(default_factory=list)
    _retriever: Any = field(default=None, init=False, repr=False)
    _generator: Any = field(default=None, init=False, repr=False)
    _backend_mode: str = field(default="not_initialized", init=False, repr=False)
    _db_available: bool = field(default=False, init=False, repr=False)
    _generator_lock: Any = field(default_factory=threading.Lock, init=False, repr=False)
    _auth_lock: Any = field(default_factory=threading.RLock, init=False, repr=False)
    warmup_status: dict[str, Any] = field(default_factory=lambda: {"status": "pending"},
                                          init=False, repr=False)

    @staticmethod
    def _db_startup_timeout() -> float:
        """Seconds a worker waits for Postgres at start-up; 0 means one attempt."""
        raw = os.environ.get("PAEDIA_DB_STARTUP_TIMEOUT_SECONDS", "").strip()
        if not raw:
            return 0.0
        try:
            return max(0.0, float(raw))
        except ValueError:
            logger.warning("Ignoring PAEDIA_DB_STARTUP_TIMEOUT_SECONDS=%r: not a number.", raw)
            return 0.0

    def _connect_database(self) -> None:
        """Hydrate from Postgres, waiting for it when a start-up timeout is set.

        After a reboot Docker starts every container at once and ignores
        depends_on, so a gunicorn worker can import this before Postgres accepts
        connections. With a single attempt that worker then ran on in-memory
        state for the rest of its life - every login refused, nothing persisted -
        while /api/health still answered 200.

        PAEDIA_DB_STARTUP_TIMEOUT_SECONDS > 0 (docker-compose.yml sets it) makes
        the database required: keep trying for that long, then raise. The worker
        fails to boot, gunicorn exits, and Docker's restart policy tries again.
        Unset or 0 keeps one attempt and the in-memory fallback that the test
        suite and offline demos depend on.
        """
        timeout = self._db_startup_timeout()
        deadline = time.monotonic() + timeout
        attempt = 0
        while True:
            attempt += 1
            try:
                from src.api import db
                db.init_schema()
                self.uploaded_documents = db.load_all_documents()
                self.indexing_jobs = db.load_all_jobs()
                self.access_tokens = db.load_all_access_tokens()
                self.refresh_tokens = db.load_all_refresh_tokens()
                self.sessions = db.load_all_sessions()
                self._db_available = True
                logger.info(
                    "APIState hydrated from Postgres on attempt %d: %d documents, "
                    "%d jobs, %d access tokens, %d sessions.",
                    attempt, len(self.uploaded_documents), len(self.indexing_jobs),
                    len(self.access_tokens), len(self.sessions),
                )
                return
            except Exception as exc:
                if timeout <= 0:
                    logger.warning(
                        "Postgres unavailable (%s: %s). Upload metadata will be in-memory only.",
                        type(exc).__name__, exc,
                    )
                    self._db_available = False
                    return
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise RuntimeError(
                        f"Postgres was not reachable within {timeout:g}s of start-up "
                        f"({type(exc).__name__}: {exc}); refusing to run without it."
                    ) from exc
                logger.warning(
                    "Postgres not ready on attempt %d (%s: %s); retrying for up to %.0fs.",
                    attempt, type(exc).__name__, exc, remaining,
                )
                time.sleep(min(2.0, remaining))
                try:
                    from src.api import db
                    db.reset_connection_state()
                except Exception:
                    pass

    def __post_init__(self) -> None:
        self._connect_database()

        try:
            from src.api import warmup
            warmup.warmup_async(self)
            if not self.use_fixtures and os.environ.get("EDURAG_RETRIEVAL_WARMUP", "true").lower() not in {"0", "false", "no"}:
                warmup.warmup_retrieval(self)
        except Exception as exc:
            logger.warning("Failed to schedule Ollama warm-up: %s", exc)
            self.warmup_status = {"status": "failed",
                                  "error": f"{type(exc).__name__}: {exc}"}

    @property
    def fixture_loaded(self) -> bool:
        return self.use_fixtures and bool(self.fixtures)

    @property
    def use_fixtures(self) -> bool:
        """Sample data requires an explicit opt-in, independent of demo login."""
        return os.environ.get("PAEDIA_USE_FIXTURES", "").strip().lower() in {"1", "true", "yes"}

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
        with self._generator_lock:
            if self._generator is None:
                from src.document_processor.ingest_corpus import EmbedderMismatchError
                try:
                    from src.document_processor.rag_pipeline import VectorRetriever, LLMResponseGeneration
                    retriever = VectorRetriever()
                    generator = LLMResponseGeneration(retriever=retriever)
                    self._retriever = retriever
                    self._generator = generator
                    self._backend_mode = "chromadb"
                    logger.info("RAG pipeline initialised (ChromaDB mode).")
                except EmbedderMismatchError:
                    self._retriever = None
                    self._backend_mode = "embedder_mismatch"
                    raise
                except Exception:
                    self._retriever = None
                    if not self.use_fixtures:
                        self._backend_mode = "not_initialized"
                        raise
                    logger.warning("RAG pipeline unavailable; explicit fixture mode enabled.")
                    self._generator = _FixtureGenerator(self)
                    self._backend_mode = "fixture"
            return self._generator

    @_auth_synchronized
    def issue_tokens(self, user: dict[str, Any],
                     family_id: str | None = None,
                     refresh_token_to_rotate: str | None = None) -> dict[str, Any] | None:
        """Issue an access/refresh pair for one login.

        `family_id` ties the pair together so logout can end the login rather
        than one credential of it. /auth/refresh passes the previous token's
        family back in, so rotating a refresh token stays inside the same
        login and a logout afterwards still reaches it. Omitting it starts a
        new login, which is what /auth/login wants.
        """
        access_token = f"dev_access_{secrets.token_urlsafe(24)}"
        refresh_token = f"dev_refresh_{secrets.token_urlsafe(24)}"
        now = time.time()
        payload = {
            "user_id": user.get("user_id") or user.get("id"),
            "email": user.get("email"),
            "role": user.get("role", "student"),
            "enrolled_courses": user.get("enrolled_courses", []),
            "family_id": family_id or f"fam_{secrets.token_urlsafe(16)}",
            "issued_at": _utc_now(),
        }
        # Persist the pair atomically before reporting a successful login.
        # On rotation the consume and insert share the logout family lock.
        if self._db_available:
            from src.api import db
            args = (access_token, refresh_token, payload,
                    ACCESS_TOKEN_TTL_SECONDS, REFRESH_TOKEN_TTL_SECONDS)
            if refresh_token_to_rotate:
                if not db.rotate_token_pair(refresh_token_to_rotate, *args):
                    return None
            else:
                db.insert_token_pair(*args)
                # A new login is a natural moment to clear credentials that can
                # no longer be used. Best effort: a login never fails over it.
                try:
                    db.prune_expired_tokens()
                except Exception as exc:
                    logger.warning("Expired-token pruning failed (%s: %s).",
                                   type(exc).__name__, exc)
        elif refresh_token_to_rotate:
            # The caller holds _auth_lock across validation, consume and issue.
            if self.consume_refresh_token(refresh_token_to_rotate) is None:
                return None
        if refresh_token_to_rotate:
            self.refresh_tokens.pop(refresh_token_to_rotate, None)
        self.access_tokens[access_token] = {**payload, "expires_at": now + ACCESS_TOKEN_TTL_SECONDS}
        self.refresh_tokens[refresh_token] = {**payload, "expires_at": now + REFRESH_TOKEN_TTL_SECONDS}
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_TTL_SECONDS,
            "user": {
                "id": payload["user_id"],
                "name": user.get("name") or user.get("username") or user.get("email"),
                "username": user.get("username"),
                "email": user.get("email"),
                "role": payload["role"],
                "enrolled_courses": user.get("enrolled_courses", []),
            },
        }

    def validate_bearer(self, authorization: str | None, *, report_store_error: bool = True) -> dict[str, Any] | None:
        """The caller's token payload, or None when there is no valid token.

        A token store that cannot be read is not the same as a token that does
        not exist. Answering it with None made every route say 401 during a
        database outage, and the interface treats 401 as "signed out" - so a
        brief outage ended real sessions. It now raises ServiceUnavailable,
        which the app answers as 503: retry, still signed in.
        """
        if not authorization:
            return None
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            return None
        return self._live_token(self.access_tokens, token, "access_tokens", report_store_error=report_store_error)

    def _live_token(self, store: dict[str, Any], token: str,
                    table: str, *, report_store_error: bool = False) -> dict[str, Any] | None:
        """Return the token's payload, or None if it is unknown or expired.

        Postgres is consulted first whenever it is available, because gunicorn
        runs more than one worker and each has its own APIState. A token issued
        by one worker is simply absent from another worker's dictionary, so a
        plain dictionary lookup rejected roughly half of all requests once a
        second worker started taking traffic. Reading the row also means logout
        takes effect everywhere rather than only where it was called.

        The dictionary remains the source of truth when there is no database,
        which is how the test suite runs.
        """
        if self._db_available:
            try:
                from src.api import db
                payload = db.get_token(table, token)
                if payload is None:
                    # Postgres is authoritative when it answers: no row means
                    # the token was retired or never existed. Falling back to
                    # this worker's cache here would undo logout, because the
                    # worker that did not handle it still holds a copy.
                    store.pop(token, None)
                    return None
            except Exception as exc:
                logger.warning("Token lookup failed (%s: %s); refusing cached credentials.",
                               type(exc).__name__, exc)
                if report_store_error:
                    raise ServiceUnavailable(
                        "Your sign-in could not be checked just now. Please retry.") from exc
                return None
        else:
            payload = store.get(token)
        if payload is None:
            return None

        expires_at = payload.get("expires_at")
        if expires_at is not None and time.time() >= expires_at:
            # Keep the expired access row as a family handle for logout after
            # cookie restore/expiry. It cannot authenticate; logout removes it.
            return None
        return payload

    def _retire_token(self, store: dict[str, Any], token: str, table: str) -> None:
        """Drop a token from this worker and from Postgres."""
        store.pop(token, None)
        if self._db_available:
            try:
                from src.api import db
                db.delete_token(table, token)
            except Exception as exc:
                logger.warning("Could not delete %s from Postgres (%s: %s); it "
                               "may still be accepted elsewhere until it expires.",
                               table, type(exc).__name__, exc)

    @_auth_synchronized
    def consume_refresh_token(self, token: str | None) -> dict[str, Any] | None:
        """Validate a refresh token and retire it, so each one is used once."""
        if not token:
            return None
        if self._db_available:
            from src.api import db
            payload = db.consume_refresh_token(token)
            self.refresh_tokens.pop(token, None)
            return payload
        payload = self._live_token(self.refresh_tokens, token, "refresh_tokens")
        if payload is not None:
            # Retiring it in Postgres is what makes "used once" hold across
            # workers; popping the local dictionary alone does not.
            self._retire_token(self.refresh_tokens, token, "refresh_tokens")
        return payload

    @_auth_synchronized
    def refresh_login(self, token: str | None) -> dict[str, Any] | None:
        if not token:
            return None
        payload = self._live_token(self.refresh_tokens, token, "refresh_tokens")
        if not payload or not payload.get("family_id"):
            return None
        user = self.find_user_any_source(payload.get("email", ""))
        if not user:
            return None
        return self.issue_tokens(user, family_id=payload["family_id"],
                                 refresh_token_to_rotate=token)

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
        status = record.get("approval_status", "approved")
        # An account waiting for approval (or not approved) has not signed in,
        # so it leaves no last-login time. The route reads `approval_status`
        # and refuses it; it is only reachable here once the password is right,
        # so the status is never revealed without the password.
        if status == "approved":
            db.touch_last_login(record["user_id"])
        return {
            "user_id": record["user_id"],
            "username": record["username"],
            "email": record["email"],
            "role": record["role"],
            "approval_status": status,
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
                    # An account that is not (or is no longer) approved cannot
                    # renew a login either.
                    if record.get("approval_status", "approved") != "approved":
                        return None
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

    def revoke_access_token(self, token: str) -> None:
        """Retire one access token everywhere. Prefer `revoke_login`."""
        self._retire_token(self.access_tokens, token, "access_tokens")

    @_auth_synchronized
    def revoke_login(self, access_token: str | None,
                     refresh_token: str | None = None) -> None:
        """End the whole login behind this access token.

        Retiring only the access token left the refresh token beside it alive,
        so the session that had just been logged out could be rebuilt from a
        credential logout was supposed to have ended. Before this change the
        old access token gave 401, but its refresh token still returned 200
        and the new token worked.

        The family covers that without depending on what the client remembers
        to send, which matters because after a page reload the browser holds
        only the access token -- the refresh token is deliberately not put in
        a cookie. Either credential can identify a family. Pre-family database
        credentials are invalidated by the idempotent schema upgrade.
        """
        if self._db_available:
            from src.api import db
            # Resolve and revoke in one transaction, including refresh-only
            # logout and expired access tokens. Errors must reach the route.
            db.revoke_login(access_token, refresh_token)
            # Reads always consult DB; stale local copies cannot revive a login.
            self.access_tokens.clear()
            self.refresh_tokens.clear()
            return
        payload = None
        if access_token:
            payload = self.access_tokens.get(access_token)
            self._retire_token(self.access_tokens, access_token, "access_tokens")

        families = {(payload or {}).get("family_id"),
                    (self.refresh_tokens.get(refresh_token) or {}).get("family_id")}
        for family_id in families - {None}:
            self._retire_token_family(family_id)

        if refresh_token:
            # A no-op once the family has been swept, and the only thing that
            # works for a pre-family token.
            self._retire_token(self.refresh_tokens, refresh_token, "refresh_tokens")

    def _retire_token_family(self, family_id: str) -> None:
        """Drop every token of one login, here and in Postgres."""
        for store in (self.access_tokens, self.refresh_tokens):
            for token in [t for t, p in store.items()
                          if (p or {}).get("family_id") == family_id]:
                store.pop(token, None)
        if self._db_available:
            try:
                from src.api import db
                db.delete_token_family(family_id)
            except Exception as exc:
                logger.warning("Could not delete token family from Postgres "
                               "(%s: %s); credentials from this login may still "
                               "be accepted elsewhere until they expire.",
                               type(exc).__name__, exc)

    def refresh_enrolled_courses(self, user_id: str | None) -> list[str] | None:
        """Re-read one user's enrollments and update every live token they hold.

        enrolled_courses is copied into the token payload when the token is
        issued, so without this a lecturer who has just created a course - or a
        student an admin has just enrolled - keeps being told they are not a
        member until they log in again. Returns the fresh list, or None if it
        could not be read.
        """
        if not self._db_available or not user_id:
            return None
        try:
            from src.api import db
            courses = db.get_enrolled_course_codes(user_id)
        except Exception as exc:
            logger.warning("Could not refresh enrollments for %s (%s: %s).",
                           user_id, type(exc).__name__, exc)
            return None
        # Walk copies: logins and token checks on other threads add to and drop
        # from these dicts, and walking a dict while its size changes raises
        # "dictionary changed size during iteration".
        for store in (self.access_tokens, self.refresh_tokens):
            for payload in list(store.values()):
                if payload.get("user_id") == user_id:
                    payload["enrolled_courses"] = list(courses)

        # Tokens are reloaded from Postgres on startup (T8-24), so the
        # in-memory update above would last only until the next restart.
        try:
            db.update_enrolled_courses_for_user(user_id, courses)
        except Exception as exc:
            logger.warning("Refreshed enrollments in memory but not in Postgres "
                           "for %s (%s: %s); they revert on restart.",
                           user_id, type(exc).__name__, exc)
        return list(courses)

    def is_enrolled(self, user: dict[str, Any], course_id: str) -> bool:
        if user.get("role") == "admin":
            return True
        uuid_form, code_form = self.resolve_course(course_id)
        if not code_form:
            return False
        enrolled = user.get("enrolled_courses") or []
        token_enrolled = code_form in enrolled or (uuid_form is not None and uuid_form in enrolled)
        if self._db_available:
            if not user.get("user_id"):
                return False
            try:
                from src.api import db
                enrolled = db.get_enrolled_course_codes(user["user_id"])
            except Exception as exc:
                raise ServiceUnavailable("Course membership is temporarily unavailable.") from exc
        # Require both token propagation and current membership: a failed join
        # confirmation must not grant access, and a stale token cannot undo leave.
        return token_enrolled and (code_form in enrolled or (uuid_form is not None and uuid_form in enrolled))

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
        """Return authoritative (UUID, code), or (None, None) for unknown input.

        Postgres is authoritative when connected. Only explicit fixture mode
        permits offline fixture identity; database failures never grant access.
        """
        if not course_ref:
            return None, None
        course_ref = str(course_ref).strip()
        if not course_ref:
            return None, None
        try:
            course_ref = str(uuid.UUID(course_ref))
        except ValueError:
            pass
        if self._db_available:
            try:
                from src.api import db
                course = db.get_course_by_ref(course_ref)
            except Exception as exc:
                raise ServiceUnavailable("Course information is temporarily unavailable.") from exc
            if course is None:
                return None, None
            return str(course["id"]), course["course_code"]
        if self.use_fixtures:
            for course in self.fixtures.get("courses", []):
                if course.get("course_code") == course_ref or course.get("course_id") == course_ref:
                    return course.get("course_id"), course.get("course_code")
            return None, None
        raise ServiceUnavailable("Course information is temporarily unavailable.")

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
        is_new_session = session_id not in self.sessions
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
        message = {
            "message_id": str(uuid.uuid4()),
            "question": question,
            "answer": answer.get("answer", ""),
            "sources": answer.get("source_references", []),
            "response_metadata": {key: answer[key] for key in (
                "confidence", "confidence_score", "model_used", "latency_ms",
                "is_fallback", "backend_mode", "retrieval_metadata", "token_count",
                "response_style",
            ) if key in answer},
            "created_at": _utc_now(),
        }
        session["messages"].append(message)
        session["updated_at"] = _utc_now()
        
        # T8-24: best-effort persist, same reasoning as issue_tokens above —
        # a failed write only costs this message on the next restart, not
        # the response the user already got.
        if self._db_available:
            try:
                from src.api import db
                if is_new_session:
                    db.upsert_chat_session(session_id, user_id, course_id)
                db.insert_chat_message(session_id, message)
            except Exception as exc:
                logger.warning("Failed to persist chat session to Postgres (%s: %s).",
                                type(exc).__name__, exc)
        return session_id

    def get_live_session(self, session_id: str,
                         message_limit: int | None = None) -> dict[str, Any] | None:
        """A session as it exists across all workers, not just this one.

        `self.sessions` is hydrated once at start-up and only ever mutated
        locally afterwards, so with --workers=2 a session created on one
        worker is missing from the other. Measured on the host: the same
        session id returned 200 five times and 404 five times over ten reads.

        Postgres is authoritative when it answers, for the same reason as
        `_live_token`: falling back to this worker's copy would resurrect a
        session that was archived elsewhere. The dictionary remains the source
        of truth when there is no database, which is how the tests run.
        """
        if not session_id:
            return None
        if self._db_available:
            try:
                from src.api import db
                session = db.get_chat_session(session_id, message_limit=message_limit)
                if session is None:
                    self.sessions.pop(session_id, None)
                    return None
                # Keep this worker's copy in step, so the next read is local
                # even if Postgres goes away in between.
                if message_limit is None:
                    self.sessions[session_id] = session
                return session
            except Exception as exc:
                logger.warning("Session lookup failed (%s: %s); falling back to "
                               "this worker's cache.", type(exc).__name__, exc)
        return self.sessions.get(session_id)

    def archive_session(self, session_id: str) -> None:
        """Used by DELETE /api/sessions/<id>. In-memory flag is set
        immediately for callers that read self.sessions right after; the
        Postgres write is best-effort like the other T8-24 writes."""
        session = self.sessions.get(session_id)
        if session is not None:
            session["archived"] = True
        if self._db_available:
            try:
                from src.api import db
                db.archive_chat_session(session_id)
            except Exception as exc:
                logger.warning("Failed to persist session archive to Postgres (%s: %s).",
                                type(exc).__name__, exc)

    def _refresh_documents(self) -> list[dict[str, Any]]:
        """This worker's uploaded documents, brought up to date with Postgres.

        `uploaded_documents` is filled once in __post_init__ and only mutated
        locally afterwards, so with --workers=2 a document uploaded through one
        worker simply does not exist for the other. Before this change, after
        an upload that returned 202 and really had indexed its chunks, sixteen
        reads of the same document id gave 404 twelve times, and its indexing
        job fourteen times out of sixteen. The lecturer saw "upload complete"
        and a document that was not there.

        Postgres is authoritative when it answers, for the same reason as
        `_live_token`: keeping this worker's extra rows would resurrect a
        document deleted on the other one, and deleting a document also removes
        its chunks, so the row would point at nothing. The dictionary remains
        the source of truth when there is no database, which is how the tests
        run.

        The table holds one row per upload -- tens of them, not thousands -- so
        re-reading it is cheaper than the second code path a query-by-id would
        add, and it reuses the row shaping that start-up already depends on.
        """
        if self._db_available:
            try:
                from src.api import db
                self.uploaded_documents = db.load_all_documents()
            except Exception as exc:
                logger.warning("Document reload failed (%s: %s); falling back to "
                               "this worker's cache.", type(exc).__name__, exc)
        return self.uploaded_documents

    def display_filenames(self, stored_names) -> dict[str, str]:
        """What each stored file was called by the person who uploaded it.

        Chunks carry the stored name, which has a suffix so two uploads of the
        same file stay apart, and which deletion uses to find a document's
        chunks. A citation built from a chunk therefore showed
        "notes-bc36086a.pdf" for a file the lecturer uploaded as "notes.pdf",
        while the document table showed "notes.pdf". A name with no row maps to
        itself, so a citation is never lost for want of a display name.
        """
        wanted = {name for name in stored_names if name}
        names = {name: name for name in wanted}
        for doc in self._refresh_documents():
            stored = doc.get("filename")
            if stored in wanted and doc.get("original_filename"):
                names[stored] = doc["original_filename"]
        return names

    def list_indexing_jobs(self) -> dict[str, dict[str, Any]]:
        """Read authoritative jobs; deleting a document cascades to its jobs."""
        if self._db_available:
            try:
                from src.api import db
                self.indexing_jobs = db.load_all_jobs()
            except Exception as exc:
                logger.warning("Job reload failed (%s: %s); falling back to "
                               "this worker's cache.", type(exc).__name__, exc)
        return self.indexing_jobs

    def find_document(self, document_id: str | None) -> dict[str, Any] | None:
        """One document by id, wherever it was uploaded from.

        Searches the merged list rather than querying Postgres by id, because
        fixture documents are part of what callers can see and have no row.
        """
        if not document_id:
            return None
        for document in self.list_documents():
            if (document.get("document_id") == document_id
                    or document.get("id") == document_id):
                return document
        return None

    def find_uploaded_document(self, document_id: str | None) -> dict[str, Any] | None:
        """Only real uploads, excluding fixtures.

        Deletion needs this narrower search: a fixture document has no file and
        no chunks of its own, so treating one as deletable would remove another
        document's chunks from ChromaDB by filename.
        """
        if not document_id:
            return None
        for document in self._refresh_documents():
            if (document.get("document_id") == document_id
                    or document.get("id") == document_id):
                return document
        return None

    def get_indexing_job(self, job_id: str | None) -> dict[str, Any] | None:
        if not job_id:
            return None
        return self.list_indexing_jobs().get(job_id)
    
    def find_message(self, session_id: str, message_id: str) -> dict[str, Any] | None:
        """The one message a feedback vote is about. Goes through
        get_live_session rather than self.sessions directly so a message
        created on another gunicorn worker doesn't look like a 404 here
        either."""
        session = self.get_live_session(session_id)
        if not session:
            return None
        for message in session.get("messages", []):
            if message.get("message_id") == message_id:
                return message
        return None

    def set_message_feedback(self, message_id: str, user_id: str, rating: str) -> bool:
        """Record a vote. True only when it is where it will be read back from.

        With Postgres behind it this dictionary is a cache: get_session_feedback
        prefers the database, so a write that failed there is a vote that
        disappears the moment anything reads it -- including the voter's own
        screen on the next load. Reporting success then is the same mistake as
        confirming an enrolment before the token carries it, so the failed
        write is rolled back here and the caller is told.
        """
        votes = self.message_feedback.setdefault(message_id, {})
        had_before = user_id in votes
        previous = votes.get(user_id)
        votes[user_id] = rating
        if not self._db_available:
            return True
        try:
            from src.api import db
            db.upsert_message_feedback(message_id, user_id, rating)
            return True
        except Exception as exc:
            logger.warning("Failed to persist feedback for message %s to Postgres (%s: %s).",
                            message_id, type(exc).__name__, exc)
            if had_before:
                votes[user_id] = previous
            else:
                votes.pop(user_id, None)
            return False

    def clear_message_feedback(self, message_id: str, user_id: str) -> bool:
        """Remove a vote. True only when it is gone where it is read back from.

        Same reasoning as set_message_feedback: a delete that failed in
        Postgres leaves a vote that comes straight back on the next read, so
        the in-memory removal is undone and the caller is told.
        """
        votes = self.message_feedback.get(message_id)
        had_before = votes is not None and user_id in votes
        previous = votes.get(user_id) if votes is not None else None
        if votes is not None:
            votes.pop(user_id, None)
        if not self._db_available:
            return True
        try:
            from src.api import db
            db.delete_message_feedback(message_id, user_id)
            return True
        except Exception as exc:
            logger.warning("Failed to clear feedback for message %s in Postgres (%s: %s).",
                            message_id, type(exc).__name__, exc)
            if had_before:
                self.message_feedback.setdefault(message_id, {})[user_id] = previous
            return False

    def get_session_feedback(self, session_id: str, user_id: str) -> dict[str, str]:
        """This user's votes for every message in a session, as
        {message_id: rating}. Postgres is authoritative when reachable, same
        reasoning as get_live_session. Falls back to this worker's dictionary
        otherwise, which is how the test suite runs."""
        if self._db_available:
            try:
                from src.api import db
                return db.get_session_feedback(session_id, user_id)
            except Exception as exc:
                logger.warning("Feedback lookup failed for session %s (%s: %s); "
                               "falling back to this worker's cache.",
                               session_id, type(exc).__name__, exc)
        session = self.sessions.get(session_id)
        if not session:
            return {}
        message_ids = {m.get("message_id") for m in session.get("messages", [])}
        result: dict[str, str] = {}
        for mid in message_ids:
            rating = self.message_feedback.get(mid, {}).get(user_id)
            if rating:
                result[mid] = rating
        return result

    def list_documents(self, course_id: str | None = None) -> list[dict[str, Any]]:
        documents = list(self._refresh_documents())
        if self.use_fixtures:
            documents = list(self.fixtures.get("documents", [])) + documents
        if course_id:
            uuid_form, code_form = self.resolve_course(course_id)
            if not code_form:
                return []
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

    def queue_upload(self, filename: str, file_size: int, course_id: str,
                     original_filename: str | None = None) -> dict[str, Any]:
        """Record an upload.

        `filename` is the name the file was stored under on disk, which is made
        unique per upload so two people uploading week1.pdf cannot overwrite
        each other. `original_filename` is what the uploader called it, and is
        what the UI shows. They differ by a short suffix.
        """
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
            "original_filename": original_filename or filename,
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
        # Refresh first, or deleting a document that was uploaded through the
        # other worker reports "not found" while the row and its chunks stay.
        before = len(self._refresh_documents())
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
    def __init__(self, data: dict, response_style: str = "concise"):
        self.answer           = data.get("answer", "")
        self.source_refs      = data.get("source_references", data.get("sources", []))
        self.is_fallback      = bool(data.get("is_fallback", data.get("fallback_used", False)))
        self.model_used       = "fixture"
        self.top_chunks       = []
        self.confidence       = "Medium"
        self.confidence_score = data.get("confidence", 0.5)
        self.response_style   = response_style


class _FixtureGenerator:
    """Fallback used when ChromaDB or generation is unavailable."""
    def __init__(self, state):
        self._state = state

    def generate(self, query: str, course_id: str = "CSIT321",
                 response_style: str = "concise", **_kwargs) -> _FixtureResponse:
        data = self._state.query_fixture(query)
        return _FixtureResponse(data, response_style=response_style)
