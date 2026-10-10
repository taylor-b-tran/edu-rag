# Authors: Thanh Binh Tran, Tung Phuong Anh Huynh
import os

from src.api.app import app


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # Debug mode serves the Werkzeug console, which executes Python from the
    # browser, to whoever triggers an unhandled exception. Off unless asked
    # for explicitly - never keyed off APP_ENV, which is "development" in the
    # Compose file that runs the shared host.
    debug = os.environ.get("PAEDIA_DEBUG", "").strip().lower() in {"1", "true", "yes"}
    app.run(host="0.0.0.0", port=port, debug=debug, use_reloader=False)
