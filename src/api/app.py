from __future__ import annotations

import os

from flask import Flask

from src.api.routes import register_routes
from src.api.state import APIState


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["EDURAG_API_STATE"] = APIState()
    register_routes(app)
    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True, use_reloader=False)
