# Flask API Query Sequence — Sprint 5 (supersedes seq_api_query.md)

Project: EduRAG / Paedia
Verified against code: 26 Jul 2026 (Sprint 6 T05 — architecture drift review)
Diagram artifact: `docs/architecture/diagrams/seq_api_query_sprint5.svg`

## Why this replaces `seq_api_query.md`

The Sprint 4 version of this document explicitly stated: *"This sequence diagram documents the implemented Sprint 4 Flask query route, not the future live ChromaDB/Ollama retrieval path... it still uses fixture-backed matching through `APIState.query_fixture()`"* and flagged an open *"Sprint 5 Gap."* That gap was closed in Sprint 5 (S5-T17/T18) but the diagram was never updated — it was still describing the old fixture-only flow. This file and the accompanying SVG describe the actual current flow, verified directly against `src/api/routes/query.py` and `src/document_processor/rag_pipeline.py`.

## Current Flow (`POST /api/query`)

1. Streamlit sends `POST /api/query` with `query`, `course_id`, optional `session_id`, and a Bearer token.
2. Flask applies a per-IP rate limit (10 requests / 60s) — `429` if exceeded.
3. Flask validates the bearer token via `APIState.validate_bearer()` — still resolves against `fixtures/sample_responses.json::demo_users`, not a real `users` table — `401` if invalid.
4. **New in Sprint 5:** `_is_ambiguous(question)` rejects vague/short questions (fewer than 3 words, or matches a vague-pattern list) with `422 ambiguous_query` before any retrieval call. Not present in the A2/Sprint 4 design.
5. Flask checks `is_enrolled(user, course_id)` — `403` if not enrolled.
6. Flask calls `state.get_generator().generate(question, course_id=course_id)`.
7. `VectorRetriever.search()` embeds the query (`all-MiniLM-L6-v2`) and runs a cosine-similarity search against ChromaDB, filtered by `course_id` metadata, `top_k=5`.
8. Chunks with cosine similarity below 0.35 (distance above 0.65) are dropped.
9. If any chunks remain, a grounded prompt is built and sent to Ollama (`qwen3:14b`); the model is kept warm by the Sprint 5 rev-3 startup warm-up (`src/api/warmup.py`) to avoid the ~45s cold-start penalty.
10. If no chunk passed the threshold, the response is prefixed with `FALLBACK_LABEL` ("Based on general knowledge — not verified against course materials.") instead of failing or guessing silently.
11. `record_session_message()` stores the exchange — **still in-memory via `APIState`**, not the formal `conversation_sessions`/`conversation_messages` Postgres tables from `db/migrations/001_initial_schema.sql` (see `erd_reconciliation_sprint5.md`).
12. Flask returns `200` JSON: `answer`, `source_references`, `confidence`, `confidence_score`, `model_used`, `is_fallback`, `session_id`, `backend_mode`, `latency_ms`.

## What changed vs. the Sprint 4 diagram

| Aspect | Sprint 4 (old diagram) | Sprint 5 (actual, this diagram) |
|---|---|---|
| Answer source | `APIState.query_fixture()` fuzzy match against `fixtures/sample_responses.json` | Real ChromaDB retrieval + Ollama generation |
| Ambiguous questions | Not handled | `422` short-circuit before retrieval (new) |
| Cold-start latency | Not addressed | Background warm-up at API startup (new, rev 3) |
| Session storage | In-memory | Still in-memory (unchanged — see ERD reconciliation) |
| Auth | Fixture-backed | Still fixture-backed (unchanged) |

## Scope note

This diagram covers only `/api/query`. Upload/indexing (`/api/upload`, background indexer) has its own real Postgres persistence path via `src/api/db.py` (`uploaded_documents`, `indexing_jobs`) — different from the query path above, and different again from the formal `documents`/`indexing_jobs` tables designed in the Sprint 3 migration. See `erd_reconciliation_sprint5.md`.
