# EduRAG System Design Document v2

## 1. Document Control

| Item | Value |
|---|---|
| Document title | EduRAG System Design Document v2 |
| Project | EduRAG / Paedia, CSIT321 Project 37 |
| Sprint context | Sprint 3 consolidation with Sprint 4 handoff |
| Document owner | Tai Huynh |
| Version | v2 |
| Status | Supervisor-facing draft based on Sprint 3 artifacts |

## 2. Executive Summary

EduRAG is a student-facing course assistant that uses Retrieval-Augmented Generation to answer questions from lecturer-provided course materials. Sprint 3 focused on proving the core RAG path, consolidating architecture decisions, refining the module interface, and documenting privacy, ethics, and evaluation assets needed before full prototype integration.

The most important Sprint 3 result is that the project moved from high-level design into evidence-backed prototype work. A working notebook PoC demonstrated local PDF ingestion, chunking, vector retrieval, and grounded answer generation. At the same time, the team clarified supporting architecture around authentication, upload flows, audit logging, UI state, and data separation between PostgreSQL and ChromaDB.

## 3. Sprint 3 Consolidation Overview

Sprint 3 deliverables are distributed across the team but now form a coherent design package:

- Binh provided the RAG PoC, prompt strategy, model selection notes, and retrieval configuration benchmark.
- Anmoldeep documented the Streamlit UI state model, design system, and wireframe set.
- Tung prepared a labelled test query corpus and sample corpus manifest.
- Namaratne updated ERD v2, DFD v2, risk, and storage planning artifacts.
- Tai consolidated the API specification, privacy policy, ethics review, and Sprint 4 kickoff material.

This document combines those Sprint 3 outputs into a single design view for supervisor review.

## 4. Updated Architecture

EduRAG remains organised as a modular monolith with four clear responsibility areas:

1. Document processing for ingestion, parsing, chunking, and embedding.
2. Vector retrieval over course-scoped content.
3. LLM response generation using retrieved context.
4. Web application services for authentication, upload, query, sessions, monitoring, and access control.

The current prototype path uses a Streamlit user interface backed by a web/API layer, PostgreSQL for relational state, ChromaDB for vector storage, and Ollama for local LLM inference during development. This structure keeps the project operationally manageable while still supporting explicit module boundaries.

## 5. RAG Proof-Of-Concept Evidence

The strongest execution artifact is `notebooks/rag_poc.ipynb`. Based on the reviewed Sprint 3 evidence, the notebook demonstrates:

- PyMuPDF-based extraction from `materials/book_embNLP_draft.pdf`
- page-aware chunk preparation using `RecursiveCharacterTextSplitter`
- local embeddings via `all-MiniLM-L6-v2`
- ChromaDB collection storage with `course_id` metadata
- top-k retrieval for course-scoped questions
- local answer generation through `qwen3:14b`
- fallback behaviour for off-topic or weakly grounded queries

This is important because it proves the project is no longer only conceptual. However, the PoC is still bounded: it is PDF-first, benchmark evidence is provisional, and not every production-facing control has been fully implemented in an integrated backend.

## 6. Document Processing And Retrieval Updates

Sprint 3 evidence supports the following ingestion and retrieval direction:

| Area | Current Sprint 3 direction |
|---|---|
| Source formats | PDF is the strongest validated path; PPTX and DOCX remain important but require more parser validation. |
| Extraction baseline | PyMuPDF is the preferred PDF extraction path. |
| Chunking | Character-based recursive splitting remains the current practical implementation path for the PoC. |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` with 384-dimensional vectors. |
| Vector store | ChromaDB with metadata filtering. |
| Retrieval isolation | `course_id` metadata filtering is a core control against cross-course leakage. |

The reviewed benchmark material selected provisional defaults of `chunk_size=1024`, `chunk_overlap=0`, `top_k=5`, and a distance threshold of `0.65`. These values should be treated as Sprint 3 integration defaults rather than final production tuning.

## 7. Prompt Strategy And RAG Configuration

Sprint 3 prompt and retrieval work was designed to reduce unsupported or misleading answers.

The selected prompt strategy requires:

- answering from retrieved course context
- inline source citations such as `[S1]`
- a visible confidence label
- a standard fallback phrase when the answer is not grounded
- resistance to prompt injection and hidden prompt leakage

The approved fallback wording is:

`Based on general knowledge - not verified against course materials`

This is ethically important because it distinguishes grounded answers from general model output instead of presenting both with the same authority.

## 8. Module 4 API Specification Summary

Tai's Sprint 3 API specification is captured in `docs/api_spec.yaml` and documents the user-facing interface for authentication, querying, uploads, indexing jobs, sessions, monitoring, and health checks.

Key API points include:

- `POST /api/auth/login` for authentication
- `POST /api/query` for course-scoped question answering
- `POST /api/upload` for lecturer/admin document upload
- `DELETE /api/document/{doc_id}` for document removal
- `GET /api/indexing-jobs/{job_id}` for asynchronous upload status polling
- session-history endpoints for conversation continuity
- compatibility monitoring aliases `GET /api/metrics` and `GET /api/logs`
- explicit admin routes `GET /api/admin/stats` and `GET /api/admin/audit-logs`

The API spec also documents JWT bearer authentication, role expectations, reusable schemas, and RAG-specific response fields such as sources, fallback state, confidence label, and model identity.

## 9. Privacy And Ethics Updates

Sprint 3 raised privacy and ethics from side notes to explicit design concerns.

Privacy work now clarifies that:

- students query the system
- lecturers and admins upload course materials
- data should be minimised by category
- role-based access control must govern visibility
- audit events are part of the accountability model
- user data should not be used for advertising or external model training

Ethics work now emphasises:

- hallucination risk when retrieval is weak
- misleading certainty from fluent model output
- the need for course-scoped retrieval isolation
- the need to label fallback answers clearly
- the need to test off-topic and ambiguous cases, not only successful in-scope answers

## 10. UI And Wireframe Updates

Anmoldeep's Sprint 3 artifacts show a coherent student-facing interface direction. The reviewed wireframes include:

- login screen
- main Q&A interface
- document upload screen
- admin dashboard
- session history view

The UI state design also maps Streamlit session state to backend responsibilities such as authentication, uploads, navigation, and conversation history. This is valuable because it links the user experience directly to the relational schema, audit trail, and role model.

## 11. Data Model And Data Flow Updates

Sprint 3 architectural updates clarify the separation between relational and vector data:

- PostgreSQL stores users, roles, courses, memberships, documents, indexing jobs, sessions, messages, refresh tokens, and audit logs.
- ChromaDB stores vector embeddings and retrieval metadata rather than acting as the source of truth for relational state.

The DFD v2 update also makes failure paths explicit. These include invalid uploads, extraction failures, indexing failures, no-hit fallback cases, provider outages, and cross-course leakage concerns. This improves supervisor-facing credibility because the design now addresses what happens when the system fails, not only when it succeeds.

## 12. Testing And Evaluation Assets

The main Sprint 3 evaluation assets are:

- the notebook PoC
- the retrieval benchmark document
- the prompt strategy test results
- Tung's labelled `test_queries.json`
- the sample corpus manifest

The labelled query set is especially important because it covers:

- easy factual in-scope questions
- harder reasoning questions
- off-topic questions that should trigger fallback
- ambiguous questions that require clarification or cautious handling

This broadens evaluation beyond a small manually selected demo set.

## 13. Risks, Limitations, And Sprint 4 Handoff

The main remaining Sprint 3 limitations are:

- retrieval benchmarking is still provisional
- PDF is the strongest validated parser path, while PPTX and DOCX need more confirmation
- some documented controls are intended design behaviours rather than fully integrated runtime features
- backend implementation maturity may lag behind documentation completeness in some areas

The highest-priority Sprint 4 handoff items are:

- integrate the RAG path into the main prototype flow
- validate the broader labelled query set against actual outputs
- confirm backend enforcement of confidence, fallback, and role controls
- finalise retention and audit-access expectations for the prototype
- keep the demo evidence honest about what is implemented versus planned

## 14. Appendix - Source Artifact Inventory

| Area | Artifact |
|---|---|
| RAG PoC | `notebooks/rag_poc.ipynb` |
| RAG configuration | `docs/rag_config.md` |
| Prompt strategy | `docs/prompt_strategy.md` |
| Model selection | `docs/ollama_model_selection.md` |
| Demo checkpoint | `docs/meetings/sprint3_internal_demo.md` |
| UI state | `docs/ui/ui_state.md` |
| Design system | `docs/ui/design_system.md` |
| Wireframes | `docs/ui/wireframes/*.png` |
| Test queries | `tests/test_queries.json` |
| Corpus manifest | `data/sample_manifest.md` |
| ERD changes | `docs/architecture/erd_v2_changes.md` |
| DFD changes | `docs/architecture/dfd_v2_changes.md` |
| Risk register | `docs/architecture/risk_register_sprint3.md` |
| Storage sizing | `docs/architecture/storage_sizing.md` |
| Tai API spec | `docs/api/api_spec.yaml` |
| Tai privacy policy | `docs/governance/privacy_policy.md` |
| Tai ethics review | `docs/governance/ethics_review_sprint3.md` |
| Tai Sprint 4 kickoff | `docs/meetings/sprint_4_kickoff.md` |

## 15. Sprint 5/6 Architecture Reconciliation (added 26 Jul 2026, Sprint 6 T05/T06)

No new architectural change has landed in Sprint 6 itself as of this writing — T07 (model fine-tuning) and T09 (vector DB optimisation) have not yet been merged. This section instead reconciles the existing diagrams and this document against the code as it actually runs today, per the Sprint 6 grading-readiness review.

### 15.1 Query flow — corrected

`docs/architecture/seq_api_query.png` (Sprint 4) documented the fixture-backed query path and explicitly flagged an open "Sprint 5 Gap" toward live retrieval. That gap was closed in Sprint 5 but the diagram was never updated. The corrected flow is documented in `docs/architecture/seq_api_query_sprint5.md` and `docs/architecture/diagrams/seq_api_query_sprint5.svg`: real ChromaDB retrieval (course-scoped, top_k=5, 0.35 similarity (0.65 distance) threshold) and Ollama generation replace `query_fixture()`, and a new ambiguous-question short-circuit (HTTP 422) runs before retrieval.

### 15.2 Data model — correction to §11

Section 11 above states "PostgreSQL stores users, roles, courses, memberships, documents, indexing jobs, sessions, messages, refresh tokens, and audit logs." **This is not accurate for the system as currently implemented.** Only 2 of those 9 designed tables have a real runtime equivalent:

- `uploaded_documents` and `indexing_jobs` (`src/api/db.py`, added Sprint 5 for QA-DATA-001) are real, live Postgres tables — but with a different, simpler, non-FK-constrained schema than the `documents`/`indexing_jobs` tables designed in `db/migrations/001_initial_schema.sql`.
- `users`, `courses`, `course_memberships`, `conversation_sessions`, `conversation_messages`, `refresh_tokens`, and `audit_logs` remain fixture-backed or in-memory (`src/api/state.py`). The migration file that defines them exists but no current code path queries them.

Full detail, table-by-table, is in `docs/architecture/erd_reconciliation_sprint5.md` and `docs/architecture/diagrams/erd_reconciliation_sprint5.svg`.

### 15.3 Why this is reported now rather than silently fixed

Rewiring the 7 unused tables to Postgres is a real engineering task, not a documentation fix, and is out of scope for the current 2-week A4 window. Consistent with this project's evidence standard elsewhere (QA checklists, sprint status tables), the correct action is to report the gap accurately rather than let the design docs continue to claim more than the system does. The A4 report and RTM (`docs/rtm_a4.md`) should cite this section rather than repeat the original Section 11 claim unqualified.
