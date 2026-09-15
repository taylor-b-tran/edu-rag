"""Live-reloadable configuration (T8-08).

Two tiers, resolved per request so nothing needs a restart:

    per-course override  →  global setting  →  the environment default

Scope is either the literal ``global`` or a course code, so one table covers
both and a course row simply shadows the global one. Deleting an override
falls back to the tier below rather than to a hardcoded value.

Who may change what follows the same line drawn in T8-04: an admin owns
anything that affects every course or moves weights in and out of VRAM, and
the lecturer who owns a course tunes retrieval for that course only.

A note on scope, because it is easy to widen by accident. `top_k` and
`num_predict` were both measured on the host and changed nothing — 5 to 8
chunks moved an answer by ten characters, and raising the token cap produced a
byte-identical answer. They are settable because the task asks for them, not
because they are expected to help. The knob that measurably matters is
`response_style`, and the honest fix for a thin answer is a better default
rather than a slider.
"""
from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from src.api.routes.courses import _require_course_manager

settings_bp = Blueprint("settings", __name__, url_prefix="/api")

GLOBAL_SCOPE = "global"

_STYLES = {"concise", "detailed", "simple", "exam_prep", "socratic"}
_STRATEGIES = {"baseline", "evidence_cited", "few_shot_cited"}

# key -> (kind, low, high) for numbers, or (kind, allowed_set) for choices.
_NUMERIC = {
    "top_k": (int, 1, 20),
    "similarity_threshold": (float, 0.0, 1.0),
    "temperature": (float, 0.0, 2.0),
    "num_predict": (int, 64, 4096),
}
_CHOICE = {
    "response_style": _STYLES,
    "prompt_strategy": _STRATEGIES,
}
_STRING = {"ollama_model"}

# The models we have actually run against this corpus on the host, so the admin
# screen can offer a choice instead of a free-text box nobody can verify. This
# is a menu, not a whitelist: validation below still accepts any name, because
# the admin may have pulled something new that this list has not caught up with.
KNOWN_MODELS = [
    {
        "name": "gemma4:12b",
        "vram_gb": 11,
        "note": "Current default, chosen for staying close to the retrieved "
                "sources and citing only the chunks it used.",
    },
    {
        "name": "qwen3.5:9b",
        "vram_gb": 6,
        "note": "Faster and more detailed, but tends to pad an answer with "
                "retrieved material that is only loosely related.",
    },
    {
        "name": "qwen3:14b",
        "vram_gb": 11,
        "note": "Previous default. Kept so a change can be compared against it.",
    },
    {
        "name": "qwen2.5:7b",
        "vram_gb": 5,
        "note": "For 8 GB-class cards, where a 12B model would offload to RAM.",
    },
    {
        "name": "llama3.2",
        "vram_gb": 3,
        "note": "CPU-only fallback for a machine with no usable GPU.",
    },
]

# Anything that changes which weights are resident, or that applies to every
# course at once, stays with the admin.
COURSE_SCOPED = {"top_k", "similarity_threshold", "response_style", "prompt_strategy"}
GLOBAL_ONLY = {"ollama_model", "temperature", "num_predict"}
ALL_KEYS = COURSE_SCOPED | GLOBAL_ONLY


def _state():
    return current_app.config["EDURAG_API_STATE"]


def _require_auth():
    user = _state().validate_bearer(request.headers.get("Authorization"))
    if user is None:
        return None, (jsonify({"error": "Authentication required."}), 401)
    return user, None


def _require_admin():
    user, err = _require_auth()
    if err:
        return None, err
    if user.get("role") != "admin":
        return None, (jsonify({"error": "Admin role required."}), 403)
    return user, None


def _require_db():
    if _state().db_available:
        return None
    return jsonify({
        "error": "Settings require the database backend, which is currently unavailable.",
    }), 503


def _stored(scope: str) -> dict[str, object]:
    """Stored overrides for a scope, or {} if they cannot be read.

    A settings read is never important enough to turn into a 500 — the caller
    can still be told what is in effect from the defaults.
    """
    try:
        from src.api import db
        return db.get_settings(scope)
    except Exception:
        current_app.logger.warning("Could not read %s settings.", scope, exc_info=True)
        return {}


def validate(key: str, value, allowed: set[str]) -> tuple[object, str | None]:
    """Return (coerced_value, None) or (None, message)."""
    if key not in allowed:
        return None, f"'{key}' cannot be set at this level. Allowed: {sorted(allowed)}."

    if key in _NUMERIC:
        kind, low, high = _NUMERIC[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None, f"'{key}' must be a number."
        coerced = kind(value)
        if not (low <= coerced <= high):
            return None, f"'{key}' must be between {low} and {high}."
        return coerced, None

    if key in _CHOICE:
        if not isinstance(value, str) or value not in _CHOICE[key]:
            return None, f"'{key}' must be one of {sorted(_CHOICE[key])}."
        return value, None

    if key in _STRING:
        if not isinstance(value, str) or not value.strip():
            return None, f"'{key}' must be a non-empty string."
        return value.strip(), None

    return None, f"'{key}' is not a known setting."


def _apply(scope: str, body: dict, allowed: set[str], actor: str):
    """Validate the whole body before writing any of it, so a request either
    lands completely or not at all."""
    if not isinstance(body, dict) or not body:
        return None, (jsonify({"error": "Send a JSON object of settings to change."}), 400)

    cleaned: dict[str, object] = {}
    clears: list[str] = []
    for key, value in body.items():
        if value is None:
            if key not in allowed:
                return None, (jsonify({
                    "error": "invalid setting",
                    "message": f"'{key}' cannot be set at this level.",
                }), 400)
            clears.append(key)
            continue
        coerced, message = validate(key, value, allowed)
        if message:
            return None, (jsonify({"error": "invalid setting", "message": message}), 400)
        cleaned[key] = coerced

    from src.api import db
    for key in clears:
        db.delete_setting(scope, key)
    for key, value in cleaned.items():
        db.set_setting(scope, key, value, updated_by=actor)
    return db.get_settings(scope), None


# ─── global ───────────────────────────────────────────────────────────

@settings_bp.get("/settings")
def read_global():
    """Readable by any signed-in user: the UI needs the values in effect."""
    _, err = _require_auth()
    if err:
        return err
    db_err = _require_db()
    if db_err:
        return db_err
    return jsonify({
        "scope": GLOBAL_SCOPE,
        "settings": _stored(GLOBAL_SCOPE),
        "known_models": KNOWN_MODELS,
        # What a question would actually be answered with right now. Without
        # this the admin screen had to guess, and guessed the first catalogue
        # entry, which is only right on a host that happens to run it.
        "effective_model": effective_settings().get("ollama_model"),
    })


@settings_bp.patch("/settings")
def write_global():
    user, err = _require_admin()
    if err:
        return err
    db_err = _require_db()
    if db_err:
        return db_err

    updated, err = _apply(GLOBAL_SCOPE, request.get_json(silent=True) or {},
                          ALL_KEYS, str(user.get("user_id") or user.get("email")))
    if err:
        return err
    return jsonify({"scope": GLOBAL_SCOPE, "settings": updated})


# ─── per course ───────────────────────────────────────────────────────

@settings_bp.get("/courses/<course_code>/settings")
def read_course(course_code: str):
    """Anyone in the course can see how it is tuned."""
    user, err = _require_auth()
    if err:
        return err
    db_err = _require_db()
    if db_err:
        return db_err
    if not _state().is_enrolled(user, course_code):
        return jsonify({"error": "Not enrolled in this course."}), 403

    return jsonify({
        "scope": course_code,
        "settings": _stored(course_code),
        "effective": effective_settings(course_code),
    })


@settings_bp.patch("/courses/<course_code>/settings")
def write_course(course_code: str):
    """Admin, or the lecturer who owns this course (T8-04)."""
    user, _course, err = _require_course_manager(course_code)
    if err:
        return err

    updated, err = _apply(course_code, request.get_json(silent=True) or {},
                          COURSE_SCOPED, str(user.get("user_id") or user.get("email")))
    if err:
        return err
    return jsonify({
        "scope": course_code,
        "settings": updated,
        "effective": effective_settings(course_code),
    })


# ─── resolution ───────────────────────────────────────────────────────

def _env_defaults() -> dict[str, object]:
    """The values the pipeline would use with nothing stored."""
    from src.document_processor import rag_pipeline as rp
    return {
        "top_k": rp.TOP_K,
        "similarity_threshold": rp.SIMILARITY_THRESHOLD,
        "response_style": rp.DEFAULT_RESPONSE_STYLE,
        "prompt_strategy": rp.PROMPT_STRATEGY,
        "temperature": rp.OLLAMA_TEMPERATURE,
        "num_predict": rp.OLLAMA_NUM_PREDICT,
        "ollama_model": rp.OLLAMA_MODEL,
    }


def effective_settings(course_code: str | None = None) -> dict[str, object]:
    """Course override, then global, then the environment default.

    Never raises: a settings lookup failing must not take the query path down
    with it, so a broken read falls through to the defaults already in use.
    """
    resolved = _env_defaults()
    state = _state()
    if not getattr(state, "db_available", False):
        return resolved
    resolved.update(_stored(GLOBAL_SCOPE))
    if course_code:
        resolved.update({k: v for k, v in _stored(course_code).items()
                         if k in COURSE_SCOPED})
    return resolved
