# Sprint 5 RAG Benchmark — Seeded / Live Retrieval

**Task:** S5-T07  
**Owner:** Tung Phuong Anh Huynh  
**Date:** 24 May 2026  
**Sprint:** 5 (14 May – 28 May 2026)  
**Status:** Retrieval-only benchmark completed (Ollama generation pending S5-T18 merge)

> **Purpose:** Provide updated, Sprint 5–specific evidence that separates live ChromaDB
> retrieval quality from the Sprint 4 fixture-backed benchmark. This document replaces
> `docs/rag_config_benchmark_31q.json` as the primary Sprint 5 retrieval evidence.

---

## 1. Scope and Separation from Sprint 4

| Dimension | Sprint 4 Benchmark | Sprint 5 Benchmark (this doc) |
|---|---|---|
| Backend | Flask test client → fixture JSON | Live ChromaDB + seeded corpus (S5-T17) |
| Generation | None (fixture answers) | Ollama `qwen3:14b` (pending S5-T18) |
| Corpus | `fixtures/sample_responses.json` (31 queries) | `src/document_processor/seed_documents.py` |
| Retrieval model | `all-MiniLM-L6-v2` (offline hash fallback in CI) | `all-MiniLM-L6-v2` (live in Docker) |
| Environment | CI / no Docker | Full Docker stack (`docker compose up`) |
| Evidence file | `docs/rag_config_benchmark_31q.json` | This file + `test/validation_report.json` |

**Key principle:** Sprint 5 benchmark must run against the _seeded corpus ingested into ChromaDB_, not against fixture JSON answers. The Sprint 4 benchmark measured API fixture matching, not vector retrieval quality.

---

## 2. Pre-conditions (Checklist Before Running)

| # | Requirement | How to verify |
|---|-------------|---------------|
| B1 | Docker Desktop running | `docker compose ps` — all 5 services up |
| B2 | Seed corpus ingested (S5-T17) | `docker compose exec api python -c "from src.document_processor.ingest_corpus import get_chroma_client, get_or_create_collection; c=get_chroma_client(); col=get_or_create_collection(c); print(col.count())"` — should print ≥ 5 |
| B3 | Ollama model pulled | `docker compose exec ollama ollama list` — shows `qwen3:14b` |
| B4 | `.env` configured | `CHROMA_HOST=chromadb`, `OLLAMA_HOST=http://ollama:11434`, `DEFAULT_OLLAMA_MODEL=qwen3:14b` |

---

## 3. Benchmark Query Set

Five queries covering the full difficulty range. These are the same queries used by `test/validate_retrieval.py`.

| ID | Category | Question | Expected fallback? |
|----|----------|----------|--------------------|
| Q01 | Easy Factual | "What is Retrieval-Augmented Generation (RAG)?" | No |
| Q02 | Easy Factual | "What embedding model does EduRAG use and what is its dimension?" | No |
| Q03 | Hard Reasoning | "Why was ChromaDB chosen over FAISS for EduRAG, and how does course_id metadata filtering prevent cross-course retrieval leakage?" | No |
| Q04 | Applied / Procedural | "How does EduRAG handle a student question when no retrieved chunk exceeds the similarity threshold?" | No |
| Q05 | Off-topic / Fallback | "What is the best recipe for chocolate cake and how long should I bake it?" | **Yes** |

---

## 4. Configuration Under Review

| Parameter | Value | Notes |
|-----------|-------|-------|
| `chunk_size` | 1024 chars | Carried from Sprint 3 baseline |
| `chunk_overlap` | 0 | Carried from Sprint 3 baseline |
| `retrieval_top_k` | 5 | Top 5 chunks retrieved per query |
| `similarity_threshold` | 0.35 (cosine sim) / 0.65 (distance) | Chunks below threshold → fallback |
| `embedding_model` | `all-MiniLM-L6-v2` (dim=384) | Via `sentence-transformers` |
| `vector_store` | ChromaDB (cosine space) | `hnsw:space = cosine` |
| `course_filter` | `course_id = "CSIT321"` | Metadata filter prevents cross-course leakage |
| `generation_model` | `qwen3:14b` via Ollama | Pending S5-T18 |
| `ollama_temperature` | 0.1 | Low temperature for factual answers |
| `ollama_num_predict` | 512 tokens | Max response length |

---

## 5. How to Run the Benchmark (Step-by-Step)

### Step 1 — Start the full Docker stack

Open a terminal in VS Code (`Ctrl + `` ` ``). Make sure you are in the repo root:

```bash
cd path/to/edu-rag
docker compose up --build
```

Wait until you see all 5 services healthy. You can verify with:

```bash
docker compose ps
```

All 5 services (`postgres`, `chromadb`, `ollama`, `api`, `streamlit`) should show **running**.

---

### Step 2 — Ingest the seed corpus (S5-T17)

Run the ingest script inside the `api` container:

```bash
docker compose exec api python -m src.document_processor.ingest_corpus
```

Expected output (abbreviated):
```
--------------------------------------------------------------
  EduRAG – Seeded Corpus Ingestion  (S5-T17)
--------------------------------------------------------------
  ChromaDB target : chromadb:8000
  Collection      : csit321_course
  Seed documents  : <N>
  ...
  [OK] Upserted <N> chunks
  [OK] Collection total: <N> chunks
  [TEST] Smoke-test: 'What is RAG?' ...
  [TEST] PASSED
--------------------------------------------------------------
  Status: OK
--------------------------------------------------------------
```

If the corpus is already ingested, add `--force` to re-ingest cleanly:

```bash
docker compose exec api python -m src.document_processor.ingest_corpus --force
```

---

### Step 3 — Pull the Ollama model (if not already done)

```bash
docker compose exec ollama ollama pull qwen3:14b
```

This may take several minutes on first run. Verify with:

```bash
docker compose exec ollama ollama list
```

---

### Step 4 — Run the retrieval validation benchmark

From the **repo root** (not inside Docker — this runs locally against the running Docker API):

```bash
# Retrieval + Ollama generation (full benchmark)
python -m pytest test/validate_retrieval.py -v -s
```

Or run the script directly:

```bash
python test/validate_retrieval.py
```

For **retrieval-only** (no Ollama — faster, useful when Ollama model is slow):

```bash
python test/validate_retrieval.py --no-ollama
```

The benchmark outputs a detailed report to the terminal **and** writes `test/validation_report.json`.

---

### Step 5 — Run the full CI test suite (local verification)

```bash
python -m pytest -v --tb=short 2>&1 | tee docs/ci_pytest_raw_sprint5.txt
```

Expected result: **108 passed, 0 failed**

---

### Step 6 — Capture the pytest output for the CI doc

```bash
python -m pytest -v --tb=short 2>&1 | tee docs/ci_pytest_raw_sprint5.txt
```

Then open `docs/ci_pytest_raw_sprint5.txt` and paste the content into **Section 9** of `docs/ci_test_validation_sprint5.md`.

---

### Step 7 — Save the benchmark JSON result

After running Step 4, copy the result to the docs folder:

```bash
cp test/validation_report.json docs/rag_benchmark_sprint5_results.json
```

---

## 6. Scoring Policy

| Metric | Pass threshold | Description |
|--------|---------------|-------------|
| Fallback correctness | 100% | Q05 must be fallback; Q01–Q04 must NOT be fallback |
| Keyword coverage | ≥ 50% | At least half of expected keywords present in answer |
| Source hit | PASS if expected source present in top chunks | Checks seeded corpus was ingested correctly |
| Confidence | High (≥0.60) or Medium (0.35–0.59) for factual Qs | Low = weak retrieval signal |
| Overall pass per query | `fallback_pass AND (keyword_pass OR expect_fallback)` | Both conditions must hold |

**Sprint 5 target: ≥ 4 / 5 queries passing** (Q05 is fallback-pass by design, so real target is 3/4 factual queries).

---

## 7. Results — Live Run 24 May 2026

**Run by:** Tai Huynh (host machine)
**Stack:** Docker Compose (postgres + chromadb 1.5.8 + ollama + api + streamlit)
**LLM:** `llama3.2` (CPU inference)
**Embedder:** `all-MiniLM-L6-v2` (384-dim, SentenceTransformers)
**Chunks indexed:** 18 (seeded from `src/document_processor/seed_documents.py`, Weeks 1–7)
**Settings:** `num_predict=256`, `timeout=300s`, `temperature=0.1`, `top_k=5`, `SIMILARITY_THRESHOLD=0.35`
**Raw JSON:** [`docs/rag_benchmark_sprint5_results.json`](rag_benchmark_sprint5_results.json)

### Summary

| Metric | Value |
|---|---|
| Queries | 5 |
| Fallback expectations met | 5 / 5 (100%) |
| Generation completed | 3 / 5 (Q02, Q04 grounded; Q05 fallback-only) |
| Generation timeouts | 2 / 5 (Q01, Q03 at 300s on CPU) |
| Top-hit source accuracy | 4 / 4 on-topic queries hit expected document |
| Off-topic fallback | 1 / 1 correct (Q05 returned 0 sources, `is_fallback=true`) |

### Per-query results

| ID | Category | Top similarity | Source hit | Fallback pass | Confidence | Generation | Latency |
|----|----------|---------------|------------|---------------|------------|------------|---------|
| Q01 | Easy Factual | 0.681 (Week1_RAG_Introduction.pdf p.1) | ✅ | ✅ | Medium (0.521) | ❌ timeout | 300.9 s |
| Q02 | Easy Factual | 0.469 (Week2_Vector_Embeddings.pdf p.1) | ✅ | ✅ | Medium (0.397) | ✅ grounded answer with citation | 96.3 s |
| Q03 | Hard Reasoning | 0.732 (Week3_ChromaDB_VectorStore.pdf p.1) | ✅ | ✅ | Medium (0.554) | ❌ timeout | 300.8 s |
| Q04 | Applied / Procedural | 0.667 (Week6_RAG_Evaluation.pdf p.2) | ✅ | ✅ | High (0.614) | ✅ grounded answer with citation | 144.9 s |
| Q05 | Off-topic | 0 sources | n/a | ✅ | Low (0.0) | LLM timeout but `FALLBACK_LABEL` prepended correctly | 300.9 s |

### Verdict

- **Retrieval quality:** ✅ 5/5 expected source hits, off-topic cleanly falls below threshold.
- **Generation quality (when it completes):** ✅ Q02 and Q04 produced concise, grounded answers with file + page citations.
- **Generation throughput:** ⚠ CPU-bound; hard-reasoning prompts (Q01, Q03) exceeded the 300 s budget. Recommend GPU host or `num_predict=128` for live demo recording.

### Example grounded answers

> **Q02:** _According to the course material, EduRAG uses the all-MiniLM-L6-v2 embedding model, which produces 384-dimensional vectors. (Week1_RAG_Introduction.pdf p.3)_

> **Q04:** _According to Context 1 | Week6_RAG_Evaluation.pdf p.2, when no retrieved chunk exceeds the cosine similarity threshold (SIMILARITY_THRESHOLD), the system must not silently use general model knowledge as if it were course material. Instead, the response is labelled..._

---

## 8. Comparison to Sprint 4 Baseline

| Metric | Sprint 4 (fixture mode) | Sprint 5 (live ChromaDB) |
|--------|------------------------|--------------------------|
| Retrieval source | Fixture JSON string match | ChromaDB cosine similarity |
| Questions answered | 31 (fixture queries) | 5 (validation set) |
| Avg confidence score | 0.5 (fixed) | TBD — fill after run |
| Fallback rate | 0% (all fixtures matched) | TBD |
| Generation | None | Ollama `qwen3:14b` (pending) |
| Evidence quality | Low — no real retrieval | High — real vector search |

---

## 9. Known Gaps and Next Steps

| Gap | Owner | ETA |
|-----|-------|-----|
| Ollama generation results (S5-T18 merge required) | Ngoc | Before 28 May |
| Live benchmark results (Steps 4–6 above) | Tung | After Ollama ready |
| Paste actual `validation_report.json` into §7 | Tung | After run |
| Compare Sprint 5 vs Sprint 4 confidence scores | Tung | After run |

---

## 10. Update Log

| Date | Author | Change |
|------|--------|--------|
| 24 May 2026 | Tung Phuong Anh Huynh | Initial document created; query set, config, and step-by-step guide complete; results section to be filled after S5-T18 merge |

---

*Owner: Tung Phuong Anh Huynh — CSIT321 Project 37, Group 19*