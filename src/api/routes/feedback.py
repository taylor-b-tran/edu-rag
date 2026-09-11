from __future__ import annotations

import logging

from flask import Blueprint, current_app, jsonify, request

logger = logging.getLogger(__name__)

feedback_bp = Blueprint("feedback", __name__, url_prefix="/api")

_VALID_RATINGS = {"up", "down"}


def _state():
    return current_app.config["EDURAG_API_STATE"]


def _require_auth():
    user = _state().validate_bearer(request.headers.get("Authorization"))
    if user is None:
        return None, (jsonify({"error": "Authentication required."}), 401)
    return user, None


def _require_own_message(user, session_id: str, message_id: str):
    """Loads the session, checks it belongs to the caller, and checks the
    message is actually in it. Returns (message, error_response); message is
    None when error_response is set."""
    state = _state()
    session = state.get_live_session(session_id)
    if not session:
        return None, (jsonify({"error": "session not found"}), 404)
    if session.get("user_id") != user.get("user_id"):
        return None, (jsonify({"error": "Access denied."}), 403)
    message = state.find_message(session_id, message_id)
    if not message:
        return None, (jsonify({"error": "message not found"}), 404)
    return message, None


@feedback_bp.put("/sessions/<session_id>/messages/<message_id>/feedback")
def set_feedback(session_id: str, message_id: str):
    """Record (or change) a thumbs up/down on one answer. Idempotent: voting
    the same way twice, or switching your vote, is one row either way -
    see upsert_message_feedback."""
    user, err = _require_auth()
    if err:
        return err
    _, err = _require_own_message(user, session_id, message_id)
    if err:
        return err

    try:
        body = request.get_json(force=False, silent=False)
    except Exception:
        return jsonify({"error": "invalid JSON body"}), 400
    if not isinstance(body, dict):
        return jsonify({"error": "JSON body must be an object"}), 400

    rating = body.get("rating")
    if rating not in _VALID_RATINGS:
        return jsonify({
            "error": "invalid rating",
            "message": f"rating must be one of: {', '.join(sorted(_VALID_RATINGS))}",
        }), 400

    _state().set_message_feedback(message_id, user.get("user_id"), rating)
    return jsonify({"message_id": message_id, "rating": rating})


@feedback_bp.delete("/sessions/<session_id>/messages/<message_id>/feedback")
def clear_feedback(session_id: str, message_id: str):
    """Un-toggle a vote (pressing the same thumb again clears it rather than
    just re-recording it — that choice belongs to the screen this backs, this
    endpoint just makes it possible)."""
    user, err = _require_auth()
    if err:
        return err
    _, err = _require_own_message(user, session_id, message_id)
    if err:
        return err

    _state().clear_message_feedback(message_id, user.get("user_id"))
    return jsonify({"message_id": message_id, "rating": None})


@feedback_bp.get("/sessions/<session_id>/feedback")
def get_session_feedback(session_id: str):
    """This caller's votes for every message in a session, as
    {message_id: "up" | "down"}, so a screen can restore every thumb's state
    in one call instead of one request per message."""
    user, err = _require_auth()
    if err:
        return err
    state = _state()
    session = state.get_live_session(session_id)
    if not session:
        return jsonify({"error": "session not found"}), 404
    if session.get("user_id") != user.get("user_id"):
        return jsonify({"error": "Access denied."}), 403
    return jsonify({"feedback": state.get_session_feedback(session_id, user.get("user_id"))})
