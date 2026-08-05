# Assessment 4 — Prototype Presentation (working notes)

**Project:** EduRAG / Paedia — Group 19, Aletheia's Zetetes, CSIT321 Project 37
**Status:** superseded by the final report — `docs/a4_report.docx`. Kept here as plain-text working notes; the docx is the version to submit.

---

## 1. Project Overview (carried over from A2, updated)

Paedia is a course-scoped RAG assistant: a lecturer uploads material, a student asks a question, and the answer is generated only from that material with a page-level citation attached. Unlike a generic LLM, Paedia can't answer from general knowledge — if nothing in the indexed corpus clears the similarity threshold, it says so instead of guessing.

Since A2/A3, the system moved from a fixture-backed prototype to a fully live pipeline — real ChromaDB retrieval, real local LLM generation via Ollama, real Postgres persistence for uploads. Sprint 6 focused on production-readiness: performance, correctness under load, grading-machine compatibility, and fixing gaps found by actually using the app.

## 2. Progress vs. A2 Requirements

Full detail in `docs/rtm_a4.md` — 33 functional requirements plus 8 non-functional requirements, each with a status and evidence pointer. Summary:

- Core Q&A flow (upload → chunk → embed → retrieve → generate → cite): implemented and tested end to end.
- Role-based access (student/lecturer/admin): implemented, RBAC enforced server-side.
- Fallback behaviour: implemented — a 0.35 similarity threshold decides whether the system answers from context or declines.
- Retrieval accuracy benchmarking (precision/recall against a labelled set): marked Partial. What exists so far is generation-quality and speed benchmarking, not formal retrieval metrics.
- The 9-table relational schema from A2: only 2 tables (`uploaded_documents`, `indexing_jobs`) are actually wired to Postgres. Auth, courses, and chat sessions are still fixture/in-memory — see §3.

## 3. System Architecture

- Sequence diagram of the real live query path: `docs/architecture/seq_api_query_sprint5.md` (rate limit → auth → ambiguous-question short-circuit → ChromaDB retrieval → Ollama generation → fallback labelling).
- Data model reconciliation: `docs/architecture/erd_reconciliation_sprint5.md`. The original System Design Document claimed the full 9-table Postgres schema was live; checking the actual code and database showed only 2 tables are. Fixed in the design doc itself (§15).
- Full system design document: `docs/system_design/EduRAG_System_Design_Document_v2.docx`.

## 4. What's New This Sprint

- Batch-encoding replaced per-chunk embedding calls — 8.6x–15.5x measured speedup (`docs/t10_embedding_benchmark.md`).
- Setup script now auto-detects GPU VRAM and picks between 3 model tiers (CPU / 8GB-class GPU / 16GB+ GPU), instead of a binary choice that wasted mid-range GPUs. Validated on an 8GB card: ~1-2s/query vs. 60-180s on CPU.
- Two UI bugs fixed after using the app in each role: chat looked frozen for the whole generation wait (up to 3 minutes on CPU) — the question now shows immediately with a live status indicator. Students briefly saw a non-functional upload box; admin Edit/Delete buttons did nothing when clicked. Both fixed.
- Confirmed the base Docker Compose stack (no GPU) runs correctly from a fresh clone with no manual fixes — `docs/dry_run_2_cold_grader.md`.
- Before/after screenshots: `docs/t11_t12_ui_polish.md`.

## 5. Verification

- Automated tests: 118/118 passing, run inside the `api` container.
- CI green on every merge to `develop` (PRs #48–#54).
- Manual pass across all 3 roles plus the upload pipeline (upload → chunk → embed → index → query → cite → delete): `docs/vv_full_app_report_2026-08-03.md`.
- Cold-start dry run, README followed from a fresh clone: `docs/dry_run_2_cold_grader.md`.

## 6. Known Limitations

- Auth, courses, and chat sessions are fixture/in-memory, not the full relational schema originally designed.
- Retrieval accuracy hasn't been formally benchmarked against a labelled query set yet.
- Admin dashboard is read-only in this build — user-management actions are disabled, not wired to a backend.

None of these block the core demo flow.

## 7. Demo / Submission

- Live walkthrough script (all 3 roles): `docs/a4_demo_video_script.md`.
- One-command readiness check: `python scripts/check_demo_ready.py`.
- Code package: built via `git archive` from `develop`, so it's clean of local dev files, `.env`, and `.git` history. See `README.md` §19 "For the Marker" for the fastest path to a working demo.

---

*Draft — please review and merge with any A2 content not covered here (cover page, references, formatting to match the subject's report template).*
