from __future__ import annotations

import os
import logging

from flask import Flask, jsonify

from src.api.routes import register_routes
from src.api.state import APIState


def create_app() -> Flask:
    # Configure the application's namespace even when the WSGI server already
    # owns root logging. Leave third-party handlers and levels alone.
    app_logger = logging.getLogger("src")
    for handler in list(app_logger.handlers):
        if getattr(handler, "_paedia_console", False):
            app_logger.removeHandler(handler)
            handler.close()
    console = logging.StreamHandler()
    console._paedia_console = True
    console.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    app_logger.addHandler(console)
    app_logger.setLevel(logging.INFO)
    app = Flask(__name__)
    # Cap the request body. Without this, an upload of any size was read whole
    # into memory, so a single request could exhaust the container. Flask
    # rejects anything larger with 413 before the view runs.
    app.config["MAX_CONTENT_LENGTH"] = int(
        os.environ.get("PAEDIA_MAX_UPLOAD_MB", "50")) * 1024 * 1024
    app.config["EDURAG_API_STATE"] = APIState()
    register_routes(app)

    @app.errorhandler(503)
    def _unavailable(err):
        return jsonify({"error": "service_unavailable", "message": err.description}), 503

    @app.errorhandler(413)
    def _too_large(_err):
        """Answer oversized uploads as JSON like every other error.

        Werkzeug's default 413 is an HTML page, and a client that manages to
        read it gets markup where it expected an error object. The client also
        checks the size before sending, because past this limit the server
        stops reading and the connection is often reset before this response
        is ever seen.
        """
        limit_mb = app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024)
        return jsonify({
            "error": "file too large",
            "message": f"Uploads are limited to {limit_mb} MB.",
        }), 413

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # Debug mode serves the Werkzeug console, which executes Python from the
    # browser, to whoever triggers an unhandled exception. Off unless asked
    # for explicitly - never keyed off APP_ENV, which is "development" in the
    # Compose file that runs the shared host.
    debug = os.environ.get("PAEDIA_DEBUG", "").strip().lower() in {"1", "true", "yes"}
    app.run(host="0.0.0.0", port=port, debug=debug, use_reloader=False)
