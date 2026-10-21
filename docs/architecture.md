# Architecture and development reference

[Back to README](../README.md) · [Installation](../README_docker.md) · [Operations](operations.md)

This reference covers the checked-in application structure and configuration. Deployment-specific availability and model residency must be checked on the host being used.

Jump to [services](#services-and-data-flow), [architecture](#architecture-overview), [repository layout](#repository-layout), [tech stack](#tech-stack-reference), [contributing](#contributing) or [implementation/tests](#implementation-and-tests).

## Services and data flow


When the setup is complete, your machine will be running a **five-service Docker stack**:

| Service | Purpose | Port | Container name |
|---|---|---|---|
| `streamlit` | Student / lecturer / admin web UI (Paedia) | `8501` | `edurag-streamlit-1` |
| `api` | Flask REST API (auth, query, upload, sessions) | `5000` | `edurag-api-1` |
| `chromadb` | Vector database — stores chunk embeddings | `8000` | `edurag-chromadb-1` |
| `ollama` | Local LLM inference (`gemma4:12b` by default) | `11434` | `edurag-ollama-1` |
| `postgres` | Relational DB — auth, sessions, upload metadata | `5432` | `edurag-postgres-1` |

The Streamlit UI talks to the Flask API. The API talks to ChromaDB (retrieval), Ollama (generation), and PostgreSQL (persistence). The default embedding model (`all-MiniLM-L6-v2`) and LLM (`gemma4:12b`) run locally. Initial setup downloads container images, Python packages and model weights; no cloud LLM API key is required for this configuration.

End-to-end demo flow:

1. Lecturer logs in, uploads a PDF.
2. API chunks it, generates 384-dimensional embeddings, writes to ChromaDB. Upload metadata is persisted to PostgreSQL so a `docker compose restart` does not lose it.
3. Student logs in, asks a question.
4. API retrieves course-scoped chunks, using top-k similarity search (default 5) with source-context ranking and expansion for supported PDF exercise or table references, then sends the context to Ollama.
5. Ollama generates an answer; the API returns it to Streamlit with validated source tags, filenames and available page or slide numbers. DOCX citations identify the file without a page number.



## Architecture overview

```
Student / Lecturer / Admin
          │
          ▼
   ┌──────────────────┐
   │   Streamlit UI   │   apps/streamlit/main.py
   │   (port 8501)    │   Light-theme overrides, native Enter-login component
   └─────────┬────────┘
             │  HTTP + bearer token
             ▼
   ┌─────────────────────┐      ┌─────────────────────────┐
   │   Flask REST API    │─────▶│   Document Processor    │
   │   src/api/          │      │   chunker · embedder    │
   │   (port 5000)       │      │   src/document_processor│
   └────┬────────┬───────┘      └────────────┬────────────┘
        │        │                           │ 384-dim embeddings
        │  background warm-up                │
        │        │                ┌──────────▼──────────┐
        │        ▼                │      ChromaDB        │
        │  ┌─────────────┐        │   (port 8000)       │
        │  │   Ollama    │        │  course_id-scoped   │
        │  │ gemma4:12b  │        │  vector store       │
        │  │ (port 11434)│        └──────────┬──────────┘
        │  └─────────────┘                   │ top-k chunks
        │                          ┌─────────▼─────────┐
        │                          │  Ollama generate  │
        │                          │  with citations   │
        │                          └───────────────────┘
        │
        ▼
   ┌─────────────────┐
   │   PostgreSQL    │   users, courses, enrolments, sessions, tokens,
   │   (port 5432)   │   feedback, settings, uploads and indexing jobs
   │                 │   (see README limitations).
   └─────────────────┘
```

**Data flow on query** (`POST /api/query`):

1. Auth: the opaque bearer token is checked against the PostgreSQL `access_tokens` table on every request, then a per-user limit of 10 requests a minute applies, and questions that are too vague get a 422.
2. Enrollment: `APIState.is_enrolled(user, course_id)` — UUID/code normalization via `resolve_course()`.
3. Retrieval query: rewrite follow-ups using recent session turns, then embed with `all-MiniLM-L6-v2` into a 384-dim vector. The original question remains the question answered.
4. Retrieval: `VectorRetriever.search(query, course_id, top_k)` against ChromaDB with metadata filter `where={"course_id": {"$eq": course_id}}`. `top_k` defaults to 5 and can be set per course in Tuning.
5. Ranking and threshold: lexical search and source-context ranking supplement similarity search. The default similarity threshold is 0.35 and can be overridden per course; explicit source-locator matches and lexical candidates can be retained below it. If no usable evidence remains, the answer carries the fallback label.
6. Confidence: the average similarity of the chunks used in the displayed references: High at 0.60 or above, Medium at 0.35 or above, otherwise Low. Refusals and directly quoted exercise statements are Low.
7. Prompt: chunks + question + system instruction → the configured LLM (`gemma4:12b` by default) via Ollama.
8. Response: answer text + the sources the model cited (renumbered to match `[S1]`, `[S2]` and showing the uploader's filename and available page/slide number; DOCX has no page) + confidence + latency. If the model fails, the API returns HTTP 503 and stores nothing.

**Data flow on upload** (`POST /api/upload`):

1. Auth + RBAC: lecturer/admin only.
2. Per-course enrollment check.
3. File written under a unique name, `<stem>-<8 hex digits><ext>`, in the `uploads_data` volume at `/workspace/data/uploads/`.
4. `APIState.queue_upload()` inserts rows into PostgreSQL `uploaded_documents` + `indexing_jobs`.
5. Background worker pool (a bounded `ThreadPoolExecutor`; `EDURAG_UPLOAD_THREAD_LIMIT`, default 3):
   - PDF/PPTX/DOCX parsing and chunking (default 1024 characters, zero overlap); PDF exercise context and table structure are preserved where recognised
   - embedder → 384-dim vectors
   - ChromaDB `upsert` with course_id metadata
   - PostgreSQL `update_job(status=completed)` + `update_document_status(status=indexed)`.


## Repository layout

```
edu-rag/
├── apps/
│   ├── streamlit/                # Streamlit UI prototype
│   │   ├── main.py               # UI entry point and role-specific pages
│   │   ├── api_client.py         # HTTP client to Flask API
│   │   └── components/login_form/  # native Streamlit Enter-login component
│   └── integration/
│       ├── backend/api.py        # dev-server entry only; the stack runs gunicorn src.api.wsgi:app
│       ├── start.sh / stop.sh    # legacy start scripts
│       └── logs/                 # gitignored
├── src/
│   ├── api/
│   │   ├── app.py                # Flask app factory
│   │   ├── state.py              # APIState: hot cache, PG hydration, warmup trigger
│   │   ├── db.py                 # PostgreSQL schema and persistence
│   │   ├── warmup.py             # Background Ollama warm-up
│   │   └── routes/               # auth, query, documents, sessions, health, courses, feedback, settings
│   ├── document_processor/
│   │   ├── chunker.py            # PDF/PPTX/DOCX → chunks
│   │   ├── ingest_corpus.py      # seed corpus loader
│   │   ├── offline_embedder.py   # FNV-1a fallback when sentence-transformers missing
│   │   ├── rag_pipeline.py       # VectorRetriever + LLMResponseGeneration
│   │   ├── source_context.py     # PDF exercise/section context and query locators
│   │   └── seed_documents.py     # in-repo sample chunks (four courses)
│   └── vector_retriever/embedder.py
├── db/
│   ├── migrations/               # design-time schema, not applied; the live schema is created by src/api/db.py
│   └── seed/                     # development seed data
├── docs/
│   ├── api/api_spec.yaml         # API specification; check routes for implementation details
│   ├── governance/               # privacy policy and ethics documents
│   ├── ui/                       # interface design documents
│   ├── architecture/             # design diagrams and earlier architecture snapshots
│   ├── rtm_a4.md                 # historical A4 requirements baseline
│   ├── operations.md             # daily operations, troubleshooting and demo checks
│   ├── architecture.md           # architecture and development reference
│   └── system_design/            # system design documents
├── fixtures/sample_responses.json    # demo users, demo responses
├── notebooks/rag_poc.ipynb           # original RAG PoC
├── scripts/
│   ├── start_stack.ps1 / .sh     # GPU-aware wrapper (Option A)
│   └── sprint5_integration_gate.py   # CI demo-readiness gate
├── test/                          # pytest suite (`pytest --collect-only -q` shows the count)
├── docker/Dockerfile.demo
├── docker-compose.yml             # base stack (CPU-safe)
├── docker-compose.gpu.yml         # GPU overlay (NVIDIA only)
├── requirements.txt               # runtime dependencies and pytest
├── requirements-dev.txt           # development/test dependencies (includes requirements.txt)
├── .env.example                   # copy to .env
├── README_docker.md               # installation and configuration
└── README.md                      # project entry point
```


## Tech stack reference

| Layer | Choice | Version | Why |
|---|---|---|---|
| Language | Python | 3.11 | Compatible with Docker base image, pinned for CI |
| UI | Streamlit | 1.51.0 | Fast iteration; native Python; no separate frontend build |
| API | Flask + Blueprints | 3.1.2 | Lightweight; team-familiar; easy testing |
| Text extraction | PyMuPDF (`fitz`) | 1.27.2.2 | Fast, reliable PDF text; better than pdfminer for layouts |
| Chunking | LangChain `RecursiveCharacterTextSplitter` | 1.1.0 | 1024-char chunks, 0 overlap (Sprint 3 benchmark default) |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` | 5.4.1 | 384-dimensional embeddings; requires a provisioned model cache |
| Vector store | ChromaDB | 1.5.8 | Metadata filtering, simple HTTP API, Docker-ready |
| Relational DB | PostgreSQL | 16-alpine | Standard; auth, tokens, courses, sessions, feedback and settings, with no audit log; psycopg3 with `dict_row` |
| Local LLM | Ollama + `gemma4:12b` (high tier), `qwen2.5:7b` (mid tier), or `llama3.2` (CPU) | Ollama image pinned by digest in Compose | Local generation; PowerShell model tiers; see [Automatic startup](../README_docker.md#automatic-startup) for the Bash default |
| Containerisation | Docker Compose | v2 | CPU + GPU overlay variants |
| Testing | Pytest + labelled query corpus | 8.3.3 | Unit, integration, retrieval evaluation |
| CI | GitHub Actions | — | Python tests + fixture validation + Compose validation + Sprint 5 integration gate |


## Contributing

### Branching workflow

```
feature/task-branch  →  develop  →  main
       ↑                    ↑
       └─ PR with CI green  └─ PR after develop has cumulative changes
```

- All changes merge through **pull requests into `develop`**. Direct pushes to `main` or `develop` are not permitted.
- Sprint-specific branches use `feature/sN-...` or `fix/sN-...` (e.g. `fix/s5-final-fix-wave`).
- PR template: short summary + test plan + link to relevant Sprint task (e.g. S5-T11).
- Agree branch scope and merge timing with the team lead.

### Local-development workflow

```powershell
# 1. Make sure your branch is up to date
git checkout develop
git pull
git checkout -b docs/readme-update

# 2. Run tests after each non-trivial change
docker compose exec api pytest test -q

# 3. Commit small, focused changes
git add <specific files>
git commit -m "docs: update setup and usage documentation"

# 4. Push and create PR via GitHub UI or gh
git push -u origin docs/readme-update
gh pr create --base develop --title "..." --body "..."

# 5. Wait for CI green before requesting review
gh pr checks <pr-number>
```

### Code conventions

- **Python**: 4-space indent, type hints where they help, no f-string in log messages (use `%s` placeholders for lazy formatting).
- **No global mutable state in routes** — go through `APIState`.
- **Tests**: every new route gets a happy-path test and at least one auth/permission test.
- **Commits**: keep changes focused and include the validation relevant to the change.

### CI gates before merge

| Check | What it does | How to debug locally |
|---|---|---|
| Python tests and fixture validation | `pytest -q`, JSON parsing checks, integration gate and PostgreSQL-specific tests | `docker compose exec api pytest test -q` |
| Docker Compose validation | `docker compose config` on both base + GPU overlay | `docker compose config --quiet`; `docker compose -f docker-compose.yml -f docker-compose.gpu.yml config --quiet` |
| Demo stack smoke test | Spins up full stack on the runner, hits all health endpoints | Compose up locally and hit each `/health` route by hand |

The Docker Demo Readiness workflow is path-filtered and does not run automatically for a README-only change. Check which jobs actually ran before reporting CI results; resolve infrastructure failures before rerunning jobs.

## Implementation and tests

| Area | Source | Automated checks |
|---|---|---|
| Authentication and lecturer approval | [`src/api/routes/auth.py`](../src/api/routes/auth.py) | [`test/test_login_email_case.py`](../test/test_login_email_case.py), [`test/test_lecturer_approval.py`](../test/test_lecturer_approval.py) |
| Course/document access | [`src/api/routes/documents.py`](../src/api/routes/documents.py) | [`test/test_document_course_boundaries.py`](../test/test_document_course_boundaries.py), [`test/test_document_file_access.py`](../test/test_document_file_access.py) |
| Parsing and source context | [`src/document_processor/chunker.py`](../src/document_processor/chunker.py), [`src/document_processor/source_context.py`](../src/document_processor/source_context.py) | [`test/test_source_context.py`](../test/test_source_context.py) |
| Retrieval and answer generation | [`src/document_processor/rag_pipeline.py`](../src/document_processor/rag_pipeline.py) | [`test/test_retrieval_quality.py`](../test/test_retrieval_quality.py), [`test/test_citation_numbering.py`](../test/test_citation_numbering.py) |
| DOCX citation handling | [`src/api/routes/query.py`](../src/api/routes/query.py) | [`test/test_docx_citation_pages.py`](../test/test_docx_citation_pages.py) |
| Conversation persistence | [`src/api/routes/sessions.py`](../src/api/routes/sessions.py), [`src/api/db.py`](../src/api/db.py) | [`test/test_sessions_across_workers.py`](../test/test_sessions_across_workers.py) |
| Build and CI | [`docker-compose.yml`](../docker-compose.yml), [CI workflow](../.github/workflows/ci.yml) | `docker compose exec api pytest test -q` |

These links identify implementation and tests; they do not state that the checks passed on a particular deployment. Earlier architecture documents and benchmarks describe their recorded revision, model and corpus.

## Evaluation context

The [Sprint 9 benchmark](retrieval_benchmark_sprint9.md) records Precision@5 of 0.2 against its stated ceiling of 0.22, Recall@10 of 1.0 and MRR of 0.925. Those results predate the current source-context and lexical ranking changes. The [earlier threshold study](retrieval_tuning_sprint9.md) does not establish performance on a different corpus or revision; re-evaluate after changing the corpus, model or retrieval behaviour.
