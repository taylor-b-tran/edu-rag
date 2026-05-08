from __future__ import annotations

from flask import Flask

from src.api.routes.auth import auth_bp
from src.api.routes.documents import documents_bp
from src.api.routes.health import health_bp
from src.api.routes.query import query_bp
from src.api.routes.sessions import sessions_bp


def register_routes(app: Flask) -> None:
    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(query_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(sessions_bp)

    @app.after_request
    def _cors(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
        return response

    @app.route("/api/<path:_>", methods=["OPTIONS"])
    def _preflight(_):
        return "", 204
