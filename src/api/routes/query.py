from __future__ import annotations

import time

from flask import Blueprint, current_app, jsonify, request


query_bp = Blueprint("query", __name__, url_prefix="/api")


def _state():
    return current_app.config["EDURAG_API_STATE"]


@query_bp.post("/query")
def query():
    body = request.get_json(force=True, silent=True) or {}
    question = (body.get("query") or "").strip()
    course_id = body.get("course_id", "CSIT321")
    session_id = body.get("session_id")

    if not question:
        return jsonify({"error": "query is required"}), 400

    started = time.time()
    user = _state().validate_bearer(request.headers.get("Authorization")) or {}
    result = _state().query_fixture(question)
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
            "backend_mode": "fixture",
            "latency_ms": round((time.time() - started) * 1000),
        }
    )
    return jsonify(result)
