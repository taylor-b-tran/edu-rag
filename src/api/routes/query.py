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


# T8-10: lets the UI render the picker from a single source of truth instead of hardcoding the five style names/labels
# client-side. No auth required — this is static config, not user data.
@query_bp.get("/response-styles")
def response_styles():
    from src.document_processor.rag_pipeline import RESPONSE_STYLES, DEFAULT_RESPONSE_STYLE
    return jsonify({
        "styles": [
            {"id": style_id, **info} for style_id, info in RESPONSE_STYLES.items()
        ],
        "default": DEFAULT_RESPONSE_STYLE,
    })


def _check_rate(key: str, state=None) -> bool:
    """Rate-limit one caller.

    The key is the authenticated user id, not the client address. Streamlit
    calls this API server-side, so every student's request arrives from the
    same container IP - keying on the address made the limit one bucket shared
    by the whole class, where the eleventh question in a minute from anyone at
    all was rejected.

    T8-24: when Postgres is available, the count is checked/recorded there
    instead of the in-memory _RATE_STORE below. This used to be a plain
    module-level dict, which meant each gunicorn worker (T8-23) had its own
    separate count — a caller could get 10 requests per worker instead of 10
    total. The in-memory path stays as a fallback for when Postgres isn't
    reachable (and is what the existing tests exercise, since there's no
    live Postgres in CI).
    """
    if state is not None and getattr(state, "_db_available", False):
        try:
            from src.api import db
            return db.check_and_record_rate(key, _RATE_WINDOW, _RATE_MAX)
        except Exception:
            logger.warning("Postgres rate-limit check failed; falling back to in-memory.")

    now = time.time()
    window_start = now - _RATE_WINDOW

    # Drop callers whose window has fully expired. Without this the store grows
    # for the life of the process, one entry per key ever seen.
    for stale in [k for k, ts in _RATE_STORE.items() if not ts or ts[-1] <= window_start]:
        if stale != key:
            del _RATE_STORE[stale]

    timestamps = [t for t in _RATE_STORE.get(key, []) if t > window_start]
    if len(timestamps) >= _RATE_MAX:
        _RATE_STORE[key] = timestamps
        return False
    timestamps.append(now)
    _RATE_STORE[key] = timestamps
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

    # Authenticate before rate-limiting: the limit is per user, so we need to
    # know who is asking. An unauthenticated request is rejected below without
    # reaching retrieval or the model, so nothing expensive runs first.
    user = state.validate_bearer(request.headers.get("Authorization"))
    if user is None:
        return jsonify({"error": "Authentication required."}), 401

    rate_key = str(user.get("user_id") or user.get("email") or "unknown")
    if not _check_rate(rate_key, state):
        logger.warning("Rate limit exceeded for user %s", rate_key)
        return jsonify({"error": "Too many requests. Limit is 10 per minute."}), 429

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
    response_style_raw = body.get("response_style")
    if not isinstance(question_raw, str):
        return jsonify({"error": "query must be a string"}), 400
    if not isinstance(course_id_raw, str):
        return jsonify({"error": "course_id must be a string"}), 400
    if session_id is not None and not isinstance(session_id, str):
        return jsonify({"error": "session_id must be a string"}), 400
    if response_style_raw is not None:
        if not isinstance(response_style_raw, str):
            return jsonify({"error": "response_style must be a string"}), 400
        from src.document_processor.rag_pipeline import RESPONSE_STYLES
        if response_style_raw not in RESPONSE_STYLES:
            return jsonify({
                "error": "invalid response_style",
                "message": f"response_style must be one of: {', '.join(sorted(RESPONSE_STYLES))}",
            }), 400

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
        generated = state.get_generator().generate(
            question, course_id=course_id, response_style=response_style_raw)
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
        "response_style": generated.response_style,
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
