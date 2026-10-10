# Authors: Andre Kahavidanage Namaratne, Thanh Binh Tran
from __future__ import annotations

import logging

from flask import Blueprint, current_app, jsonify, request

logger = logging.getLogger(__name__)

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
    state = _state()
    # Same cross-worker problem as get_session below: this worker's dictionary
    # only holds the sessions it happened to serve, so the sidebar was missing
    # roughly half of a user's own conversations.
    known = state.sessions
    if state.db_available:
        try:
            from src.api import db
            known = db.load_all_sessions()
        except Exception as exc:
            logger.warning("Could not list sessions from Postgres (%s: %s); "
                           "showing this worker's cache.", type(exc).__name__, exc)
    sessions = [
        s for s in known.values()
        if s.get("user_id") == user.get("user_id")
    ]
    return jsonify({"sessions": sessions})


@sessions_bp.get("/sessions/<session_id>")
def get_session(session_id: str):
    user, err = _require_auth()
    if err:
        return err
    session = _state().get_live_session(session_id)
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
    session = _state().get_live_session(session_id)
    if not session:
        return jsonify({"error": "session not found"}), 404
    if session.get("user_id") != user.get("user_id"):
        return jsonify({"error": "Access denied."}), 403
    _state().archive_session(session_id)
    return jsonify({"status": "success", "session_id": session_id})
