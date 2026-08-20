from __future__ import annotations

import logging
import os
import threading
import uuid as _uuid
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


def _find_document(doc_id: str):
    """Locate a document by either of the two id fields it is stored under."""
    for document in _state().list_documents():
        if document.get("document_id") == doc_id or document.get("id") == doc_id:
            return document
    return None


def _document_course(document: dict) -> str:
    return document.get("course_id") or document.get("course_code") or ""


def _may_see_document(user: dict, document: dict) -> bool:
    """Whether this user is allowed to know the document exists.

    Enrollment is the test, and admins pass it for every course. Callers turn a
    False into a 404 rather than a 403: a 403 confirms the id is real, which
    lets anyone walk the id space and learn what other courses hold.
    """
    return _state().is_enrolled(user, _document_course(document))


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

        # Batch-encode all chunks in one model.encode() call instead of one
        # call per chunk — cuts embedding time for multi-chunk uploads by
        # amortising tokenisation/forward-pass overhead across the batch
        # (T09, Sprint 6).
        chunk_texts = [ch["text"] for ch in chunks]
        batch_embeddings = model.encode(chunk_texts, normalize_embeddings=True)

        ids, texts, embeddings, metadatas = [], [], [], []
        for idx, (ch, emb) in enumerate(zip(chunks, batch_embeddings)):
            chunk_text = ch["text"]
            meta = ch["metadata"]

            page_number = meta.get("page_number") or meta.get("slide_number") or 1
            topic = meta.get("topic") or "Uploaded Material"
            week = meta.get("week") or "General"

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

    # Only accept what the chunker can actually read. Anything else would be
    # written to disk and then fail in the background job with "no extractable
    # text", which tells the uploader nothing useful.
    from src.document_processor.chunker import SUPPORTED_EXTENSIONS

    original_filename = uploaded_file.filename or "uploaded_document"
    safe_name = secure_filename(original_filename) or "uploaded_document"
    extension = Path(safe_name).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        return jsonify({
            "error": "unsupported file type",
            "message": f"Only {', '.join(sorted(SUPPORTED_EXTENSIONS))} files can be indexed.",
        }), 400

    # Store under a unique name. Two lecturers uploading week1.pdf used to
    # overwrite each other on disk, and because ChromaDB chunks are keyed on
    # source_file, deleting either document removed both sets of chunks.
    stored_name = f"{Path(safe_name).stem}-{_uuid.uuid4().hex[:8]}{extension}"
    upload_dir = _upload_dir()
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / stored_name

    # save() streams from the request to disk. The previous read() pulled the
    # whole file into memory first.
    uploaded_file.save(file_path)
    file_size = file_path.stat().st_size

    import copy
    result = _state().queue_upload(
        filename=stored_name,
        file_size=file_size,
        course_id=course_id,
        original_filename=original_filename,
    )
    response_payload = copy.deepcopy(result)

    # Spawn background indexing thread
    t = threading.Thread(
        target=_bg_index_document,
        args=(file_path, course_id, result["document"]["document_id"], result["job_id"], _state())
    )
    t.start()

    logger.info("User %s uploaded %s (stored as %s) to course %s (indexing job %s started)",
                user.get("user_id"), original_filename, stored_name, course_id,
                result["job_id"])
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
    document = _find_document(doc_id)
    if document is None:
        return jsonify({"error": "document not found"}), 404
    if not _may_see_document(user, document):
        logger.warning("User %s requested document %s from unauthorised course %s",
                       user.get("user_id"), doc_id, _document_course(document))
        return jsonify({"error": "document not found"}), 404
    return jsonify(document)


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

    # Holding the lecturer role is not enough. Without this, any lecturer could
    # delete any other lecturer's material in any course - and deletion also
    # removes the document's chunks from ChromaDB, so it is not recoverable
    # from the UI.
    if target_doc is not None and not _state().is_enrolled(user, _document_course(target_doc)):
        logger.warning("User %s attempted to delete document %s in unauthorised course %s",
                       user.get("user_id"), doc_id, _document_course(target_doc))
        return jsonify({"error": "document not found"}), 404

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

    # A job carries the document it belongs to, and its `error` field can quote
    # server-side file paths, so it is gated on the same enrollment test.
    document = _find_document(job.get("document_id") or "")
    if document is not None and not _may_see_document(user, document):
        logger.warning("User %s requested indexing job %s for unauthorised course %s",
                       user.get("user_id"), job_id, _document_course(document))
        return jsonify({"error": "indexing job not found"}), 404
    return jsonify(job)
