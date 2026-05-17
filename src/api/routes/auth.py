from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request


auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def _state():
    return current_app.config["EDURAG_API_STATE"]


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
    token_state = _state().refresh_tokens.get(refresh_token)
    if not token_state:
        return jsonify({"error": "invalid refresh token"}), 401

    user = _state().find_demo_user(token_state.get("email", ""))
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
