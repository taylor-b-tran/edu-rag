from __future__ import annotations

from flask import Blueprint, current_app, jsonify


health_bp = Blueprint("health", __name__, url_prefix="/api")


def _state():
    return current_app.config["EDURAG_API_STATE"]


@health_bp.get("/health")
def health():
    state = _state()
    return jsonify(
        {
            "status": "ok",
            "mode": state.backend_mode,
            "rag_available": state.rag_available,
            "fixture_loaded": state.fixture_loaded,
            "routes": [
                "/api/auth/login",
                "/api/query",
                "/api/upload",
                "/api/documents",
                "/api/sessions",
            ],
        }
    )


@health_bp.get("/admin/stats")
@health_bp.get("/metrics")
def metrics():
    state = _state()
    return jsonify(
        {
            "documents": len(state.list_documents()),
            "sessions": len(state.sessions),
            "indexing_jobs": len(state.indexing_jobs),
            "mode": state.backend_mode,
        }
    )


@health_bp.get("/admin/audit-logs")
@health_bp.get("/logs")
def logs():
    return jsonify({"logs": [], "mode": _state().backend_mode})
