from __future__ import annotations

import logging

from flask import Blueprint, current_app, jsonify, request

logger = logging.getLogger(__name__)

documents_bp = Blueprint("documents", __name__, url_prefix="/api")

_LECTURER_ROLES = {"lecturer", "admin"}


def _state():
    return current_app.config["EDURAG_API_STATE"]


def _require_auth():
    user = _state().validate_bearer(request.headers.get("Authorization"))
    if user is None:
        return None, (jsonify({"error": "Authentication required."}), 401)
    return user, None


@documents_bp.post("/upload")
def upload_document():
    user, err = _require_auth()
    if err:
        return err
    if user.get("role") not in _LECTURER_ROLES:
        return jsonify({"error": "Lecturer or admin role required."}), 403

    uploaded_file = request.files.get("file")
    course_id = request.form.get("course_id") or request.args.get("course_id") or "CSIT321"
    if uploaded_file is None:
        return jsonify({"error": "file is required"}), 400

    data = uploaded_file.read()
    result = _state().queue_upload(
        filename=uploaded_file.filename or "uploaded_document",
        file_size=len(data),
        course_id=course_id,
    )
    logger.info("User %s uploaded %s to course %s", user.get("user_id"), uploaded_file.filename, course_id)
    return jsonify(result), 202


@documents_bp.get("/documents")
def list_documents():
    user, err = _require_auth()
    if err:
        return err
    course_id = request.args.get("course_id")
    return jsonify({"documents": _state().list_documents(course_id)})


@documents_bp.get("/document/<doc_id>")
def get_document(doc_id: str):
    user, err = _require_auth()
    if err:
        return err
    for document in _state().list_documents():
        if document.get("document_id") == doc_id or document.get("id") == doc_id:
            return jsonify(document)
    return jsonify({"error": "document not found"}), 404


@documents_bp.delete("/document/<doc_id>")
def delete_document(doc_id: str):
    user, err = _require_auth()
    if err:
        return err
    if user.get("role") not in _LECTURER_ROLES:
        return jsonify({"error": "Lecturer or admin role required."}), 403

    before = len(_state().uploaded_documents)
    _state().uploaded_documents = [
        doc for doc in _state().uploaded_documents
        if doc.get("document_id") != doc_id and doc.get("id") != doc_id
    ]
    if len(_state().uploaded_documents) == before:
        return jsonify({"error": "document not found or fixture document is read-only"}), 404
    return jsonify({"status": "success", "message": "Document deleted."})


@documents_bp.get("/indexing-jobs/<job_id>")
def get_indexing_job(job_id: str):
    user, err = _require_auth()
    if err:
        return err
    job = _state().indexing_jobs.get(job_id)
    if not job:
        return jsonify({"error": "indexing job not found"}), 404
    return jsonify(job)
