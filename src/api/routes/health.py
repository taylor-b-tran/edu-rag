from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request


health_bp = Blueprint("health", __name__, url_prefix="/api")


def _state():
    return current_app.config["EDURAG_API_STATE"]


def _require_admin():
    """Gate the operational endpoints. /api/health stays open because the
    container healthcheck calls it unauthenticated."""
    user = _state().validate_bearer(request.headers.get("Authorization"))
    if user is None:
        return jsonify({"error": "Authentication required."}), 401
    if user.get("role") != "admin":
        return jsonify({"error": "Admin role required."}), 403
    return None


@health_bp.get("/health")
def health():
    state = _state()
    from src.document_processor.ingest_corpus import embedder_status
    return jsonify(
        {
            "status": "ok",
            "mode": state.backend_mode,
            "rag_available": state.rag_available,
            "fixture_loaded": state.fixture_loaded,
            "embedder": embedder_status(),
            "warmup": getattr(state, "warmup_status", {"status": "unknown"}),
            "routes": [
                "/api/auth/login",
                "/api/query",
                "/api/upload",
                "/api/documents",
                "/api/sessions",
                "/api/warmup",
                "/api/courses",
            ],
        }
    )


@health_bp.get("/admin/stats")
@health_bp.get("/metrics")
def metrics():
    err = _require_admin()
    if err:
        return err
    state = _state()
    fixture_users = state.fixtures.get("demo_users", []) if state.fixture_loaded else []
    total_messages = sum(len(s.get("messages", [])) for s in state.sessions.values())
    return jsonify(
        {
            "documents": len(state.list_documents()),
            "uploaded_documents": len(state.uploaded_documents),
            "indexing_jobs": len(state.indexing_jobs),
            "sessions": len(state.sessions),
            "queries_total": total_messages,
            "users": len(fixture_users),
            "courses": len(state.list_courses()),
            "mode": state.backend_mode,
            "warmup": getattr(state, "warmup_status", {"status": "unknown"}),
        }
    )


@health_bp.get("/admin/audit-logs")
@health_bp.get("/logs")
def logs():
    err = _require_admin()
    if err:
        return err
    return jsonify({"logs": [], "mode": _state().backend_mode})


@health_bp.post("/warmup")
def trigger_warmup():
    """Synchronously warm Ollama on demand (admin only)."""
    state = _state()
    user = state.validate_bearer(request.headers.get("Authorization"))
    if user is None:
        return jsonify({"error": "Authentication required."}), 401
    if user.get("role") not in {"admin", "lecturer"}:
        return jsonify({"error": "Admin or lecturer role required."}), 403

    from src.api import warmup
    outcome = warmup.warmup_ollama()
    outcome["status"] = "ok" if outcome.get("generated") else "degraded"
    state.warmup_status = outcome
    return jsonify(outcome)
