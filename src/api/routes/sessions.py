from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request


sessions_bp = Blueprint("sessions", __name__, url_prefix="/api")


def _state():
    return current_app.config["EDURAG_API_STATE"]


@sessions_bp.get("/sessions")
def list_sessions():
    user_id = request.args.get("user_id")
    sessions = list(_state().sessions.values())
    if user_id:
        sessions = [session for session in sessions if session.get("user_id") == user_id]
    return jsonify({"sessions": sessions})


@sessions_bp.get("/sessions/<session_id>")
def get_session(session_id: str):
    session = _state().sessions.get(session_id)
    if not session:
        return jsonify({"error": "session not found"}), 404
    return jsonify(session)


@sessions_bp.delete("/sessions/<session_id>")
def archive_session(session_id: str):
    session = _state().sessions.get(session_id)
    if not session:
        return jsonify({"error": "session not found"}), 404
    session["archived"] = True
    return jsonify({"status": "success", "session_id": session_id})
