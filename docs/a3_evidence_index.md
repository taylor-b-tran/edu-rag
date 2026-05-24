# Assessment 3 Evidence Index

**Task:** S5-T14
**Owner:** Tai Huynh
**Sprint:** 5 (14 May – 28 May 2026)
**Last updated:** 24 May 2026

> Canonical pointer file for every artifact that backs Assessment 3 claims. If a claim in the A3 report cites EduRAG evidence, the file must be listed here with a stable path. Update this file whenever new evidence lands on `develop`.

---

## 1. Sprint plan and scope

| Artifact | Path |
|---|---|
| Sprint 5 kickoff plan | [`docs/sprint_5_kickoff.md`](sprint_5_kickoff.md) |
| Sprint 4 closeout summary | [`docs/sprint4_summary.md`](sprint4_summary.md) |
| Sprint 5 status table (per task) | [`docs/sprint5_status_table.md`](sprint5_status_table.md) |
| Sprint 5 implementation summary | [`docs/sprint5_implementation_summary.md`](sprint5_implementation_summary.md) |
| Risk register | [`docs/risk_register.md`](risk_register.md) |
| Sprint 5 runtime / demo setup notes | [`docs/sprint5_runtime_notes.md`](sprint5_runtime_notes.md) |

## 2. CI / CD evidence

| Artifact | Path |
|---|---|
| CI workflow | [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) |
| Docker demo workflow | [`.github/workflows/docker-demo.yml`](../.github/workflows/docker-demo.yml) |
| Sprint 5 integration gate | [`scripts/sprint5_integration_gate.py`](../scripts/sprint5_integration_gate.py) |
| CI test validation report | [`docs/ci_test_validation_sprint5.md`](ci_test_validation_sprint5.md) |
| QA checklist | [`docs/qa_checklist_sprint5.md`](qa_checklist_sprint5.md) |
| Demo bug report | [`docs/demo_bug_report_sprint5.md`](demo_bug_report_sprint5.md) |
| Latest CI run on `develop` | GitHub Actions tab — paste latest URL during A3 freeze |

## 3. RAG configuration and benchmarks

| Artifact | Path |
|---|---|
| RAG config decisions | [`docs/rag_config.md`](rag_config.md) |
| Embedding benchmarks | [`docs/embedding_benchmarks.md`](embedding_benchmarks.md) |
| Parser evaluation | [`docs/parser_evaluation.md`](parser_evaluation.md) |
| Ollama model selection | [`docs/ollama_model_selection.md`](ollama_model_selection.md) |
| Prompt strategy | [`docs/prompt_strategy.md`](prompt_strategy.md) |
| Fixture-mode 31-query benchmark | [`docs/rag_config_benchmark_31q.json`](rag_config_benchmark_31q.json) |
| 22 April variant benchmark | [`docs/rag_config_benchmark_2026-04-22.json`](rag_config_benchmark_2026-04-22.json) |
| Live retrieval validation report | [`test/validation_report.json`](../test/validation_report.json) |
| Sprint 5 live benchmark runbook + results | [`docs/rag_benchmark_sprint5.md`](rag_benchmark_sprint5.md) |

## 4. Architecture and design

| Artifact | Path |
|---|---|
| System design document | [`docs/system_design/EduRAG_System_Design_Document_v2.docx`](system_design/EduRAG_System_Design_Document_v2.docx) |
| System design source | [`docs/system_design/system_design_document_v2_source.md`](system_design/system_design_document_v2_source.md) |
| ERD v2 | [`docs/architecture/erd_v2.png`](architecture/erd_v2.png) · [diff notes](architecture/erd_v2_changes.md) |
| DFD Level 1 v2 | [`docs/architecture/diagrams/dfd_level1_v2.png`](architecture/diagrams/dfd_level1_v2.png) · [diff notes](architecture/dfd_v2_changes.md) |
| Upload failure sequence | [`docs/architecture/diagrams/upload_failure_sequence.png`](architecture/diagrams/upload_failure_sequence.png) |
| API query sequence | [`docs/architecture/seq_api_query.png`](architecture/seq_api_query.png) · [notes](architecture/seq_api_query.md) |
| Storage sizing | [`docs/architecture/storage_sizing.md`](architecture/storage_sizing.md) |
| API specification | [`docs/api/api_spec.yaml`](api/api_spec.yaml) · [validation](api/api_spec_validation.md) |

## 5. UI / UX evidence

| Artifact | Path |
|---|---|
| UI state machine | [`docs/ui/ui_state.md`](ui/ui_state.md) |
| Design system | [`docs/ui/design_system.md`](ui/design_system.md) |
| Acceptance criteria | [`docs/ui/acceptance_criteria.md`](ui/acceptance_criteria.md) |
| Wireframes (Sprint 3) | [`docs/ui/wireframes/`](ui/wireframes/) |
| A3 interface demo — login | [`docs/a3_interface_demo/01_login_screen.png`](a3_interface_demo/01_login_screen.png) |
| A3 interface demo — chat + citations | [`docs/a3_interface_demo/02_chat_with_citations.png`](a3_interface_demo/02_chat_with_citations.png) |
| A3 interface demo — fallback response | [`docs/a3_interface_demo/03_fallback_response.png`](a3_interface_demo/03_fallback_response.png) |
| A3 interface demo — document upload | [`docs/a3_interface_demo/04_document_upload.png`](a3_interface_demo/04_document_upload.png) |
| A3 interface demo — role comparison | [`docs/a3_interface_demo/05_role_comparison.png`](a3_interface_demo/05_role_comparison.png) |
| A3 interface demo — course switching | [`docs/a3_interface_demo/06_course_switching.png`](a3_interface_demo/06_course_switching.png) |
| A3 interface demo — narrative | [`docs/a3_interface_demo/narrative.md`](a3_interface_demo/narrative.md) |

## 6. Governance and ethics

| Artifact | Path |
|---|---|
| Ethics review | [`docs/governance/ethics_review_sprint3.md`](governance/ethics_review_sprint3.md) |
| Privacy policy | [`docs/governance/privacy_policy.md`](governance/privacy_policy.md) |

## 7. Meeting / supervisor evidence

| Artifact | Path |
|---|---|
| Sprint 3 internal demo notes | [`docs/meetings/sprint3_internal_demo.md`](meetings/sprint3_internal_demo.md) · [docx](meetings/sprint3_internal_demo.docx) |
| Sprint 3 sponsor review | [`docs/meetings/sprint3_sponsor_review.docx`](meetings/sprint3_sponsor_review.docx) |
| Sprint 4 kickoff | [`docs/meetings/sprint_4_kickoff.md`](meetings/sprint_4_kickoff.md) |
| Sprint 4 sponsor review | [`docs/meetings/sprint4_sponsor_review.docx`](meetings/sprint4_sponsor_review.docx) |
| Sprint 4 group meeting record | [`docs/meetings/Sprint4_EduRAG_Group19.docx`](meetings/Sprint4_EduRAG_Group19.docx) |
| Sprint 5 sponsor review | (to be added 27 May) |

## 8. Source code anchors referenced by A3 report

| Subsystem | Entry point |
|---|---|
| Flask API app factory | [`src/api/app.py`](../src/api/app.py) |
| API state + fixture fallback | [`src/api/state.py`](../src/api/state.py) |
| Query route | [`src/api/routes/query.py`](../src/api/routes/query.py) |
| Auth + RBAC route | [`src/api/routes/auth.py`](../src/api/routes/auth.py) |
| Upload + indexing-job route | [`src/api/routes/documents.py`](../src/api/routes/documents.py) |
| Session route | [`src/api/routes/sessions.py`](../src/api/routes/sessions.py) |
| Chunker | [`src/document_processor/chunker.py`](../src/document_processor/chunker.py) |
| Seed corpus | [`src/document_processor/seed_documents.py`](../src/document_processor/seed_documents.py) |
| Ingest path (Chroma + embedder) | [`src/document_processor/ingest_corpus.py`](../src/document_processor/ingest_corpus.py) |
| Offline embedder (CI fallback) | [`src/document_processor/offline_embedder.py`](../src/document_processor/offline_embedder.py) |
| RAG pipeline (Retriever + Ollama generation) | [`src/document_processor/rag_pipeline.py`](../src/document_processor/rag_pipeline.py) |
| Vector embedder benchmark | [`src/vector_retriever/embedder.py`](../src/vector_retriever/embedder.py) |
| Streamlit UI | [`apps/streamlit/main.py`](../apps/streamlit/main.py) |
| Streamlit API client | [`apps/streamlit/api_client.py`](../apps/streamlit/api_client.py) |
| Integration launcher | [`apps/integration/start.sh`](../apps/integration/start.sh) |

## 9. Tests

| Suite | Path |
|---|---|
| API integration tests | [`test/test_api.py`](../test/test_api.py) |
| Chunker tests | [`test/test_chunker.py`](../test/test_chunker.py) |
| Sprint 5 integration gate tests | [`test/test_sprint5_integration_gate.py`](../test/test_sprint5_integration_gate.py) |
| Retrieval validation (Ngoc) | [`test/validate_retrieval.py`](../test/validate_retrieval.py) |
| 31-query fixtures | [`fixtures/test_queries.json`](../fixtures/test_queries.json) |
| Sample fixture responses | [`fixtures/sample_responses.json`](../fixtures/sample_responses.json) |

## 10. Demo recording (final A3)

| Item | Status | Link |
|---|---|---|
| Demo script (11 steps per `sprint_5_kickoff.md` §10) | To be drafted in `sprint5_implementation_summary.md` §Demo script | — |
| Final demo recording | To be added 27–28 May | (Drive / OneDrive share link) |
| Recording access check from non-owner account | To be added | — |

## 11. Pull request history (Sprint 5)

| PR | Title | Merged |
|---|---|---|
| #27 | feature/s5-doc-processor (initial seeded ingestion path) | 18 May |
| #29 | Sprint 5 integration gate | 19 May |
| #30 | S5-T05/T06/T07/T08 — Tung QA + CI validation + benchmark + bug report skeleton | 19 May |
| #31 | Ollama generation + citation mapping + retrieval validation | 20 May |
| #32 | S5-T05/T06 fill-in updates | 22 May |
| #33 | Untrack `chroma_data/` vector store binaries | 22 May |
| #35 | Switch `/api/query` backend from fixture to ChromaDB | 23 May |
| #36 | Streamlit UI S5-T09..T12 + A3 screenshots (Anmoldeep) | 23 May |
| #37 | Lazy `chromadb` import + fixture fallback + CI report populated | 23 May |
| #38 | Remove `===` patterns from raw CI text | 23 May |
| #39 | Remove `ci_pytest_raw_sprint5.txt` (integration gate noise) | 23 May |
| (pending) | S5-T13..T16 + live benchmark | 25 May target |

## 12. External references (non-repo)

| Item | Pointer |
|---|---|
| Shared tracker (Google Sheet) | https://docs.google.com/spreadsheets/d/13Y9YarTRwCqpFcu7riYiWvzZRK6QBciaeHPsMDXAOfI/edit |
| Sprint 5 plan source doc (Google Doc "Sprint 5 - EduRAG") | (team Drive — owner: Thanh Binh Tran) |
| GitHub repo | https://github.com/taylor-b-tran/edu-rag |
| Demo recording (when filed) | (to be added) |
