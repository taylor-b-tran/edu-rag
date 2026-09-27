from __future__ import annotations

import logging

from flask import Blueprint, current_app, jsonify, request

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def _state():
    return current_app.config["EDURAG_API_STATE"]


# Signup may only ever create these. "admin" is deliberately absent: the role
# arrives in the request body, so accepting it would let anyone mint themselves
# an administrator.
_SELF_SIGNUP_ROLES = {"student", "lecturer"}

# bcrypt silently ignores anything past 72 bytes, so a longer password would be
# accepted at signup and then effectively truncated at login. Reject instead.
_MIN_PASSWORD_LENGTH = 10
_MAX_PASSWORD_BYTES = 72

_WEAK_PASSWORDS = {
    "password", "password1", "password123", "12345678", "123456789", "1234567890",
    "qwertyuiop", "letmein123", "changeme", "admin12345", "iloveyou", "welcome123",
}


def _password_problem(password: str, email: str, username: str) -> str | None:
    """Return a human-readable reason the password is unusable, else None."""
    if len(password) < _MIN_PASSWORD_LENGTH:
        return f"Password must be at least {_MIN_PASSWORD_LENGTH} characters."
    if len(password.encode("utf-8")) > _MAX_PASSWORD_BYTES:
        return f"Password must be at most {_MAX_PASSWORD_BYTES} bytes."
    if password.lower() in _WEAK_PASSWORDS:
        return "That password is too common. Choose something less guessable."
    local_part = email.split("@", 1)[0].lower()
    if password.lower() in {email.lower(), username.lower(), local_part}:
        return "Password must not be your email or username."
    return None


@auth_bp.post("/signup")
def signup():
    state = _state()
    body = request.get_json(silent=True) or {}
    if not isinstance(body, dict):
        return jsonify({"error": "JSON body must be an object"}), 400

    email = (body.get("email") or "").strip().lower()
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""
    role = (body.get("role") or "student").strip().lower()

    if not email or "@" not in email:
        return jsonify({"error": "a valid email is required"}), 400
    if not username:
        return jsonify({"error": "username is required"}), 400
    if len(username) > 50:
        return jsonify({"error": "username must be at most 50 characters"}), 400
    if not isinstance(password, str):
        return jsonify({"error": "password must be a string"}), 400

    if role not in _SELF_SIGNUP_ROLES:
        logger.warning("Signup attempt with disallowed role %r for %s", role, email)
        return jsonify({
            "error": "invalid role",
            "message": f"Choose one of {sorted(_SELF_SIGNUP_ROLES)}.",
        }), 400

    problem = _password_problem(password, email, username)
    if problem:
        return jsonify({"error": "weak password", "message": problem}), 400

    if not state.db_available:
        return jsonify({
            "error": "signup_unavailable",
            "message": "Accounts require the database backend, which is currently unavailable.",
        }), 503

    from src.api import db
    user, taken = db.create_user(username=username, email=email, role=role, password=password)
    if user is None:
        return jsonify({
            "error": "already_registered",
            "message": f"That {taken} is already registered.",
        }), 409

    logger.info("New %s account created.", role)
    try:
        return jsonify(state.issue_tokens(user)), 201
    except Exception:
        logger.exception("Could not persist signup session")
        return jsonify({"error": "Session store unavailable; sign in again when available."}), 503


@auth_bp.post("/login")
def login():
    try:
        body = request.get_json(force=False, silent=False) or {}
    except Exception:
        return jsonify({"error": "invalid JSON body"}), 400
    email = (body.get("email") or "").strip()
    password = body.get("password") or ""
    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400

    user = _state().authenticate_user(email, password)
    if not user:
        return jsonify({"error": "invalid credentials"}), 401
    try:
        return jsonify(_state().issue_tokens(user))
    except Exception:
        logger.exception("Could not persist login session")
        return jsonify({"error": "Session store unavailable."}), 503


@auth_bp.post("/refresh")
def refresh():
    try:
        body = request.get_json(force=False, silent=False) or {}
    except Exception:
        return jsonify({"error": "invalid JSON body"}), 400
    refresh_token = body.get("refresh_token")
    try:
        tokens = _state().refresh_login(refresh_token)
    except Exception:
        logger.exception("Could not rotate login session")
        return jsonify({"error": "Session store unavailable."}), 503
    if not tokens:
        return jsonify({"error": "invalid or expired refresh token"}), 401
    return jsonify(tokens)


@auth_bp.get("/me")
def me():
    """Who this bearer token belongs to.

    Added for T9-14. The UI keeps the access token in a browser cookie so a
    page refresh no longer throws the user back to the login screen, and on
    reload it needs to turn that token back into a user. Asking the server
    rather than storing the user in the cookie alongside the token keeps one
    copy of the truth: role and enrolled courses are whatever they are now,
    not whatever they were when the cookie was written.

    A dead or expired token is a plain 401, which is the signal to clear the
    cookie and show the login form.
    """
    try:
        user = _state().validate_bearer(request.headers.get("Authorization"), report_store_error=True)
    except Exception:
        logger.exception("Could not validate restored session")
        return jsonify({"error": "Session store unavailable. Please retry."}), 503
    if user is None:
        return jsonify({"error": "Authentication required."}), 401
    if _state().db_available:
        # Token rows carry authorization, not the display profile. Resolve the
        # account so reload uses the same name as login, including older tokens.
        from src.api import db
        try:
            profile = db.get_user_by_email(user.get("email", ""))
        except Exception:
            logger.exception("Could not load session profile")
            return jsonify({"error": "Session profile unavailable. Please retry."}), 503
        if not profile or str(profile["user_id"]) != str(user.get("user_id")):
            return jsonify({"error": "Authentication required."}), 401
        user = {**user, **profile}
    else:
        profile = _state().find_demo_user(user.get("email", "")) or {}
        user = {**profile, **user}
    return jsonify({
        "id": user.get("user_id"),
        "email": user.get("email"),
        "username": user.get("username"),
        "name": user.get("name") or user.get("username") or user.get("email"),
        "role": user.get("role", "student"),
        "enrolled_courses": user.get("enrolled_courses", []),
    })


@auth_bp.post("/logout")
def logout():
    """End the login, not just the credential that was presented.

    This used to retire the access token alone, which read as a successful
    logout while the refresh token beside it still issued new access tokens.
    Both now go, via the family they share.

    The refresh token is read from the body as well, because tokens issued
    before families existed have no family to sweep -- the UI already sends it.
    """
    auth_header = request.headers.get("Authorization")
    token = auth_header.partition(" ")[2] if auth_header else ""
    try:
        body = request.get_json(silent=True) or {}
    except Exception:
        body = {}
    refresh_token = body.get("refresh_token") if isinstance(body, dict) else None
    if token or refresh_token:
        # Must reach Postgres: the rows outlive the worker that issued them,
        # and every other worker would keep honouring them.
        try:
            _state().revoke_login(token, refresh_token)
        except Exception:
            logger.exception("Could not revoke login session")
            return jsonify({"error": "Session store unavailable; logout was not confirmed."}), 503
    return jsonify({"status": "success", "message": "Logged out successfully."})
