# Authors: Thanh Binh Tran
"""Administrator approval of lecturer accounts.

A lecturer who signs up for themselves has no access until an administrator
approves the account (src/api/routes/auth.py answers sign-in with 403 until
then). These routes let an administrator see who is waiting and decide.
Admin only; nothing here can touch a student or an admin account.
"""
from __future__ import annotations

import logging
import uuid

from flask import Blueprint, current_app, jsonify, request

logger = logging.getLogger(__name__)

admin_users_bp = Blueprint("admin_users", __name__, url_prefix="/api/admin")


def _state():
    return current_app.config["EDURAG_API_STATE"]


def _require_admin():
    user = _state().validate_bearer(request.headers.get("Authorization"))
    if user is None:
        return None, (jsonify({"error": "Authentication required."}), 401)
    if user.get("role") != "admin":
        return None, (jsonify({"error": "Admin role required."}), 403)
    if not _state().db_available:
        return None, (jsonify({
            "error": "Account approval requires the database backend, which is currently unavailable.",
        }), 503)
    return user, None


@admin_users_bp.get("/users/pending")
def pending_users():
    """Lecturer accounts waiting for a decision, oldest first."""
    _, err = _require_admin()
    if err:
        return err
    from src.api import db
    return jsonify({"users": db.list_users_by_approval_status("pending")})


def _decide(user_id: str, status: str):
    admin, err = _require_admin()
    if err:
        return err

    try:
        uuid.UUID(user_id)
    except (ValueError, AttributeError):
        return jsonify({"error": "user not found"}), 404

    from src.api import db
    target = db.get_user_by_id(user_id)
    if target is None:
        return jsonify({"error": "user not found"}), 404
    if target.get("role") != "lecturer":
        return jsonify({"error": "Only lecturer accounts are approved or rejected."}), 409

    # Rejecting is for an account that has not been let in. An approved
    # lecturer may already hold a live session, and rejecting the row would not
    # end it, so that is refused rather than half done.
    if status == "rejected" and target.get("approval_status", "approved") == "approved":
        return jsonify({"error": "An approved account cannot be rejected."}), 409

    updated = db.set_approval_status(user_id, status)
    if updated is None:
        return jsonify({"error": "user not found"}), 404
    # The user id and the decision only: the audit log is not written yet, so
    # this line is the whole record.
    logger.info("Lecturer account %s set to %s by %s.", user_id, status, admin.get("user_id"))
    return jsonify({"user": updated})


@admin_users_bp.post("/users/<user_id>/approve")
def approve_user(user_id: str):
    return _decide(user_id, "approved")


@admin_users_bp.post("/users/<user_id>/reject")
def reject_user(user_id: str):
    return _decide(user_id, "rejected")
