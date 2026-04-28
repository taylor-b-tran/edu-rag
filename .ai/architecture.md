# Architecture

## System Summary

EduRAG is a course-material-grounded assistant that combines document retrieval with local LLM generation. Sprint 3 currently delivers a working notebook pipeline plus a Dockerized infrastructure baseline and integration scaffolding. The system emphasizes course-scoped retrieval (`course_id` metadata filters), source-aware responses, and explicit fallback handling when grounding is weak.

## Main Modules

| Module | Path | Responsibility |
|---|---|---|
| Streamlit UI | `apps/streamlit/` | Student-facing prototype UI and response rendering |
| Integration adapter | `apps/integration/` | Flask adapter and startup scripts to bridge UI and backend behavior |
| Document processing | `src/document_processor/` | Chunking and parser-related logic |
| Retrieval/embedding | `src/vector_retriever/` | Embedding generation and retrieval scaffolding |
| Notebook PoC | `notebooks/` | End-to-end experiment path for Sprint 3 RAG validation |
| Data schemas | `db/` | PostgreSQL migration and seed definitions |
| Canonical docs | `docs/` | API/governance/architecture/UI/system-design documentation |
| Test assets | `test/`, `tests/` | Unit tests and labeled query corpus |

## Entry Points

- UI entry: `apps/streamlit/main.py`
- Integration backend entry: `apps/integration/backend/api.py`
- Integration startup: `apps/integration/start.sh`
- PoC entry: `notebooks/rag_poc.ipynb`
- Test entry: `pytest` from repository root (`pytest.ini` -> `test/`)

## Data Flow

1. User submits a question via Streamlit UI.
2. UI calls integration API endpoint (`/api/query`) when integration mode is used.
3. Backend attempts real pipeline call; if unavailable, returns fixture-backed responses.
4. Real flow uses course-scoped retrieval over ChromaDB and model generation via Ollama.
5. Response returns answer, source references, confidence/fallback metadata.
6. UI renders answer and source context.

## External Dependencies

- PostgreSQL (Docker service)
- ChromaDB (Docker service)
- Ollama runtime and model pulls
- Python libraries in `requirements.txt` (`PyMuPDF`, `sentence-transformers`, `langchain-text-splitters`, etc.)

## Risky Areas

- API response shape consistency between fixture mode and real pipeline mode.
- Canonical path policy drift (avoid reintroducing duplicate source files in `Team_Contributions`).
- Retrieval threshold and fallback semantics in docs vs runtime behavior.
- Integration scripts are shell-based and environment-sensitive.
- `test/` vs `tests/` split can confuse contributors if not documented.
