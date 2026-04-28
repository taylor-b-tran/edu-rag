# AGENTS.md

## Project Overview

EduRAG is a CSIT321 university project that builds a course-material-grounded assistant using Retrieval-Augmented Generation (RAG). The current repository state is a Sprint 3 integration baseline focused on infrastructure, document processing, retrieval configuration, and documentation handoff. Main users are students (question answering), lecturers (document management), and admins (monitoring and governance). The system currently includes a runnable notebook PoC and Docker stack, while full production API/service integration remains in progress. Recent cleanup work normalized deliverables into canonical root packages (`docs`, `apps`, `fixtures`, `tests`, `data`) and converted `Team_Contributions` into ownership indexes.

## Tech Stack

- Frontend: Streamlit (`apps/streamlit/main.py`)
- Backend: Python + Flask integration wrapper (`apps/integration/backend/api.py`), notebook-driven RAG PoC
- Database: PostgreSQL (relational), ChromaDB (vector)
- LLM runtime: Ollama (`qwen3:14b` default)
- Embeddings / NLP: `sentence-transformers`, `langchain-text-splitters`, `PyMuPDF`
- Testing: `pytest` (`test/`), JSON/YAML validation scripts
- Build tools: Docker Compose
- Deployment target (current): local Docker development environment

## Repository Structure

- `apps/streamlit/` — Streamlit UI prototype entrypoint
- `apps/integration/` — Task 20 integration scripts and Flask adapter
- `db/` — PostgreSQL schema migrations and seed data
- `docs/` — architecture, governance, API, UI, meetings, and cleanup mapping docs
- `fixtures/` — static response fixtures for UI/integration fallback mode
- `materials/` — sample source material used by PoC
- `notebooks/` — end-to-end RAG proof-of-concept notebook
- `src/` — parser/chunker/embedder modules
- `test/` — automated tests (`pytest` path configured here)
- `tests/` — labeled query corpus assets
- `data/` — sample corpus manifest (raw samples stay external/gitignored)
- `.ai/` — persistent agent-readable codebase memory

## Development Commands

```bash
# Install dependencies (local)
python -m pip install -r requirements.txt

# Start local infrastructure stack
docker compose up -d

# GPU-enabled startup
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d

# Run tests
pytest

# Validate compose
docker compose -f docker-compose.yml config

# Validate integration backend syntax
python -m py_compile apps/integration/backend/api.py
```

## Coding Standards

- Python-first codebase; prefer clear module boundaries by responsibility (`src/document_processor`, `src/vector_retriever`, `apps/*`).
- Keep naming descriptive and snake_case for Python files/functions.
- Prefer small, targeted changes over broad refactors.
- Maintain existing JSON/YAML schema shape unless requirement explicitly changes.
- Keep documentation in Markdown, mapped to canonical `docs/` subdomains (`api`, `architecture`, `governance`, `ui`, `system_design`).
- Preserve fallback and course-isolation semantics (`course_id` scoping, clear ungrounded/fallback labeling).

## Testing Rules

- Unit tests: `pytest` (configured via `pytest.ini`, `testpaths = test`).
- For config/docs contract changes, run lightweight validation (JSON parse, YAML parse, syntax checks).
- Manual checks are important for Docker service health (`postgres`, `chromadb`, `ollama`) and integration startup scripts.
- Regression-sensitive areas: query response schema, API spec contracts, parser/chunker behavior, and integration path wiring.

## Safe Change Rules

When modifying this repository, agents must:

1. Read this file first.
2. Check `.ai/INDEX.md` before non-trivial work.
3. Prefer minimal, targeted changes.
4. Follow canonical root package structure.
5. Avoid adding dependencies unless clearly justified.
6. Update tests or docs when behavior changes.
7. Run relevant validation commands and report outcomes honestly.
8. Preserve branch and workflow constraints (no destructive git operations).

## Do Not Touch Without Explicit Instruction

- `docs/meetings/sprint3_sponsor_review.docx` and sponsor-review content timing.
- Database migration history under `db/migrations/` unless task explicitly requires migration updates.
- Public API response shapes defined in `docs/api/api_spec.yaml` without aligned doc/test updates.
- Large structural moves outside the established canonical package policy.
- Secrets or credential handling beyond `.env.example` placeholders.

## Definition of Done

A task is complete only when:

- Requested changes are implemented in the correct canonical path.
- Relevant validation commands have been run (or limitations clearly reported).
- Documentation and `.ai/` memory are updated if durable project knowledge changed.
- Risks, gaps, and deferred items are explicitly stated.
