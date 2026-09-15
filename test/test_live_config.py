"""Live-reloadable configuration (T8-08).

Settings resolve per request — course override, then global, then the value the
environment already had — so a change takes effect without restarting anything.
Restarting is not a neutral cost here: it logs everyone out and drops the model
out of VRAM, which is a 40-second wait for the next student.

The authorization line is the same one T8-04 drew. An admin owns anything that
affects every course or moves weights in and out of VRAM; the lecturer who owns
a course tunes retrieval for that course and nothing else.

`db` is stubbed, as in test_course_ownership, so these stay about authorization
and validation rather than about Postgres.
"""
from __future__ import annotations

import pytest

from src.api.app import create_app
from src.api.routes import settings as settings_mod


LECTURER = {"user_id": "lect-1", "email": "lecturer@uow.edu.au", "role": "lecturer",
            "enrolled_courses": ["OWNED101"]}
OTHER_LECTURER = {"user_id": "lect-2", "email": "other@uow.edu.au", "role": "lecturer",
                  "enrolled_courses": ["FOREIGN101"]}
STUDENT = {"user_id": "stu-1", "email": "student@uow.edu.au", "role": "student",
           "enrolled_courses": ["OWNED101"]}
ADMIN = {"user_id": "adm-1", "email": "admin@uow.edu.au", "role": "admin",
         "enrolled_courses": []}

OWNED = {"course_code": "OWNED101", "course_name": "Owned", "owner_id": LECTURER["user_id"]}
FOREIGN = {"course_code": "FOREIGN101", "course_name": "Theirs",
           "owner_id": OTHER_LECTURER["user_id"]}
_COURSES = {c["course_code"]: c for c in (OWNED, FOREIGN)}

AUTH = {"Authorization": "Bearer stub"}


@pytest.fixture
def store():
    """Stands in for the settings table: {(scope, key): value}."""
    return {}


@pytest.fixture
def client(monkeypatch, store):
    app = create_app()
    app.config.update(TESTING=True)
    state = app.config["EDURAG_API_STATE"]

    monkeypatch.setattr(type(state), "db_available", property(lambda self: True))
    monkeypatch.setattr(state, "_db_available", True)

    current = {"user": None}
    monkeypatch.setattr(type(state), "validate_bearer",
                        lambda self, authorization: current["user"])
    monkeypatch.setattr(type(state), "is_enrolled",
                        lambda self, user, cid: user.get("role") == "admin"
                        or cid in (user.get("enrolled_courses") or []))

    from src.api import db
    monkeypatch.setattr(db, "get_course_by_code", lambda code: _COURSES.get(code))
    monkeypatch.setattr(db, "get_settings",
                        lambda scope: {k[1]: v for k, v in store.items() if k[0] == scope})
    monkeypatch.setattr(db, "set_setting",
                        lambda scope, key, value, updated_by=None:
                        store.__setitem__((scope, key), value))
    monkeypatch.setattr(db, "delete_setting",
                        lambda scope, key: store.pop((scope, key), None))

    c = app.test_client()
    c.as_user = lambda u: current.__setitem__("user", u)
    return c


# --- who may change what ---------------------------------------------

def test_admin_can_change_a_global_setting(client, store):
    client.as_user(ADMIN)
    resp = client.patch("/api/settings", json={"top_k": 8}, headers=AUTH)
    assert resp.status_code == 200
    assert store[("global", "top_k")] == 8


def test_a_lecturer_cannot_change_global_settings(client):
    client.as_user(LECTURER)
    assert client.patch("/api/settings", json={"top_k": 8},
                        headers=AUTH).status_code == 403


def test_a_student_cannot_change_global_settings(client):
    client.as_user(STUDENT)
    assert client.patch("/api/settings", json={"top_k": 8},
                        headers=AUTH).status_code == 403


def test_any_signed_in_user_can_read_global_settings(client):
    """The UI has to show what is in effect."""
    client.as_user(STUDENT)
    assert client.get("/api/settings", headers=AUTH).status_code == 200


def test_anonymous_callers_are_rejected(client):
    client.as_user(None)
    assert client.get("/api/settings", headers=AUTH).status_code == 401
    assert client.patch("/api/settings", json={"top_k": 8}, headers=AUTH).status_code == 401


def test_the_owning_lecturer_can_tune_their_course(client, store):
    client.as_user(LECTURER)
    resp = client.patch("/api/courses/OWNED101/settings",
                        json={"similarity_threshold": 0.45}, headers=AUTH)
    assert resp.status_code == 200
    assert store[("OWNED101", "similarity_threshold")] == 0.45


def test_a_lecturer_cannot_tune_someone_elses_course(client):
    client.as_user(LECTURER)
    resp = client.patch("/api/courses/FOREIGN101/settings",
                        json={"top_k": 9}, headers=AUTH)
    assert resp.status_code == 403


def test_a_student_cannot_tune_a_course_they_are_in(client):
    client.as_user(STUDENT)
    assert client.patch("/api/courses/OWNED101/settings",
                        json={"top_k": 9}, headers=AUTH).status_code == 403


def test_a_student_can_read_the_settings_of_their_own_course(client):
    client.as_user(STUDENT)
    assert client.get("/api/courses/OWNED101/settings", headers=AUTH).status_code == 200


def test_a_student_cannot_read_a_course_they_are_not_in(client):
    client.as_user(STUDENT)
    assert client.get("/api/courses/FOREIGN101/settings", headers=AUTH).status_code == 403


# --- the tier line ----------------------------------------------------

def test_vram_level_settings_are_not_course_scoped(client):
    """Model choice decides what is resident in 16 GB of VRAM, which is shared
    by everyone. One lecturer must not be able to evict another's model."""
    client.as_user(LECTURER)
    resp = client.patch("/api/courses/OWNED101/settings",
                        json={"ollama_model": "llama3.2"}, headers=AUTH)
    assert resp.status_code == 400
    assert "cannot be set at this level" in resp.get_json()["message"]


def test_an_admin_sets_model_choice_globally(client, store):
    client.as_user(ADMIN)
    assert client.patch("/api/settings", json={"ollama_model": "llama3.2"},
                        headers=AUTH).status_code == 200
    assert store[("global", "ollama_model")] == "llama3.2"


# --- validation -------------------------------------------------------

@pytest.mark.parametrize("payload", [
    {"top_k": 0}, {"top_k": 999}, {"top_k": "five"}, {"top_k": True},
    {"similarity_threshold": 1.5}, {"similarity_threshold": -0.1},
    {"response_style": "shouty"}, {"num_predict": 4},
    {"prompt_strategy": "whatever"}, {"ollama_model": "  "},
    {"not_a_setting": 1},
])
def test_bad_values_are_refused(client, payload):
    client.as_user(ADMIN)
    assert client.patch("/api/settings", json=payload, headers=AUTH).status_code == 400


def test_a_rejected_key_leaves_the_rest_unwritten(client, store):
    """The body applies whole or not at all, so a typo cannot half-configure
    the system."""
    client.as_user(ADMIN)
    client.patch("/api/settings", json={"top_k": 7, "response_style": "shouty"},
                 headers=AUTH)
    assert ("global", "top_k") not in store


def test_an_empty_body_is_refused(client):
    client.as_user(ADMIN)
    assert client.patch("/api/settings", json={}, headers=AUTH).status_code == 400


# --- resolution -------------------------------------------------------

def test_course_setting_beats_global(client, store):
    store[("global", "top_k")] = 6
    store[("OWNED101", "top_k")] = 9
    client.as_user(ADMIN)
    body = client.get("/api/courses/OWNED101/settings", headers=AUTH).get_json()
    assert body["effective"]["top_k"] == 9


def test_global_beats_the_environment_default(client, store):
    store[("global", "top_k")] = 6
    client.as_user(ADMIN)
    body = client.get("/api/courses/OWNED101/settings", headers=AUTH).get_json()
    assert body["effective"]["top_k"] == 6


def test_with_nothing_stored_the_defaults_stand(client):
    from src.document_processor import rag_pipeline as rp
    client.as_user(ADMIN)
    body = client.get("/api/courses/OWNED101/settings", headers=AUTH).get_json()
    assert body["effective"]["top_k"] == rp.TOP_K
    assert body["effective"]["similarity_threshold"] == rp.SIMILARITY_THRESHOLD


def test_clearing_an_override_falls_back(client, store):
    store[("global", "top_k")] = 6
    store[("OWNED101", "top_k")] = 9
    client.as_user(LECTURER)

    client.patch("/api/courses/OWNED101/settings", json={"top_k": None}, headers=AUTH)

    assert ("OWNED101", "top_k") not in store
    body = client.get("/api/courses/OWNED101/settings", headers=AUTH).get_json()
    assert body["effective"]["top_k"] == 6, "should fall back to global, not to the default"


def test_a_global_only_key_never_leaks_from_a_course_row(client, store):
    """Even if a row somehow exists, course scope must not override a
    VRAM-level setting."""
    store[("OWNED101", "ollama_model")] = "sneaky"
    client.as_user(ADMIN)
    body = client.get("/api/courses/OWNED101/settings", headers=AUTH).get_json()
    assert body["effective"]["ollama_model"] != "sneaky"


def test_resolution_survives_a_database_error(client, monkeypatch):
    """A settings read failing must not take the query path down with it."""
    from src.api import db

    def boom(scope):
        raise RuntimeError("postgres is away")

    monkeypatch.setattr(db, "get_settings", boom)
    from src.document_processor import rag_pipeline as rp
    client.as_user(ADMIN)
    resp = client.get("/api/courses/OWNED101/settings", headers=AUTH)
    assert resp.status_code == 200
    assert resp.get_json()["effective"]["top_k"] == rp.TOP_K


# --- the pipeline actually honours them -------------------------------

def test_generate_no_longer_freezes_top_k_at_import(client):
    """`top_k=TOP_K` as a default argument is evaluated once, when the function
    is defined, so live config could never have reached it."""
    import inspect
    from src.document_processor.rag_pipeline import LLMResponseGeneration, VectorRetriever

    for fn in (LLMResponseGeneration.generate, VectorRetriever.search):
        assert inspect.signature(fn).parameters["top_k"].default is None


def test_generate_accepts_a_per_call_threshold():
    import inspect
    from src.document_processor.rag_pipeline import LLMResponseGeneration
    params = inspect.signature(LLMResponseGeneration.generate).parameters
    assert "similarity_threshold" in params
    assert params["similarity_threshold"].default is None


# --- the model catalogue ---------------------------------------------

def test_the_admin_screen_is_offered_the_models_we_measured(client):
    """The picker's options come from the API, next to the validation that
    accepts them, so the notes cannot drift away from what is allowed."""
    client.as_user(ADMIN)
    body = client.get("/api/settings", headers=AUTH).get_json()
    names = [m["name"] for m in body["known_models"]]
    assert "gemma4:12b" in names
    assert len(names) == len(set(names))


def test_a_model_outside_the_catalogue_is_still_accepted(client, store):
    """The catalogue is a menu, not a whitelist. An admin who has just pulled
    something new must not be blocked by a list that has not caught up."""
    client.as_user(ADMIN)
    catalogued = {m["name"] for m in settings_mod.KNOWN_MODELS}
    fresh = "mistral-small:24b"
    assert fresh not in catalogued

    assert client.patch("/api/settings", json={"ollama_model": fresh},
                        headers=AUTH).status_code == 200
    assert store[("global", "ollama_model")] == fresh
