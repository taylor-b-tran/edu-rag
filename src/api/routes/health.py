from __future__ import annotations

from flask import Blueprint, current_app, jsonify


health_bp = Blueprint("health", __name__, url_prefix="/api")


def _state():
    return current_app.config["EDURAG_API_STATE"]


@health_bp.get("/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "mode": "fixture",
            "fixture_loaded": _state().fixture_loaded,
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
    return jsonify(
        {
            "documents": len(_state().list_documents()),
            "sessions": len(_state().sessions),
            "indexing_jobs": len(_state().indexing_jobs),
            "mode": "fixture",
        }
    )


@health_bp.get("/admin/audit-logs")
@health_bp.get("/logs")
def logs():
    return jsonify({"logs": [], "mode": "fixture"})
