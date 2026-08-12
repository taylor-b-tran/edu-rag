from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

courses_bp = Blueprint("courses", __name__, url_prefix="/api")

_VALID_MEMBERSHIP_ROLES = {"student", "lecturer"}


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
        "error": "Course management requires the database backend, which is currently unavailable.",
    }), 503


@courses_bp.get("/courses")
def list_courses():
    _, err = _require_auth()
    if err:
        return err
    return jsonify({"courses": _state().list_courses()})


@courses_bp.post("/courses")
def create_course():
    _, err = _require_admin()
    if err:
        return err

    body = request.get_json(silent=True) or {}
    course_code = (body.get("course_code") or "").strip()
    course_name = (body.get("course_name") or body.get("name") or "").strip()
    description = body.get("description")
    if not course_code or not course_name:
        return jsonify({"error": "course_code and course_name are required"}), 400

    db_err = _require_db()
    if db_err:
        return db_err

    from src.api import db
    course = db.create_course(course_code, course_name, description)
    if course is None:
        return jsonify({"error": f"course_code '{course_code}' already exists"}), 409
    return jsonify({"course": course}), 201


@courses_bp.patch("/courses/<course_code>")
def update_course(course_code: str):
    _, err = _require_admin()
    if err:
        return err
    db_err = _require_db()
    if db_err:
        return db_err

    body = request.get_json(silent=True) or {}
    from src.api import db
    course = db.update_course(
        course_code,
        course_name=body.get("course_name") or body.get("name"),
        description=body.get("description"),
        is_active=body.get("is_active"),
    )
    if course is None:
        return jsonify({"error": f"course '{course_code}' not found"}), 404
    return jsonify({"course": course})


@courses_bp.delete("/courses/<course_code>")
def deactivate_course(course_code: str):
    _, err = _require_admin()
    if err:
        return err
    db_err = _require_db()
    if db_err:
        return db_err

    from src.api import db
    course = db.update_course(course_code, is_active=False)
    if course is None:
        return jsonify({"error": f"course '{course_code}' not found"}), 404
    return jsonify({"status": "deactivated", "course": course})


@courses_bp.get("/courses/<course_code>/members")
def list_members(course_code: str):
    _, err = _require_admin()
    if err:
        return err
    db_err = _require_db()
    if db_err:
        return db_err

    from src.api import db
    if db.get_course_by_code(course_code) is None:
        return jsonify({"error": f"course '{course_code}' not found"}), 404
    return jsonify({"members": db.list_course_members(course_code)})


@courses_bp.post("/courses/<course_code>/members")
def add_member(course_code: str):
    _, err = _require_admin()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    email = (body.get("email") or "").strip()
    membership_role = body.get("membership_role") or body.get("role") or "student"
    if not email:
        return jsonify({"error": "email is required"}), 400
    if membership_role not in _VALID_MEMBERSHIP_ROLES:
        return jsonify({
            "error": f"membership_role must be one of {sorted(_VALID_MEMBERSHIP_ROLES)}",
        }), 400

    db_err = _require_db()
    if db_err:
        return db_err

    from src.api import db
    if db.get_course_by_code(course_code) is None:
        return jsonify({"error": f"course '{course_code}' not found"}), 404
    if db.get_user_by_email(email) is None:
        return jsonify({"error": f"user '{email}' not found"}), 404

    db.add_course_membership(course_code, email, membership_role)
    return jsonify({
        "status": "enrolled",
        "email": email,
        "course_code": course_code,
        "membership_role": membership_role,
    }), 201


@courses_bp.delete("/courses/<course_code>/members/<email>")
def remove_member(course_code: str, email: str):
    _, err = _require_admin()
    if err:
        return err
    db_err = _require_db()
    if db_err:
        return db_err

    from src.api import db
    if not db.remove_course_membership(course_code, email):
        return jsonify({"error": "membership not found"}), 404
    return jsonify({"status": "unenrolled", "email": email, "course_code": course_code})
