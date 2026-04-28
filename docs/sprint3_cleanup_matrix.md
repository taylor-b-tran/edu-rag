# Sprint 3 Repo Cleanup Matrix

## Purpose

This matrix documents Sprint 3 deliverables by task and owner, then maps each deliverable to a canonical repository path. The cleanup technique used is "single source of truth in root packages" while keeping `Team_Contributions/<member>/README.md` as an ownership index.

## Canonical Structure Rules

- `docs/`: report and design documentation deliverables.
- `apps/`: application entry points and UI/backend integration scripts.
- `fixtures/`: mock/test fixture payloads for prototypes.
- `tests/`: reusable test corpora and test inputs.
- `data/`: manifests and metadata (not raw protected course files).
- `Team_Contributions/`: member ownership index only (no canonical source files).

## Cleanup Table

| Task | Owner | Expected Output (Sprint 3 plan) | Canonical Path After Cleanup | Status | Action |
|---|---|---|---|---|---|
| 1 | Thanh Binh Tran | RAG PoC notebook | `notebooks/rag_poc.ipynb` | Complete | Kept canonical in root |
| 2 | Thanh Binh Tran | Docker stack docs/config | `docker-compose.yml`, `README_docker.md`, `.env.example` | Complete | Kept canonical in root |
| 3 | Thanh Binh Tran | PostgreSQL schema and seed | `db/migrations/001_initial_schema.sql`, `db/seed/development.sql` | Complete | Kept canonical in root |
| 4 | Thanh Binh Tran | Prompt strategy | `docs/prompt_strategy.md` | Complete | Kept canonical in root |
| 5 | Thanh Binh Tran | RAG benchmark config | `docs/rag_config.md` | Complete | Kept canonical in root |
| 6 | Thanh Binh Tran | Integration checkpoint minutes | `docs/meetings/sprint3_internal_demo.md` | Partial | Demo doc present; recording link still missing |
| 7 | Anmoldeep Singh | 5 wireframe screens | `docs/ui/wireframes/*.png` | Complete | Moved from member package |
| 8 | Anmoldeep Singh | Streamlit UI + fixtures | `apps/streamlit/main.py`, `fixtures/sample_responses.json` | Complete | Moved from member package |
| 9 | Anmoldeep Singh | UI state document | `docs/ui/ui_state.md` | Complete | Moved from member package |
| 10 | Anmoldeep Singh | Design system | `docs/ui/design_system.md` | Complete | Moved from member package |
| 11 | Thi Hong Ngoc Nguyen | Parser evaluation | `docs/parser_evaluation.md` | Complete | Kept canonical in root |
| 12 | Thi Hong Ngoc Nguyen | Chunker implementation + tests | `src/document_processor/chunker.py`, `test/test_chunker.py` | Complete | Kept canonical in root |
| 13 | Thi Hong Ngoc Nguyen | Embedder scaffolding | `src/vector_retriever/embedder.py` | Complete | Kept canonical in root |
| 14 | Thi Hong Ngoc Nguyen | Retrieval edge-case design | `docs/rag_config.md` (Retrieval Edge Cases section) | Complete | Kept canonical in root |
| 15 | Thi Hong Ngoc Nguyen | Pair contribution to PoC | `notebooks/rag_poc.ipynb` | Partial | Co-authoring is process evidence, not file split |
| 16 | Tung Phuong Anh Huynh | Sprint 3 meeting reports | `docs/meetings/sprint3_*.docx` | Partial | Not all planned reports present |
| 17 | Tung Phuong Anh Huynh | 30+ labelled query corpus | `tests/test_queries.json` | Complete | Added canonical corpus file |
| 18 | Tung Phuong Anh Huynh | Sample manifest + external corpus list | `data/sample_manifest.md` | Complete | Added canonical manifest |
| 19 | Tung Phuong Anh Huynh | Sponsor review minutes | `docs/meetings/sprint3_sponsor_review.docx` | Deferred | Intentionally untouched until sponsor meeting later this week |
| 20 | Tung Phuong Anh Huynh | UI/backend integration support | `apps/integration/*` and `apps/streamlit/main.py` wiring | Partial | Integration artifacts migrated from branch and path-normalised; runtime test still required |
| 21 | Kahavidanage Namaratne | ERD v2 updates | `docs/architecture/erd_v2_changes.md` | Complete | Moved from member package |
| 22 | Kahavidanage Namaratne | DFD v2 updates | `docs/architecture/dfd_v2_changes.md` | Complete | Moved from member package |
| 23 | Kahavidanage Namaratne | Upload error sequence diagram | `docs/architecture/diagrams/upload_failure_sequence.png` | Complete | Moved from member package |
| 24 | Kahavidanage Namaratne | Risk register update | `docs/architecture/risk_register_sprint3.md` | Complete | Moved from member package |
| 25 | Kahavidanage Namaratne | Storage sizing estimate | `docs/architecture/storage_sizing.md` | Complete | Moved from member package |
| 26 | Tai Huynh | OpenAPI spec | `docs/api/api_spec.yaml` | Complete | Added canonical path |
| 27 | Tai Huynh | Privacy policy | `docs/governance/privacy_policy.md` | Complete | Added canonical path |
| 28 | Tai Huynh | Ethics review | `docs/governance/ethics_review_sprint3.md` | Complete | Added canonical path |
| 29 | Tai Huynh | System design v2 | `docs/system_design/EduRAG_System_Design_Document_v2.docx` | Complete | Added canonical path |
| 30 | Tai Huynh | Sprint 4 kickoff agenda | `docs/meetings/sprint_4_kickoff.md` | Complete | Added canonical path |

## Team Package Policy

`Team_Contributions/<member>/README.md` now acts as the ownership index and points to canonical root paths. This avoids duplicate drifting files across member folders and root packages.
