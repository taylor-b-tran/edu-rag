from flask import Flask, request, jsonify
import json
import os
import time
from difflib import SequenceMatcher

_REAL_PIPELINE_AVAILABLE = False
try:
    from rag_module import RAGPipeline
    _REAL_PIPELINE_AVAILABLE = True
    print("[backend] Real RAGPipeline loaded — using Binh's backend")
except ImportError:
    print("[backend] rag_module.py not found — fixture mock active")
    print("[backend] Drop backend/rag_module.py to enable real pipeline")

# ── Load fixture data (always loaded as fallback) ──────────────────
_FIXTURE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "fixtures", "sample_responses.json"
)

def _load_fixtures() -> dict | None:
    if os.path.exists(_FIXTURE_PATH):
        with open(_FIXTURE_PATH) as f:
            return json.load(f)
    print("[backend] fixtures/sample_responses.json not found")
    return None

_FIXTURES = _load_fixtures()


app = Flask(__name__)


@app.after_request
def _cors(response):
    """Allow Streamlit dev server (any origin) to call this API."""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response

@app.route("/api/<path:_>", methods=["OPTIONS"])
def _preflight(_):
    return "", 204


# ── /api/health ────────────────────────────────────────────────────

@app.route("/api/health", methods=["GET"])
def health():
    """
    Returns backend status so the Streamlit UI can show the correct
    backend mode indicator in the sidebar.
    """
    return jsonify({
        "status": "ok",
        "mode": "real" if _REAL_PIPELINE_AVAILABLE else "fixture",
        "fixture_loaded": _FIXTURES is not None,
    })

@app.route("/api/query", methods=["POST"])
def query():
    """
    Main RAG query endpoint.

    Request body (JSON):
        { "query": "...", "course_id": "csit321" }

    Response (JSON) — same schema as the existing fixture data so the
    Streamlit UI needs zero changes to render it:
        {
          "answer": str,
          "source_references": [...],
          "confidence": float,
          "model_used": str,
          "token_count": int,
          "is_fallback": bool,
          "backend_mode": "real" | "fixture"
        }
    """
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


def _query_real(question: str, course_id: str) -> dict:
    """Call Binh's RAGPipeline and normalise the response to Paedia's schema."""
    try:
        pipeline = RAGPipeline(course_id=course_id)
        raw = pipeline.query(question)

        # Normalise — Binh's key names → Paedia schema
        sources = []
        for s in raw.get("sources", []):
            sources.append({
                "chunk_id":    s.get("chunk_id", ""),
                "document_id": s.get("document_id", ""),
                "filename":    s.get("filename", s.get("source", "unknown")),
                "page_number": s.get("page", s.get("page_number", 1)),
                "chunk_order": s.get("chunk_order", 0),
                "similarity":  round(float(s.get("score", s.get("similarity", 0.0))), 4),
            })

        return {
            "answer":            raw.get("answer", ""),
            "source_references": sources,
            "confidence":        round(float(raw.get("confidence", 0.0)), 3),
            "model_used":        raw.get("model", "ollama/llama3"),
            "token_count":       raw.get("token_count", 0),
            "is_fallback":       raw.get("is_fallback", False),
        }
    except Exception as exc:
        print(f"[backend] Real pipeline error: {exc} — falling back to fixture")
        result = _query_fixture(question)
        result["backend_mode"] = "fixture-fallback"
        return result


def _query_fixture(question: str) -> dict:
    """
    Match question against the fixture response bank using text similarity.
    This reproduces what Binh's backend does, but with static answers.
    """
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

        # Sequence similarity
        seq = SequenceMatcher(None, q_lower, k_lower).ratio()

        # Keyword overlap (ignore stop words)
        stop = {"what", "is", "the", "a", "an", "how", "does", "do",
                "can", "you", "me", "and", "or", "in", "of", "to",
                "for", "on", "at", "with", "are"}
        q_words = set(q_lower.split()) - stop
        k_words = set(k_lower.split()) - stop
        kw = len(q_words & k_words) / len(q_words) if q_words else 0.0

        score = 0.55 * seq + 0.45 * kw

        if score > best_score:
            best_score = score
            best_response = response

    THRESHOLD = 0.28
    if best_response and best_score >= THRESHOLD:
        return {
            **best_response,
            "confidence": round(min(best_score * 1.5, 0.97), 3),
        }

    return dict(_FIXTURES["fallback_response"])


# ── Entry point ────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"{'-' * 55}\n")
    print(f"""
 Paedia Flask Backend  ·  Task 20
 CSIT321 Project 37  ·  Group 19
 """)
    print(f"{'─' * 55}\n")
    print(f"""
 Mode    : {'REAL (Binh)' if _REAL_PIPELINE_AVAILABLE else 'Fixture mock':38s}
 Fixture : {'Loaded' if _FIXTURES else 'Missing':38s}
 URL     : http://localhost:{port:<20}
""")
    print(f"{'─' * 55}\n")
    app.run(host="0.0.0.0", port=port, debug=True, use_reloader=False)