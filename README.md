# EduRAG

EduRAG is a CSIT321 Project 37 course assistant for Group 19. The project uses
retrieval-augmented generation to answer student questions from course
materials, with answers grounded in indexed documents rather than general chat
alone.

## Project Details

| Item | Value |
|---|---|
| Subject | CSIT321 Annual Session 2026 |
| Campus | Liverpool Campus (SWS) |
| Group | Group 19 |
| Supervisor / Sponsor | Prof. Jun Yan |

## Team

| Name | Role |
|---|---|
| Thanh Binh Tran | Team Lead |
| Tai Huynh | Team Member |
| Tung Phuong Anh Huynh | Team Member |
| Kahavidanage Namaratne | Team Member |
| Thi Hong Ngoc Nguyen | Team Member |
| Anmoldeep Singh | Team Member |

## Current Sprint 3 Baseline

The current `develop` branch includes the Sprint 3 RAG/backend checkpoint:

- Docker Compose local stack with `app`, `postgres`, `chromadb`, and `ollama`
- PostgreSQL schema and development seed data
- ChromaDB vector-store setup for chunk embeddings
- Ollama model selection and prompt strategy notes
- RAG configuration benchmark and retrieval edge-case notes
- Executed RAG proof-of-concept notebook using one sample PDF
- Internal handoff notes for Sprint 4 planning

The `app` service is still a bootstrap workspace container. It is not a finished
production API or web application yet.

## Repository Structure

```text
.
|-- db/
|   |-- migrations/              # PostgreSQL schema
|   `-- seed/                    # Development seed data
|-- docs/
|   |-- meetings/                # Sprint checkpoint notes
|   |-- ollama_model_selection.md
|   |-- prompt_strategy.md
|   `-- rag_config.md
|-- materials/                   # Sample course material for the PoC
|-- notebooks/                   # RAG proof-of-concept notebook
|-- scripts/                     # Local helper scripts
|-- docker-compose.yml
|-- docker-compose.gpu.yml
|-- README_docker.md
|-- requirements.txt
`-- SPRINT_BRANCH_WORKFLOW.md
```

## Tech Stack

| Layer | Current Sprint 3 Choice |
|---|---|
| Language | Python |
| Notebook / PoC | Jupyter notebook |
| Text splitting | LangChain `RecursiveCharacterTextSplitter` |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector database | ChromaDB |
| Relational database | PostgreSQL |
| Local LLM runtime | Ollama |
| Default local model | `qwen3:14b` |
| Prototype UI target | Streamlit |

## Quick Start

Copy the example environment file:

```powershell
Copy-Item .env.example .env
```

Start the base local stack:

```powershell
docker compose up -d
```

For an NVIDIA GPU environment, use the GPU override:

```powershell
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
```

Pull the default Ollama model:

```powershell
docker compose exec ollama ollama pull qwen3:14b
```

Install Python dependencies if running the notebook outside Docker:

```powershell
python -m pip install -r requirements.txt
```

Open the proof-of-concept notebook:

```text
notebooks/rag_poc.ipynb
```

See `README_docker.md` for service checks, connection values, and known Docker
scope limitations.

## Sprint 3 RAG Defaults

| Setting | Value |
|---|---|
| Chunk size | 1024 characters |
| Chunk overlap | 0 characters |
| Retrieval top-k | 5 |
| Fallback threshold | cosine distance `0.65` |
| Course isolation | `course_id` metadata filter |

These defaults are Sprint 3 checkpoint values. They should be rechecked once the
larger labelled query set is available.

## Git Workflow

The team uses:

- `main` for release points
- `develop` for team integration
- short-lived task branches for normal work

Normal merge direction:

```text
task branch -> develop -> main
```

Do not push directly to `main` or `develop`. Open a pull request into `develop`
for feature, docs, test, fix, and chore work. See `SPRINT_BRANCH_WORKFLOW.md`
for the full team workflow.

## Useful Commands

Validate the base Compose file:

```powershell
docker compose -f docker-compose.yml config
```

Validate the GPU overlay:

```powershell
docker compose -f docker-compose.yml -f docker-compose.gpu.yml config
```

Check running services:

```powershell
docker compose ps
```

## Current Limitations

- The backend API wrapper is not implemented yet.
- The Streamlit UI is not wired into the RAG pipeline yet.
- The benchmark uses one sample PDF and a small provisional query set.
- PPTX/DOCX ingestion, hybrid retrieval, reranking, and full evaluation remain
  future work.

## License

Course project repository for CSIT321. Licensing and reuse terms are not yet
finalised.
