from __future__ import annotations

import logging
import os
import threading
from pathlib import Path
from flask import Blueprint, current_app, jsonify, request
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

documents_bp = Blueprint("documents", __name__, url_prefix="/api")

_LECTURER_ROLES = {"lecturer", "admin"}

# Repo root: src/api/routes/documents.py -> parents[3] = repo root.
_REPO_ROOT = Path(__file__).resolve().parents[3]


def _upload_dir() -> Path:
    """Return the upload directory.

    Order of precedence:
    1. EDURAG_UPLOAD_DIR env var (set explicitly by ops/tests).
    2. /workspace/data/uploads when /workspace exists and is writable (Docker).
    3. <repo_root>/data/uploads (host runs, CI without a /workspace mount).
    """
    env_override = os.environ.get("EDURAG_UPLOAD_DIR")
    if env_override:
        return Path(env_override)
    workspace = Path("/workspace")
    if workspace.is_dir() and os.access(workspace, os.W_OK):
        return workspace / "data" / "uploads"
    return _REPO_ROOT / "data" / "uploads"


def _state():
    return current_app.config["EDURAG_API_STATE"]


def _require_auth():
    user = _state().validate_bearer(request.headers.get("Authorization"))
    if user is None:
        return None, (jsonify({"error": "Authentication required."}), 401)
    return user, None


def _bg_index_document(file_path: Path, course_id: str, document_id: str, job_id: str, state):
    try:
        state.update_job(job_id, status="processing", progress_percent=10)
        state.update_document_status(document_id, "processing")

        from src.document_processor.chunker import extract_and_chunk
        from src.document_processor.ingest_corpus import get_chroma_client, get_or_create_collection, _load_embedder
        import uuid

        state.update_job(job_id, progress_percent=30)

        chunks = extract_and_chunk(file_path)
        if not chunks:
            raise Exception("No extractable text found in file")

        state.update_job(job_id, progress_percent=50)

        client = get_chroma_client()
        collection = get_or_create_collection(client)

        model, model_name, dim = _load_embedder()

        state.update_job(job_id, progress_percent=70)

        ids, texts, embeddings, metadatas = [], [], [], []
        for idx, ch in enumerate(chunks):
            chunk_text = ch["text"]
            meta = ch["metadata"]

            page_number = meta.get("page_number") or meta.get("slide_number") or 1
            topic = meta.get("topic") or "Uploaded Material"
            week = meta.get("week") or "General"

            emb = model.encode(chunk_text, normalize_embeddings=True)
            if hasattr(emb, "tolist"):
                emb = emb.tolist()

            doc_id = f"uploaded-{file_path.name}-{idx}-{uuid.uuid4().hex[:6]}"
            ids.append(doc_id)
            texts.append(chunk_text)
            embeddings.append(emb)
            metadatas.append({
                "course_id": course_id,
                "source_file": file_path.name,
                "page_number": page_number,
                "topic": topic,
                "week": week
            })

        state.update_job(job_id, progress_percent=90)

        if ids:
            collection.upsert(
                ids=ids, documents=texts,
                embeddings=embeddings, metadatas=metadatas
            )

        state.update_job(job_id, status="completed", progress_percent=100)
        state.update_document_status(document_id, "indexed", chunks=len(ids))

    except Exception as e:
        logger.exception("Error in background indexing: %s", e)
        state.update_job(job_id, status="failed", error=str(e))
        state.update_document_status(document_id, "failed")


@documents_bp.post("/upload")
def upload_document():
    user, err = _require_auth()
    if err:
        return err
    if user.get("role") not in _LECTURER_ROLES:
        return jsonify({"error": "Lecturer or admin role required."}), 403

    uploaded_file = request.files.get("file")
    raw_course_id = request.form.get("course_id") or request.args.get("course_id") or "CSIT321"
    _uuid_form, code_form = _state().resolve_course(raw_course_id)
    course_id = code_form or raw_course_id
    if uploaded_file is None:
        return jsonify({"error": "file is required"}), 400

    if not _state().is_enrolled(user, course_id):
        logger.warning("User %s attempted upload to unauthorised course %s",
                       user.get("user_id"), course_id)
        return jsonify({"error": "Not allowed to upload to this course."}), 403

    # Ensure secure filename and write content
    filename = secure_filename(uploaded_file.filename or "uploaded_document")
    upload_dir = _upload_dir()
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / filename

    data = uploaded_file.read()
    with open(file_path, "wb") as f:
        f.write(data)

    import copy
    result = _state().queue_upload(
        filename=filename,
        file_size=len(data),
        course_id=course_id,
    )
    response_payload = copy.deepcopy(result)

    # Spawn background indexing thread
    t = threading.Thread(
        target=_bg_index_document,
        args=(file_path, course_id, result["document"]["document_id"], result["job_id"], _state())
    )
    t.start()

    logger.info("User %s uploaded %s to course %s (indexing job %s started)",
                user.get("user_id"), filename, course_id, result["job_id"])
    return jsonify(response_payload), 202


@documents_bp.get("/documents")
def list_documents():
    user, err = _require_auth()
    if err:
        return err
    course_id = request.args.get("course_id")
    if course_id and not _state().is_enrolled(user, course_id):
        logger.warning("User %s requested documents for unauthorised course %s",
                       user.get("user_id"), course_id)
        return jsonify({"documents": [], "error": "Not enrolled in this course."}), 403
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

    target_doc = None
    for doc in _state().uploaded_documents:
        if doc.get("document_id") == doc_id or doc.get("id") == doc_id:
            target_doc = doc
            break

    if target_doc:
        filename = target_doc.get("filename")
        if filename:
            try:
                from src.document_processor.ingest_corpus import get_chroma_client, get_or_create_collection
                client = get_chroma_client()
                collection = get_or_create_collection(client)
                collection.delete(where={"source_file": {"$eq": filename}})
                logger.info("Deleted ChromaDB chunks for document: %s", filename)

                # Delete the file from host uploads directory too
                file_path = _upload_dir() / filename
                if file_path.exists():
                    os.remove(file_path)
            except Exception as e:
                logger.warning("Failed to delete chunks or file for %s: %s", filename, e)

    if not _state().delete_uploaded_document(doc_id):
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
