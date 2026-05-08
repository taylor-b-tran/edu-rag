# Sprint 3 Internal Integration Checkpoint

Project: Paedia EduRAG, CSIT321 Project 37, Group 19  
Owner: Thanh Binh Tran  
Date: 22 April 2026  
Purpose: Confirm that the Sprint 3 backend/RAG work is ready for team handoff and Sprint 4 preparation.

## 1. Checkpoint Summary

The Sprint 3 backend infrastructure and RAG proof-of-concept track are ready for internal handoff. The Docker stack, PostgreSQL schema, one-PDF RAG notebook, prompt strategy, and RAG configuration benchmark are all present in the project workspace.

Scope note: this checkpoint originally did not claim that a production API or finished application server existed. Sprint 4 Task 2 has since added a fixture-backed Flask API wrapper at `src/api/app.py` with route modules under `src/api/routes/`; it preserves the same contract expected by the Streamlit client while the real RAG pipeline is connected behind the route layer.

Recording evidence: no actual uploaded PoC recording URL was present in the local workspace as of 9 May 2026. Until the team supplies the video URL, this file records the demo walkthrough and the meeting-minute evidence fallback. Insert the final recording URL here when available:

`PoC recording link: TODO - actual uploaded video URL required`

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
| Flask API wrapper | Ready | `src/api/app.py` and `src/api/routes/` expose auth, query, upload/indexing, document, session, health, and admin compatibility routes in fixture-backed Sprint 4 mode. |
| Contribution bundle | Ready | The Sprint 3 RAG/backend files are synced into the project workspace for review. |

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
| Anmoldeep Singh | Unblocked for UI-to-backend planning | Notebook query flow, prompt output format, citation structure, fallback behaviour, Docker service contract, and the Sprint 4 Flask wrapper at `src/api/app.py`. | The wrapper is fixture-backed until the real RAG pipeline is connected behind the same route contract. |
| Tai Huynh | Unblocked for API, ethics, and System Design v2 consolidation | PostgreSQL schema, RAG config, prompt strategy, retrieval edge cases, Docker contract, and benchmark results. | Larger labelled query corpus is still needed before final evaluation claims are strong. |
| Kahavidanage Namaratne | Unblocked for ERD v2, DFD v2, error paths, and storage sizing | Actual SQL schema, ChromaDB metadata design, Docker topology, retrieval edge cases, and data-store assumptions. | ChromaDB stores vectors outside the relational schema, so ERD should not model embeddings as PostgreSQL rows. |

## 6. Open Follow-Ups

| Follow-Up | Owner | Reason |
|---|---|---|
| Add actual uploaded demo recording URL | Binh / Tung | Placeholder added above; the real recording URL was not present in the local workspace on 9 May 2026. |
| Rerun benchmark with `tests/test_queries.json` once available | Binh / Tung | Batch 7 used a small provisional query set because the larger 31-question corpus was not present locally. |
| Connect real RAG pipeline behind Flask routes | Binh / Anmoldeep / Tung | The fixture-backed wrapper route contract is ready; real retrieval/generation integration remains the next implementation step. |
| Update ERD and DFD from actual schema and error paths | Namaratne | Sprint 3 backend outputs now provide concrete implementation evidence. |
| Consolidate outputs into System Design Document v2 | Tai | Backend artefacts are now ready for documentation handoff. |

## 7. Verdict

The Sprint 3 backend infrastructure and RAG PoC track are ready for checkpoint review. The project now has enough backend evidence for Sprint 4 planning: runnable infrastructure services, a concrete relational schema, a real one-PDF RAG PoC, selected prompt defaults, selected retrieval defaults, and a clear handoff path for UI, API, ethics, ERD, DFD, and report consolidation work.
