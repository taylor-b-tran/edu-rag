from __future__ import annotations

import os

from flask import Flask

from src.api.routes import register_routes
from src.api.state import APIState


def create_app() -> Flask:
    app = Flask(__name__)
    # Cap the request body. Without this, an upload of any size was read whole
    # into memory, so a single request could exhaust the container. Flask
    # rejects anything larger with 413 before the view runs.
    app.config["MAX_CONTENT_LENGTH"] = int(
        os.environ.get("PAEDIA_MAX_UPLOAD_MB", "50")) * 1024 * 1024
    app.config["EDURAG_API_STATE"] = APIState()
    register_routes(app)
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
