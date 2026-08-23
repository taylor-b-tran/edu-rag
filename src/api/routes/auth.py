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

    logger.info("New %s account created: %s", role, email)
    return jsonify(state.issue_tokens(user)), 201


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
    return jsonify(_state().issue_tokens(user))


@auth_bp.post("/refresh")
def refresh():
    try:
        body = request.get_json(force=False, silent=False) or {}
    except Exception:
        return jsonify({"error": "invalid JSON body"}), 400
    refresh_token = body.get("refresh_token")
    # Retires the token as it is read, so a captured refresh token cannot be
    # replayed after the legitimate holder has already used it.
    token_state = _state().consume_refresh_token(refresh_token)
    if not token_state:
        return jsonify({"error": "invalid or expired refresh token"}), 401

    user = _state().find_user_any_source(token_state.get("email", ""))
    if not user:
        return jsonify({"error": "user no longer available"}), 401
    return jsonify(_state().issue_tokens(user))


@auth_bp.post("/logout")
def logout():
    auth_header = request.headers.get("Authorization")
    token = auth_header.partition(" ")[2] if auth_header else ""
    if token:
        _state().access_tokens.pop(token, None)
    return jsonify({"status": "success", "message": "Logged out successfully."})
