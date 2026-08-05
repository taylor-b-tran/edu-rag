# A4 Evidence Index

One-stop map of every artifact backing the A4 (Prototype Presentation) submission. Grouped by what a marker or team member is likely looking for.

## 1. Requirements & progress vs. A2

| Evidence | What it shows |
|---|---|
| [`docs/rtm_a4.md`](rtm_a4.md) / [`.docx`](rtm_a4.docx) | Requirements Traceability Matrix — all 33 functional requirements + 8 new NFRs, mapped to current status (Implemented / Partial / Not Started) with evidence pointers |
| [`docs/sprint6_status_table.md`](sprint6_status_table.md) | Task-by-task Sprint 6 progress (19/34 done), owners, evidence per task |
| [`README.md`](../README.md) §19 "For the Marker" | Fast orientation path for grading — what's real, what's fixture, how to verify in under 5 minutes |

## 2. Architecture & system design

| Evidence | What it shows |
|---|---|
| [`docs/architecture/erd_reconciliation_sprint5.md`](architecture/erd_reconciliation_sprint5.md) / [`.svg`](architecture/diagrams/erd_reconciliation_sprint5.svg) | As-designed vs. as-implemented data model — honest accounting of which 2/9 Postgres tables are actually wired up |
| [`docs/architecture/seq_api_query_sprint5.md`](architecture/seq_api_query_sprint5.md) / [`.svg`](architecture/diagrams/seq_api_query_sprint5.svg) | Real live query sequence diagram (rate limit → auth → retrieval → generation → fallback), supersedes the old fixture-only diagram |
| [`docs/system_design/system_design_document_v2_source.md`](system_design/system_design_document_v2_source.md) §15 / [`EduRAG_System_Design_Document_v2.docx`](system_design/EduRAG_System_Design_Document_v2.docx) | Full system design doc, with Sprint 5/6 reconciliation section appended |

## 3. Performance & benchmarks

| Evidence | What it shows |
|---|---|
| [`docs/t10_embedding_benchmark.md`](t10_embedding_benchmark.md) | Batch vs. per-chunk embedding: 8.6x–15.5x speedup, measured live |
| [`docs/finetuning_benchmark_sprint6.md`](finetuning_benchmark_sprint6.md) / `.json` | Model fine-tuning / prompt strategy before-after benchmark |
| [`docs/t25_gpu_free_verification.md`](t25_gpu_free_verification.md) | Base Compose runs correctly with no GPU (grading-machine safety) |
| GPU 3-tier auto-select (PR #54) | `scripts/start_stack.sh`/`.ps1` — CPU / 8GB / 16GB+ tiers, validated live on an 8GB card (~1-2s/query vs. 60-180s CPU) |

## 4. Verification & QA

| Evidence | What it shows |
|---|---|
| [`docs/dry_run_1_cold_grader.md`](dry_run_1_cold_grader.md) | First fresh-machine dry run, 2 bugs found and fixed |
| [`docs/vv_full_app_report_2026-08-03.md`](vv_full_app_report_2026-08-03.md) | Full V&V pass — all 3 roles, upload pipeline end-to-end, what's real vs. fixture-backed |
| [`docs/t09_vector_db_optimisation.md`](t09_vector_db_optimisation.md) | Batch-encoding fix verification (real upload/query/cleanup) |
| [`docs/t11_t12_ui_polish.md`](t11_t12_ui_polish.md) | UI fixes found via live testing (frozen-looking generation, timeout mismatch) + before/after screenshots |
| pytest suite | 118/118 passing, run inside the `api` container — `docker compose exec api pytest -v` |
| CI (`.github/workflows/ci.yml`) | Green on every merge to `develop`, PRs #48-54 |

## 5. UI / design

| Evidence | What it shows |
|---|---|
| [`docs/ui/design_system.md`](ui/design_system.md), [`docs/ui/ui_state.md`](ui/ui_state.md), [`docs/ui/acceptance_criteria.md`](ui/acceptance_criteria.md) | UI design system, session-state model, acceptance criteria |
| [`docs/a3_interface_demo/`](a3_interface_demo/) | Fixture-backed UI screenshots (login, chat+citations, fallback, upload, role comparison) from A3 |

## 6. Demo & presentation

| Evidence | What it shows |
|---|---|
| [`docs/a4_demo_video_script.md`](a4_demo_video_script.md) | Full script + timeline for the A4 walkthrough video (all 3 roles) |
| `scripts/check_demo_ready.py` | One-command health check before any live demo |

## 7. Code

| Path | What it is |
|---|---|
| `src/api/` | Flask REST API — auth, query, upload, sessions, admin |
| `src/document_processor/` | Chunker, embedding, RAG pipeline |
| `apps/streamlit/` | Presentation layer (role-based UI) |
| `db/migrations/` | Original relational schema design (see §2 reconciliation for what's actually live) |
| `test/` | 118-test pytest suite |
