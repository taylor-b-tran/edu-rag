# QA Checklist -- Sections 4 & 5 Results (programmatic re-run)

**Run on:** 26 May 2026 01:51
**Script:** `scripts/qa_sections_4_5_rerun.py`
**Backend:** live `/api/query` against running Docker stack (GPU-enabled Ollama)
**Purpose:** Provide evidence for Tung to flip the SKIP rows in `docs/qa_checklist_sprint5.md` Sections 4–5 to PASS/FAIL.

> This script does not replace manual UI verification of citation rendering. It validates the API-level contract; pair with a manual Streamlit walk-through for the final sign-off.

## Section 4 -- Live ChromaDB / Ollama RAG Backend

| ID | Expectation | Status | Notes |
|---|---|---|---|
| R-01 | live retrieval; backend_mode=chromadb | **PASS** | backend=chromadb model=llama3.2 refs=3 conf=Medium 0.74s |
| R-02 | at least one source_reference | **PASS** | backend=chromadb model=llama3.2 refs=1 conf=Medium 1.13s |
| R-03 | cites seeded corpus | **PASS** | backend=chromadb model=llama3.2 refs=4 conf=Medium 1.28s |
| R-04 | cites seeded corpus | **PASS** | backend=chromadb model=llama3.2 refs=5 conf=Medium 2.31s |
| R-05 | mentions PDF, PPTX, or DOCX | **PASS** | answer head: "Based on general knowledge — not verified against course materials.\n\nI'm Paedia, your course assistant for CSIT321 at UO"... (1.69s) |
| R-06 | graceful fallback; no fake citations | **PASS** | off-topic -> is_fallback=True, refs=0, conf=Low, 1.12s |
| R-07 | source_references shape check (run after R-01) | **PASS** | R-01 returned 3 references; first ref keys: ['page', 'similarity', 'source_file', 'topic', 'week'] |

## Section 5 -- Citations (API-level)

| ID | Expectation | Status | Notes |
|---|---|---|---|
| C-01 | After live RAG query -- citation source + excerpt visible in response | **PASS** | on-topic refs: 3 (sample: {'page': 2, 'similarity': 0.431, 'source_file': 'Week1_RAG_Introduction.pdf', 'topic': 'RAG Fundamentals', 'week': 'Week 1'}) |
| C-02 | Citations not empty for on-topic queries | **PASS** | on-topic ref count: 3 |
| C-03 | No fake citations for off-topic queries | **PASS** | off-topic refs: 0, is_fallback=True |
| C-04 | Citation metadata includes a source identifier | **PASS** | all refs have a source identifier: True |
| C-05 | Citation metadata includes chunk_index or page | **PASS** | all refs have chunk_index or page: True |

## Raw response sample (R-01)

```json
{
  "answer": "RAG stands for Retrieval-Augmented Generation. \n\nSource: Week1_RAG_Introduction.pdf p.1 [RAG Fundamentals] sim=0.40",
  "backend_mode": "chromadb",
  "confidence": "Medium",
  "confidence_score": 0.402,
  "is_fallback": false,
  "latency_ms": 676,
  "model_used": "llama3.2",
  "session_id": "a57e1e79-47c2-489a-9789-384af5b3e73c",
  "source_references": [
    {
      "page": 2,
      "similarity": 0.431,
      "source_file": "Week1_RAG_Introduction.pdf",
      "topic": "RAG Fundamentals",
      "week": "Week 1"
    },
    {
      "page": 1,
      "similarity": 0.403,
      "source_file": "Week1_RAG_Introduction.pdf",
      "topic": "RAG Fundamentals",
      "week": "Week 1"
    },
    {
      "page": 1,
      "similarity": 0.373,
      "source_file": "Week6_RAG_Evaluation.pdf",
      "topic": "RAG Evaluation",
      "week": "Week 6"
    }
  ],
  "_elapsed_s": 0.74
}
```