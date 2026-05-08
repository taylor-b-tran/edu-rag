# EduRAG

> A course-aware AI assistant that answers student questions from lecturer-provided materials — grounded in documents, not general web knowledge.

EduRAG is a six-person team project that applies **Retrieval-Augmented Generation (RAG)** to higher education. Students ask questions in natural language; the system retrieves the most relevant passages from indexed course documents and generates an answer with inline source citations. Off-topic or unsupported questions are explicitly labelled as fallback responses rather than presented as course-authoritative answers.

---

## Why This Exists

University students routinely spend hours searching PDFs, slides, and lecture notes to find an answer that takes a few sentences to state. At the same time, generic AI tools like ChatGPT have no visibility into course-specific content and can produce confident but incorrect answers drawn from their general training data.

EduRAG addresses both problems:

- **Lecturers** upload course materials once. The system indexes them automatically.
- **Students** ask questions in plain language and receive answers grounded in those materials, with page-level citations they can verify.
- **Admins** monitor usage, manage access, and inspect an audit log of document events.

The answer generation is always scoped to the enrolled course. Cross-course data leakage is a first-class design constraint, not an afterthought.

---

## Technical Highlights

These are the engineering skills and practices demonstrated by this project:

| Area | What was built |
|---|---|
| **RAG pipeline** | End-to-end: PDF extraction → chunking → embedding → vector retrieval → LLM generation with citation formatting and fallback detection |
| **Vector search** | ChromaDB with `course_id` metadata filtering to enforce retrieval isolation per course |
| **Relational data model** | PostgreSQL schema covering users, roles, courses, documents, indexing jobs, session history, and an immutable audit log |
| **Local LLM inference** | Ollama running `qwen3:14b` — fully self-hosted, no external API calls required in development |
| **API design** | Full OpenAPI 3.0 specification + Flask implementation (JWT auth, role-scoped endpoints, async indexing jobs, session history, admin monitoring) |
| **Containerised stack** | Docker Compose with CPU and GPU override variants; service-health dependency ordering |
| **Prompt engineering** | Evidence-cited safety-first prompt with confidence labelling, fallback phrasing, and injection-resistance notes |
| **Evaluation assets** | Retrieval benchmark (chunk size, overlap, top-k, distance threshold) + 31-question labelled test corpus covering factual, reasoning, off-topic, and ambiguous cases |
| **Privacy & ethics** | Explicit privacy policy, ethics review document, role-based access control model, data minimisation by category, and audit event trail |
| **Team workflow** | Git branching strategy (main / develop / task branches), PR-only merges, per-sprint deliverable ownership tracked per member |

---

## System Architecture

```
Student / Lecturer / Admin
          │
          ▼
  ┌─────────────────┐
  │  Streamlit UI   │  (Sprint 3: wireframes + state model; Sprint 4: connected)
  └────────┬────────┘
           │  HTTP
           ▼
  ┌─────────────────┐      ┌──────────────────────┐
  │  Web/API Layer  │─────▶│  Document Processor  │
  │  Flask (src/api)│      │  chunker · embedder  │
  └────────┬────────┘      └──────────┬───────────┘
           │                          │ embeddings
     ┌─────┴──────┐           ┌───────▼──────────┐
     │ PostgreSQL │           │    ChromaDB       │
     │ users      │           │  vector store     │
     │ documents  │           │  course-scoped    │
     │ sessions   │           └───────┬───────────┘
     │ audit log  │                   │ retrieved chunks
     └────────────┘           ┌───────▼───────────┐
                              │  Ollama (local)   │
                              │  qwen3:14b        │
                              │  grounded answer  │
                              └───────────────────┘
```

---

## Current Status

| Sprint | Status | Key Outcomes |
|---|---|---|
| Sprint 1–2 | Complete | Architecture decisions, module interface design, Assessment 2 documentation |
| Sprint 3 | Complete | Working RAG PoC notebook, Docker stack, PostgreSQL schema, API specification, prompt strategy, retrieval benchmark, privacy/ethics review, UI wireframes, test query corpus |
| Sprint 4 | Complete | Flask API with JWT auth, role-based access control, course-scoped query enforcement, Streamlit UI connected to live API, document upload/indexing flow, PPTX/DOCX parser validation |

### What is working now

- Docker Compose stack: PostgreSQL, ChromaDB, and Ollama run locally with health checks
- PostgreSQL schema applied with development seed data (users, courses, documents, sessions, audit events)
- RAG PoC notebook executes the full ingestion-to-answer pipeline against a real PDF
- `sentence-transformers/all-MiniLM-L6-v2` embeddings stored in ChromaDB with `course_id` metadata
- Prompt strategy and RAG configuration benchmark frozen for Sprint 3 integration baseline
- Full OpenAPI 3.0 specification covering auth, query, upload, indexing, sessions, and admin routes
- **Flask REST API** (`src/api/`) with Blueprint-based routing: auth, query, documents, sessions, health
- **JWT authentication** enforced on all protected endpoints; wrong-password login returns 401
- **Role-based access control**: lecturer/admin only for upload/delete; students blocked with 403
- **Course-scoped query enforcement**: students cannot query courses they are not enrolled in
- **Streamlit UI** connected to live Flask API via `apps/integration/start.sh`
- **Document upload flow** wired end-to-end: UI → `api_client.upload_document()` → Flask → indexing job queue
- PPTX and DOCX parser paths validated with extended test suite (104 tests passing)

### Current report and planning artifacts

- Assessment 2 report: `docs/reports/Assessment_2_Group19.docx`
- Sprint 4 plan: `docs/meetings/Sprint4_EduRAG_Group19.docx`

---

## Tech Stack

| Layer | Choice | Notes |
|---|---|---|
| Language | Python | Across all modules |
| UI prototype | Streamlit | Student-facing Q&A + admin dashboard |
| API layer | Flask + Blueprints | `src/api/` — JWT auth, role-scoped routes, fixture-backed Sprint 4 prototype |
| Text extraction | PyMuPDF (`fitz`) | PDF-first; PPTX/DOCX in progress |
| Text splitting | LangChain `RecursiveCharacterTextSplitter` | 1024-char chunks, 0 overlap (Sprint 3 benchmark default) |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` | 384-dimensional, fully local |
| Vector database | ChromaDB | Metadata-filtered by `course_id` |
| Relational database | PostgreSQL | Users, roles, docs, sessions, audit log |
| Local LLM | Ollama + `qwen3:14b` | GPU-optional; no external API required |
| Containerisation | Docker Compose | CPU + GPU overlay variants |
| Testing | Pytest + labelled query corpus | Unit, integration, and retrieval evaluation assets |

---

## Team

| Name | Module ownership |
|---|---|
| Thanh Binh Tran | Team Lead — RAG pipeline, prompt strategy, retrieval benchmark, system integration |
| Tai Huynh | Module 4 — API specification, privacy policy, ethics review, Sprint 4 kickoff |
| Tung Phuong Anh Huynh | Testing — test query corpus, corpus manifest, evaluation methodology |
| Kahavidanage Namaratne | Data — ERD, DFD, risk register, storage sizing, PostgreSQL schema |
| Thi Hong Ngoc Nguyen | Document processing — retrieval edge cases, RAG configuration contribution |
| Anmoldeep Singh | UI — Streamlit wireframes, design system, UI state model |

---

## Project Context

| Item | Value |
|---|---|
| Subject | CSIT321 Annual Session 2026 — Project 37 |
| Campus | University of Wollongong, Liverpool Campus (SWS) |
| Group | Group 19 |
| Supervisor | Prof. Jun Yan |

This is an assessed final-year project but the engineering work — system design, API specification, retrieval tuning, privacy modelling, and sprint delivery — reflects professional software development practice rather than tutorial exercises.

---

## Quick Start

Copy the example environment file:

```bash
cp .env.example .env
```

Start the local stack:

```bash
docker compose up -d
```

For an NVIDIA GPU environment:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
```

Pull the default LLM:

```bash
docker compose exec ollama ollama pull qwen3:14b
```

Install Python dependencies (if running the notebook outside Docker):

```bash
pip install -r requirements.txt
```

Open the RAG proof-of-concept notebook:

```
notebooks/rag_poc.ipynb
```

See [`README_docker.md`](README_docker.md) for service connection values, health checks, and known Docker scope notes.

---

## Sprint 3 RAG Defaults

| Setting | Value | Rationale |
|---|---|---|
| Chunk size | 1024 characters | Best in-scope / out-of-scope distance separation in the Sprint 3 benchmark |
| Chunk overlap | 0 characters | Overlap did not improve coverage on the benchmark PDF |
| Retrieval top-k | 5 | Sufficient context for the LLM without overloading the prompt |
| Fallback threshold | cosine distance 0.65 | Separates weakly-grounded queries from supported ones |
| Course isolation | `course_id` metadata filter | Non-negotiable; prevents cross-course retrieval leakage |

These are Sprint 3 integration defaults. They will be revalidated against the full 31-question labelled corpus in Sprint 4.

---

## Repository Layout

```
.
├── apps/streamlit/          # Streamlit UI prototype
├── db/
│   ├── migrations/          # PostgreSQL schema
│   └── seed/                # Development seed data
├── docs/
│   ├── api/                 # OpenAPI 3.0 spec (api_spec.yaml)
│   ├── governance/          # Privacy policy, ethics review
│   ├── meetings/            # Sprint checkpoint notes, Sprint 4 kickoff
│   ├── system_design/       # System design document v2
│   ├── ui/                  # Wireframes, design system, UI state
│   ├── ollama_model_selection.md
│   ├── prompt_strategy.md
│   └── rag_config.md
├── materials/               # Sample course PDF for the PoC
├── notebooks/               # rag_poc.ipynb — executed RAG pipeline
├── src/
│   ├── api/                 # Flask REST API (Sprint 4)
│   │   ├── app.py           # App factory
│   │   ├── state.py         # In-memory state + auth helpers
│   │   └── routes/          # auth, query, documents, sessions, health
│   ├── document_processor/  # chunker.py (PDF, PPTX, DOCX)
│   └── vector_retriever/    # embedder.py
├── test/                    # Pytest: API auth, chunker, PPTX/DOCX integration
├── tests/                   # Pytest assets and test query corpus
├── docker-compose.yml
├── docker-compose.gpu.yml
└── SPRINT_BRANCH_WORKFLOW.md
```

---

## Git Workflow

Branches follow: `task branch → develop → main`

All changes merge through pull requests into `develop`. Direct pushes to `main` or `develop` are not permitted. See [`SPRINT_BRANCH_WORKFLOW.md`](SPRINT_BRANCH_WORKFLOW.md) for the full team convention.

---

## Known Limitations

- The Flask API serves fixture-backed responses in Sprint 4; the live RAG pipeline (`rag_module.py`) is not yet wired into the API layer.
- The retrieval benchmark used a provisional query set; full 31-question corpus validation is pending live pipeline integration.
- Docker Compose `app` service runs a placeholder; Flask and Streamlit are launched via `apps/integration/start.sh` for the connected demo.
- Session data and uploaded document records are in-memory only; they reset on Flask restart.

---

## License

University of Wollongong course project repository. Licensing and reuse terms are not yet finalised.
