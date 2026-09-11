from __future__ import annotations

import os

from flask import Flask

from src.api.routes.auth import auth_bp
from src.api.routes.courses import courses_bp
from src.api.routes.settings import settings_bp
from src.api.routes.documents import documents_bp
from src.api.routes.feedback import feedback_bp
from src.api.routes.health import health_bp
from src.api.routes.query import query_bp
from src.api.routes.sessions import sessions_bp

_ALLOWED_ORIGIN = os.environ.get("PAEDIA_ALLOWED_ORIGIN", "http://localhost:8501")


def register_routes(app: Flask) -> None:
    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(query_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(sessions_bp)
    app.register_blueprint(feedback_bp)
    app.register_blueprint(courses_bp)
    app.register_blueprint(settings_bp)

    @app.after_request
    def _cors(response):
        response.headers["Access-Control-Allow-Origin"] = _ALLOWED_ORIGIN
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PATCH, DELETE, OPTIONS"
        return response

    @app.route("/api/<path:_>", methods=["OPTIONS"])
    def _preflight(_):
        return "", 204