from flask import Flask, request, jsonify
import json
import os
import time
from difflib import SequenceMatcher

_REAL_PIPELINE_AVAILABLE = False
try:
    from rag_module import RAGPipeline
    _REAL_PIPELINE_AVAILABLE = True
    print("[backend] Real RAGPipeline loaded; using backend module")
except ImportError:
    print("[backend] rag_module.py not found; fixture mode active")

# Load fixture data from canonical root fixtures folder.
_FIXTURE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "fixtures", "sample_responses.json")
)


def _load_fixtures():
    if os.path.exists(_FIXTURE_PATH):
        with open(_FIXTURE_PATH, encoding="utf-8") as f:
            return json.load(f)
    print(f"[backend] Fixture file not found: {_FIXTURE_PATH}")
    return None


_FIXTURES = _load_fixtures()

app = Flask(__name__)


@app.after_request
def _cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


@app.route("/api/<path:_>", methods=["OPTIONS"])
def _preflight(_):
    return "", 204


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify(
        {
            "status": "ok",
            "mode": "real" if _REAL_PIPELINE_AVAILABLE else "fixture",
            "fixture_loaded": _FIXTURES is not None,
        }
    )


@app.route("/api/query", methods=["POST"])
def query():
    body = request.get_json(force=True, silent=True) or {}
    q = (body.get("query") or "").strip()
    course_id = body.get("course_id", "csit321")

    if not q:
        return jsonify({"error": "query is required"}), 400

    t0 = time.time()
    if _REAL_PIPELINE_AVAILABLE:
        result = _query_real(q, course_id)
        result["backend_mode"] = "real"
    else:
        result = _query_fixture(q)
        result["backend_mode"] = "fixture"
    result["latency_ms"] = round((time.time() - t0) * 1000)
    return jsonify(result)


def _query_real(question: str, course_id: str):
    try:
        pipeline = RAGPipeline(course_id=course_id)
        raw = pipeline.query(question)
        sources = []
        for s in raw.get("sources", []):
            sources.append(
                {
                    "chunk_id": s.get("chunk_id", ""),
                    "document_id": s.get("document_id", ""),
                    "filename": s.get("filename", s.get("source", "unknown")),
                    "page_number": s.get("page", s.get("page_number", 1)),
                    "chunk_order": s.get("chunk_order", 0),
                    "similarity": round(float(s.get("score", s.get("similarity", 0.0))), 4),
                }
            )

        return {
            "answer": raw.get("answer", ""),
            "source_references": sources,
            "confidence": round(float(raw.get("confidence", 0.0)), 3),
            "model_used": raw.get("model", "ollama/llama3"),
            "token_count": raw.get("token_count", 0),
            "is_fallback": raw.get("is_fallback", False),
        }
    except Exception as exc:
        print(f"[backend] Real pipeline error: {exc}; falling back to fixture")
        result = _query_fixture(question)
        result["backend_mode"] = "fixture-fallback"
        return result


def _query_fixture(question: str):
    if not _FIXTURES:
        return {
            "answer": "Backend running but fixture data is missing.",
            "source_references": [],
            "confidence": 0.0,
            "model_used": "fixture",
            "token_count": 0,
            "is_fallback": True,
        }

    best_score = 0.0
    best_response = None

    q_lower = question.lower().strip("?").strip()
    for key, response in _FIXTURES["responses"].items():
        k_lower = key.lower().strip("?").strip()
        seq = SequenceMatcher(None, q_lower, k_lower).ratio()
        stop = {
            "what",
            "is",
            "the",
            "a",
            "an",
            "how",
            "does",
            "do",
            "can",
            "you",
            "me",
            "and",
            "or",
            "in",
            "of",
            "to",
            "for",
            "on",
            "at",
            "with",
            "are",
        }
        q_words = set(q_lower.split()) - stop
        k_words = set(k_lower.split()) - stop
        kw = len(q_words & k_words) / len(q_words) if q_words else 0.0
        score = 0.55 * seq + 0.45 * kw
        if score > best_score:
            best_score = score
            best_response = response

    threshold = 0.28
    if best_response and best_score >= threshold:
        return {**best_response, "confidence": round(min(best_score * 1.5, 0.97), 3)}
    return dict(_FIXTURES["fallback_response"])


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True, use_reloader=False)
