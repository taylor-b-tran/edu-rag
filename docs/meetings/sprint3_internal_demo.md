# Sprint 3 Internal Integration Checkpoint

Project: Paedia EduRAG, CSIT321 Project 37, Group 19  
Owner: Thanh Binh Tran  
Date: 22 April 2026  
Purpose: Confirm that the Sprint 3 backend/RAG work is ready for team handoff and Sprint 4 preparation.

## 1. Checkpoint Summary

The Sprint 3 backend infrastructure and RAG proof-of-concept track are ready for internal handoff. The Docker stack, PostgreSQL schema, one-PDF RAG notebook, prompt strategy, and RAG configuration benchmark are all present in the project workspace.

Scope note: this checkpoint does not claim that a production API or finished application server exists yet. The Compose `app` service is still a bootstrap workspace container; the validated runtime pieces are PostgreSQL, ChromaDB, Ollama, and the executed notebook workflow.

Sprint 4 update on 12 May 2026: the team added a real Google Drive recording
link for the connected prototype walkthrough. This closes the Sprint 4 Task 4
evidence gap, with the scope note that the recording demonstrates a
Streamlit-to-Flask prototype and not a fully live ChromaDB/Ollama RAG path.

## 1.1 Sprint 4 Demo Recording Evidence

| Item | Value |
|---|---|
| Recording title | Sprint 4 connected prototype demo |
| Recording link | https://drive.google.com/file/d/1pZLpK6btLJEVn3XzLPOjm6v_ViHEmJTb/view?usp=sharing |
| Date added | 12 May 2026 |
| Owner | Thanh Binh Tran |
| Coverage | Flask health route, Streamlit login, chat/query flow, fallback behaviour, document/session/admin screens |
| Scope boundary | Demonstrates the Sprint 4 connected prototype; backend query mode remains fixture-backed and live ChromaDB/Ollama RAG is Sprint 5 work |
| Access check | Link was provided as a Google Drive share link; verify viewer access from a non-owner account before final A3 submission |

## 2. Evidence Checklist

| Area | Status | Evidence |
|---|---|---|
| Docker infrastructure stack | Ready | `docker-compose.yml`, `.env.example`, `README_docker.md`, and optional `docker-compose.gpu.yml`; Compose config validated. |
| Running backend services | Ready | `postgres`, `chromadb`, and `ollama` containers were up; PostgreSQL reported healthy. The `app` service remains bootstrap-only and is not a callable API yet. |
| PostgreSQL schema | Ready | `db/migrations/001_initial_schema.sql` and `db/seed/development.sql` exist and have been applied to the live container. |
| Seed data | Ready | Live database contained users, courses, documents, conversation messages, and audit logs. |
| RAG PoC notebook | Ready | `notebooks/rag_poc.ipynb` contains executed code cells and output evidence using the Batch 7 RAG defaults. |
| Source material | Ready | `materials/book_embNLP_draft.pdf` was used as the first real PDF. |
| Embedding model | Ready | `sentence-transformers/all-MiniLM-L6-v2`. |
| Vector store | Ready | ChromaDB with `course_id` metadata filtering. |
| LLM runtime | Ready | Ollama has `qwen3:14b` installed. |
| Prompt strategy | Ready | `docs/prompt_strategy.md` selects the safety-first evidence-cited RAG prompt. |
| RAG configuration | Ready | `docs/rag_config.md` selects `chunk_size=1024`, `overlap=0`, `top_k=5`, threshold `0.65`; the notebook has been rerun with the same defaults. |
| Contribution bundle | Ready | The Sprint 3 RAG/backend files are synced into the project workspace for review. |
| Sprint 4 connected prototype recording | Ready | Google Drive recording link filed in Section 1.1. |

## 3. Demo Walkthrough

Internal demo order:

1. Show the root Docker stack with `docker compose ps`.
2. Show PostgreSQL seed counts and explain the core relational tables.
3. Open `notebooks/rag_poc.ipynb` and show the successful execution outputs.
4. Show ingestion of `materials/book_embNLP_draft.pdf`.
5. Show chunking, embedding, and ChromaDB storage with `course_id`.
6. Show an in-scope query returning answer text with citations.
7. Show the fallback behaviour for an off-topic query.
8. Show `docs/prompt_strategy.md` and `docs/rag_config.md` as the frozen Sprint 3 defaults.
9. Explain which teammates are now unblocked for Sprint 4.

## 4. Frozen Backend Decisions

| Decision | Current Value |
|---|---|
| Local stack | Docker Compose with bootstrap `app`, `postgres`, `chromadb`, `ollama` |
| Relational database | PostgreSQL |
| Vector database | ChromaDB |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Local generation model | `qwen3:14b` through Ollama |
| Prompt default | Safety-first evidence-cited RAG |
| Chunk size | `1024` characters |
| Chunk overlap | `0` characters |
| Retrieval top-k | `5` |
| Fallback threshold | Cosine distance `0.65` |
| Course isolation | `course_id` metadata filter |

## 5. Teammate Handoff

| Teammate | Status | What They Can Use Now | Remaining Caveat |
|---|---|---|---|
| Anmoldeep Singh | Unblocked for UI-to-backend planning | Notebook query flow, prompt output format, citation structure, fallback behaviour, and Docker service contract. | A formal API wrapper is not implemented yet; initial integration should wait for a thin API/function wrapper or explicitly call notebook-derived code during prototyping. |
| Tai Huynh | Unblocked for API, ethics, and System Design v2 consolidation | PostgreSQL schema, RAG config, prompt strategy, retrieval edge cases, Docker contract, and benchmark results. | Larger labelled query corpus is still needed before final evaluation claims are strong. |
| Kahavidanage Namaratne | Unblocked for ERD v2, DFD v2, error paths, and storage sizing | Actual SQL schema, ChromaDB metadata design, Docker topology, retrieval edge cases, and data-store assumptions. | ChromaDB stores vectors outside the relational schema, so ERD should not model embeddings as PostgreSQL rows. |

## 6. Open Follow-Ups

| Follow-Up | Owner | Reason |
|---|---|---|
| Verify demo recording share access | Binh / Tung | Recording link is now filed; confirm it opens for the intended team/supervisor audience before A3 evidence freeze. |
| Rerun benchmark with `tests/test_queries.json` once available | Binh / Tung | Batch 7 used a small provisional query set because the larger 31-question corpus was not present locally. |
| Decide UI integration boundary | Binh / Anmoldeep / Tung | The backend infrastructure and notebook evidence are ready, but a formal API wrapper is still a Sprint 4 integration decision. |
| Update ERD and DFD from actual schema and error paths | Namaratne | Sprint 3 backend outputs now provide concrete implementation evidence. |
| Consolidate outputs into System Design Document v2 | Tai | Backend artefacts are now ready for documentation handoff. |

## 7. Verdict

The Sprint 3 backend infrastructure and RAG PoC track are ready for checkpoint review. The project now has enough backend evidence for Sprint 4 planning: runnable infrastructure services, a concrete relational schema, a real one-PDF RAG PoC, selected prompt defaults, selected retrieval defaults, and a clear handoff path for UI, API, ethics, ERD, DFD, and report consolidation work.
