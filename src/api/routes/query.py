from __future__ import annotations

import logging
import time

from flask import Blueprint, current_app, jsonify, request

logger = logging.getLogger(__name__)

query_bp = Blueprint("query", __name__, url_prefix="/api")

_RATE_STORE: dict[str, list[float]] = {}
_RATE_MAX = 10
_RATE_WINDOW = 60

_AMBIGUOUS_PATTERNS = (
    "tell me everything",
    "explain everything",
    "what do you know",
    "tell me about the course",
    "summarize everything",
    "give me all",
    "what is this course",
)


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


def _is_ambiguous(question: str) -> bool:
    """Return True if the question is too vague for meaningful RAG retrieval."""
    lowered = question.lower()
    if len(question.split()) < 3:
        return True
    return any(pat in lowered for pat in _AMBIGUOUS_PATTERNS)


@query_bp.post("/query")
def query():
    state = _state()
    ip = request.remote_addr or "unknown"
    if not _check_rate(ip):
        logger.warning("Rate limit exceeded for IP %s", ip)
        return jsonify({"error": "Too many requests. Limit is 10 per minute."}), 429

    user = state.validate_bearer(request.headers.get("Authorization"))
    if user is None:
        return jsonify({"error": "Authentication required."}), 401

    try:
        body = request.get_json(force=False, silent=False)
    except Exception:
        return jsonify({"error": "invalid JSON body"}), 400
    if body is None:
        body = {}
    if not isinstance(body, dict):
        return jsonify({"error": "JSON body must be an object"}), 400

    question_raw = body.get("query") or ""
    course_id_raw = body.get("course_id", "CSIT321")
    session_id = body.get("session_id")
    if not isinstance(question_raw, str):
        return jsonify({"error": "query must be a string"}), 400
    if not isinstance(course_id_raw, str):
        return jsonify({"error": "course_id must be a string"}), 400
    if session_id is not None and not isinstance(session_id, str):
        return jsonify({"error": "session_id must be a string"}), 400

    question = question_raw.strip()
    course_id = course_id_raw.strip()

    if not question:
        return jsonify({"error": "query is required"}), 400
    if not course_id:
        return jsonify({"error": "course_id is required"}), 400

    if _is_ambiguous(question):
        logger.info("Ambiguous query from user %s: %r", user.get("user_id"), question)
        return jsonify({
            "error": "ambiguous_query",
            "message": (
                "Your question is too broad for course-specific retrieval. "
                "Please ask about a specific topic, concept, or week from CSIT321 "
                "(e.g. 'What is retrieval-augmented generation?' or 'Explain the chunking strategy from Week 5')."
            ),
        }), 422

    if not state.is_enrolled(user, course_id):
        logger.warning("User %s attempted access to unauthorised course %s", user.get("user_id"), course_id)
        return jsonify({"error": "Not enrolled in this course."}), 403

    started = time.time()
    try:
        generated = state.get_generator().generate(question, course_id=course_id)
    except Exception as exc:
        logger.error("Generation failed for user %s: %s", user.get("user_id"), exc)
        return jsonify({
            "error": "generation_unavailable",
            "message": (
                "The answer generation service is temporarily unavailable. "
                "Please ensure Ollama is running (`ollama serve`) and try again."
            ),
            "detail": str(exc),
        }), 503

    result = {
        "answer": generated.answer,
        "source_references": generated.source_refs,
        "confidence": generated.confidence,
        "confidence_score": generated.confidence_score,
        "model_used": generated.model_used,
        "is_fallback": generated.is_fallback,
    }
    session_id = state.record_session_message(
        session_id=session_id,
        user_id=user.get("user_id"),
        course_id=course_id,
        question=question,
        answer=result,
    )
    result.update(
        {
            "session_id": session_id,
            "backend_mode": state.backend_mode,
            "latency_ms": round((time.time() - started) * 1000),
        }
    )
    return jsonify(result)
