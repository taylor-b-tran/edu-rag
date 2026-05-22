from __future__ import annotations

import logging
import time

from flask import Blueprint, current_app, jsonify, request

logger = logging.getLogger(__name__)

query_bp = Blueprint("query", __name__, url_prefix="/api")

_RATE_STORE: dict[str, list[float]] = {}
_RATE_MAX = 10
_RATE_WINDOW = 60


def _state():
    return current_app.config["EDURAG_API_STATE"]


def _check_rate(ip: str) -> bool:
    now = time.time()
    window_start = now - _RATE_WINDOW
    timestamps = [t for t in _RATE_STORE.get(ip, []) if t > window_start]
    if len(timestamps) >= _RATE_MAX:
        _RATE_STORE[ip] = timestamps
        return False
    timestamps.append(now)
    _RATE_STORE[ip] = timestamps
    return True


@query_bp.post("/query")
def query():
    ip = request.remote_addr or "unknown"
    if not _check_rate(ip):
        logger.warning("Rate limit exceeded for IP %s", ip)
        return jsonify({"error": "Too many requests. Limit is 10 per minute."}), 429

    user = _state().validate_bearer(request.headers.get("Authorization"))
    if user is None:
        return jsonify({"error": "Authentication required."}), 401

    try:
        body = request.get_json(force=False, silent=False) or {}
    except Exception:
        return jsonify({"error": "invalid JSON body"}), 400

    question = (body.get("query") or "").strip()
    course_id = body.get("course_id", "CSIT321")
    session_id = body.get("session_id")

    if not question:
        return jsonify({"error": "query is required"}), 400

    if not _state().is_enrolled(user, course_id):
        logger.warning("User %s attempted access to unauthorised course %s", user.get("user_id"), course_id)
        return jsonify({"error": "Not enrolled in this course."}), 403

    started = time.time()
    result = _state().get_generator().generate(question, course_id=course_id)
    session_id = _state().record_session_message(
        session_id=session_id,
        user_id=user.get("user_id"),
        course_id=course_id,
        question=question,
        answer=result,
    )
    result.update(
        {
            "session_id": session_id,
            "backend_mode": "chromadb",
            "latency_ms": round((time.time() - started) * 1000),
        }
    )
    return jsonify(result)
