# Authors: Thanh Binh Tran
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


def _require_course_manager(course_code: str):
    """Authorize a write against one course (T8-04).

    An admin manages every course. A lecturer manages only the courses they
    own. Courses created before ownership existed have no owner and stay
    admin-only, which is the safe reading of a null.

    Returns (user, course, None) or (None, None, error_response). The failure
    is a 403 rather than a 404: every authenticated user can already list
    course codes via GET /api/courses, so hiding existence here would buy
    nothing and only make a real permission problem look like a typo.
    """
    user, err = _require_auth()
    if err:
        return None, None, err
    if user.get("role") not in {"admin", "lecturer"}:
        # Settled before the database is consulted: a student is refused
        # whether or not Postgres happens to be reachable.
        return None, None, (jsonify({
            "error": "You can only manage courses you own.",
        }), 403)
    db_err = _require_db()
    if db_err:
        return None, None, db_err

    from src.api import db
    course = db.get_course_by_code(course_code)
    if course is None:
        return None, None, (jsonify({"error": f"course '{course_code}' not found"}), 404)

    if user.get("role") == "admin":
        return user, course, None

    owner_id = course.get("owner_id")
    if user.get("role") == "lecturer" and owner_id and owner_id == user.get("user_id"):
        return user, course, None

    return None, None, (jsonify({
        "error": "You can only manage courses you own.",
    }), 403)


@courses_bp.get("/courses")
def list_courses():
    """Every course, each tagged with whether this caller may manage it.

    `can_manage` mirrors _require_course_manager exactly: an admin manages all,
    a lecturer manages only what they own, a student manages none. Without it
    the live-config UI (T8-09) has no way to tell which courses a lecturer may
    tune, so it would offer controls on every course and only discover the
    answer when saving failed with a 403 — a screen that lies until you use it.

    The owner id itself is deliberately not exposed: the UI needs the decision,
    not the identity behind it.
    """
    user, err = _require_auth()
    if err:
        return err

    role = user.get("role")
    owned: set[str] = set()
    if role == "lecturer" and _state().db_available:
        try:
            from src.api import db
            owned = {
                c.get("course_code")
                for c in db.list_courses_owned_by(user.get("user_id"))
            }
        except Exception:
            current_app.logger.warning(
                "Could not resolve course ownership; treating none as managed.",
                exc_info=True,
            )

    courses = []
    for course in _state().list_courses():
        code = course.get("course_code")
        courses.append({
            **course,
            "can_manage": role == "admin" or (role == "lecturer" and code in owned),
            # The check the query, document and settings routes make, so a Join
            # or Joined label cannot disagree with what the next question gets
            # (T8-05). Unlike looking for the code in the token's list, it also
            # matches the fixture course ids a login without Postgres carries,
            # and it is true for an admin, who may ask about any course.
            "is_enrolled": _state().is_enrolled(user, code),
        })
    return jsonify({"courses": courses})


# Students join and leave courses themselves (T8-05). Until now the only way
# into a course was POST /courses/<code>/members, which only the course's manager
# may call - and still only they may - so a student who had just signed up could
# see every course and ask about none of them. Any active course is open to any
# student, so there is nothing to approve.
#
# The routes are named like /auth/login and /auth/logout because each is
# something the caller does to their own account. Both are safe to repeat, so a
# double click or a retry after a timeout ends in the same place.

def _require_student():
    user, err = _require_auth()
    if err:
        return None, err
    if user.get("role") != "student":
        return None, (jsonify({
            "error": "Only students join or leave courses themselves. Lecturers and "
                     "admins are added to a course by the person who manages it.",
        }), 403)
    return user, None


def _answer_once_the_token_shows_it(code: str, *, enrolled: bool, status: str,
                                    http_status: int):
    """Report the change only when the caller's own credentials carry it.

    Every worker authorises a request from the stored token, not from the
    membership table. refresh_enrolled_courses logs and carries on when it
    cannot rewrite that token, which is right for a lecturer creating a course,
    but here it would tell a student they had joined and then refuse their first
    question. Reading the token back is what their next request will do.
    """
    seen = _state().validate_bearer(request.headers.get("Authorization"))
    held = list((seen or {}).get("enrolled_courses") or [])
    if seen is None or (code in held) != enrolled:
        return jsonify({
            "error": "Your courses could not be updated just now. Please try again.",
        }), 503
    return jsonify({"status": status, "course_code": code, "enrolled_courses": held}), http_status


@courses_bp.post("/courses/<course_code>/join")
def join_course(course_code: str):
    """A student joins an active course."""
    user, err = _require_student()
    if err:
        return err
    db_err = _require_db()
    if db_err:
        return db_err

    from src.api import db
    course = db.get_course_by_code(course_code)
    if course is None:
        return jsonify({"error": f"course '{course_code}' not found"}), 404
    if not course.get("is_active", True):
        return jsonify({"error": f"course '{course_code}' is not open to join right now"}), 409

    code = course["course_code"]
    already = code in db.get_enrolled_course_codes(user["user_id"])
    if not already:
        db.add_course_membership(code, user["email"], "student")
    _state().refresh_enrolled_courses(user["user_id"])
    return _answer_once_the_token_shows_it(
        code, enrolled=True,
        status="already_enrolled" if already else "enrolled",
        http_status=200 if already else 201,
    )


@courses_bp.post("/courses/<course_code>/leave")
def leave_course(course_code: str):
    """A student leaves a course, including one that has since closed."""
    user, err = _require_student()
    if err:
        return err
    db_err = _require_db()
    if db_err:
        return db_err

    from src.api import db
    course = db.get_course_by_code(course_code)
    if course is None:
        return jsonify({"error": f"course '{course_code}' not found"}), 404

    code = course["course_code"]
    removed = db.remove_course_membership(code, user["email"])
    _state().refresh_enrolled_courses(user["user_id"])
    return _answer_once_the_token_shows_it(
        code, enrolled=False,
        status="unenrolled" if removed else "not_enrolled",
        http_status=200,
    )


@courses_bp.post("/courses")
def create_course():
    """Create a course. Admins and lecturers both may; students may not (T8-04).

    A lecturer always owns what they create - the owner is taken from the
    token, never from the body, so nobody can hand a course to someone else on
    the way in. An admin may name an owner, or leave it unset for a course only
    admins manage.
    """
    user, err = _require_auth()
    if err:
        return err
    if user.get("role") not in {"admin", "lecturer"}:
        return jsonify({"error": "Only lecturers and admins can create courses."}), 403

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
    if user.get("role") == "lecturer":
        owner_id = user.get("user_id")
    else:
        owner_id = (body.get("owner_id") or "").strip() or None
        if owner_id and db.get_user_by_id(owner_id) is None:
            return jsonify({"error": f"owner_id '{owner_id}' is not a known user"}), 400

    course = db.create_course(course_code, course_name, description, owner_id=owner_id)
    if course is None:
        return jsonify({"error": f"course_code '{course_code}' already exists"}), 409

    # Enroll the owner as a lecturer member, otherwise they own a course whose
    # documents they cannot read - is_enrolled checks membership, not ownership.
    if owner_id:
        owner = db.get_user_by_id(owner_id)
        if owner is not None:
            db.add_course_membership(course_code, owner["email"], "lecturer")
            _state().refresh_enrolled_courses(owner_id)

    return jsonify({"course": course}), 201


@courses_bp.patch("/courses/<course_code>")
def update_course(course_code: str):
    _, _, err = _require_course_manager(course_code)
    if err:
        return err

    body = request.get_json(silent=True) or {}
    from src.api import db
    # owner_id is deliberately not settable here - transferring a course is
    # POST /courses/<code>/owner, which is admin-only.
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
    _, _, err = _require_course_manager(course_code)
    if err:
        return err

    from src.api import db
    course = db.update_course(course_code, is_active=False)
    if course is None:
        return jsonify({"error": f"course '{course_code}' not found"}), 404
    return jsonify({"status": "deactivated", "course": course})


@courses_bp.get("/courses/<course_code>/members")
def list_members(course_code: str):
    _, _, err = _require_course_manager(course_code)
    if err:
        return err

    from src.api import db
    return jsonify({"members": db.list_course_members(course_code)})


@courses_bp.post("/courses/<course_code>/members")
def add_member(course_code: str):
    _, err = _require_auth()
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

    # A malformed body is a 400 before ownership is consulted, so the answer
    # does not depend on the database being reachable.
    _, _, err = _require_course_manager(course_code)
    if err:
        return err

    from src.api import db
    member = db.get_user_by_email(email)
    if member is None:
        return jsonify({"error": f"user '{email}' not found"}), 404

    db.add_course_membership(course_code, email, membership_role)
    # The new member may be logged in right now; their token still carries the
    # enrollment list from login.
    _state().refresh_enrolled_courses(member["user_id"])
    return jsonify({
        "status": "enrolled",
        "email": email,
        "course_code": course_code,
        "membership_role": membership_role,
    }), 201


@courses_bp.delete("/courses/<course_code>/members/<email>")
def remove_member(course_code: str, email: str):
    _, course, err = _require_course_manager(course_code)
    if err:
        return err

    from src.api import db
    member = db.get_user_by_email(email)
    # Removing the owner would leave a course only an admin could manage, which
    # is how you lock yourself out of your own course in one click.
    if member is not None and course.get("owner_id") == member["user_id"]:
        return jsonify({
            "error": "The course owner cannot be removed. Transfer the course first.",
        }), 409

    if not db.remove_course_membership(course_code, email):
        return jsonify({"error": "membership not found"}), 404
    if member is not None:
        _state().refresh_enrolled_courses(member["user_id"])
    return jsonify({"status": "unenrolled", "email": email, "course_code": course_code})


@courses_bp.post("/courses/<course_code>/owner")
def transfer_course(course_code: str):
    """Hand a course to another lecturer. Admin only — a lecturer giving their
    own course away is the same action as taking it, and only an admin should
    be able to decide who ends up responsible for it."""
    _, err = _require_admin()
    if err:
        return err
    db_err = _require_db()
    if db_err:
        return db_err

    body = request.get_json(silent=True) or {}
    owner_id = body.get("owner_id")
    owner_email = (body.get("owner_email") or "").strip()

    from src.api import db
    if db.get_course_by_code(course_code) is None:
        return jsonify({"error": f"course '{course_code}' not found"}), 404

    owner = None
    if owner_email:
        owner = db.get_user_by_email(owner_email)
    elif owner_id:
        owner = db.get_user_by_id(str(owner_id).strip())
    elif owner_id is None and not owner_email:
        # Explicit null clears the owner and returns the course to admin-only.
        course = db.set_course_owner(course_code, None)
        return jsonify({"course": course})

    if owner is None:
        return jsonify({"error": "owner not found"}), 404
    if owner["role"] not in {"lecturer", "admin"}:
        return jsonify({"error": "A course owner must be a lecturer or an admin."}), 400

    course = db.set_course_owner(course_code, owner["user_id"])
    db.add_course_membership(course_code, owner["email"], "lecturer")
    _state().refresh_enrolled_courses(owner["user_id"])
    return jsonify({"course": course})
