from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request


sessions_bp = Blueprint("sessions", __name__, url_prefix="/api")


def _state():
    return current_app.config["EDURAG_API_STATE"]


def _require_auth():
    user = _state().validate_bearer(request.headers.get("Authorization"))
    if user is None:
        return None, (jsonify({"error": "Authentication required."}), 401)
    return user, None


@sessions_bp.get("/sessions")
def list_sessions():
    user, err = _require_auth()
    if err:
        return err
    sessions = [
        s for s in _state().sessions.values()
        if s.get("user_id") == user.get("user_id")
    ]
    return jsonify({"sessions": sessions})


@sessions_bp.get("/sessions/<session_id>")
def get_session(session_id: str):
    user, err = _require_auth()
    if err:
        return err
    session = _state().sessions.get(session_id)
    if not session:
        return jsonify({"error": "session not found"}), 404
    if session.get("user_id") != user.get("user_id"):
        return jsonify({"error": "Access denied."}), 403
    return jsonify(session)


@sessions_bp.delete("/sessions/<session_id>")
def archive_session(session_id: str):
    user, err = _require_auth()
    if err:
        return err
    session = _state().sessions.get(session_id)
    if not session:
        return jsonify({"error": "session not found"}), 404
    if session.get("user_id") != user.get("user_id"):
        return jsonify({"error": "Access denied."}), 403
    _state().archive_session(session_id)
    return jsonify({"status": "success", "session_id": session_id})
