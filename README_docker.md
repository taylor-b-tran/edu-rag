# EduRAG Sprint 3 Docker Bundle

This Docker bundle is the Sprint 3 infrastructure baseline for the RAG backend
track. It keeps the four-service contract from the Sprint 3 plan in one place:

- `app`
- `postgres`
- `chromadb`
- `ollama`

The current `app` container is a bootstrap Python workspace container rather
than a finished web application image. That is intentional for Batch 2: it
gives the team a stable runtime target for the notebook, schema work, and later
backend code without forcing a premature Dockerfile design.

## Files

- `docker-compose.yml`: four-service local stack
- `docker-compose.gpu.yml`: optional NVIDIA GPU override for Ollama
- `.env.example`: example environment variables for local development

## Prerequisites

- Docker Desktop or Docker Engine
- Docker Compose v2+
- Python dependencies from `requirements.txt` if running the notebook outside
  the `app` container

## Quick Start

1. Copy the example environment file:

```powershell
Copy-Item .env.example .env
```

2. Start the stack:

```powershell
docker compose up -d
```

This default command is CPU-safe for teammates who do not have an NVIDIA Docker
runtime. On a machine with NVIDIA GPU support, start the stack with the GPU
override instead:

```powershell
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
```

3. Check service status:

```powershell
docker compose ps
```

4. Validate PostgreSQL health:

```powershell
docker compose exec postgres pg_isready -U $env:POSTGRES_USER -d $env:POSTGRES_DB
```

5. Check ChromaDB:

```powershell
Invoke-WebRequest http://localhost:8000/api/v2/heartbeat
```

6. Check Ollama:

```powershell
Invoke-WebRequest http://localhost:11434/api/tags
```

7. Enter the bootstrap app container:

```powershell
docker compose exec app sh
```

## Service Contract

### `app`

- Base image: `python:3.11-slim`
- Purpose in Batch 2: workspace container for notebook and backend work
- Host port reserved for future app-facing work: `8501`
- Workspace mount: the full project root is mounted at `/workspace`

### `postgres`

- Image: `postgres:16-alpine`
- Default database: `edurag`
- Purpose: users, sessions, audit logs, document metadata, and future indexing jobs

### `chromadb`

- Image: `chromadb/chroma@sha256:607103123fbd79794e3cd8029e16137031a464551e3a61df77191627a9d23c72`
- Purpose: vector storage for chunk embeddings and metadata

### `ollama`

- Image: `ollama/ollama@sha256:d3d553bdfbcc7f55dd5ddf42c4cbe3a927aa9bb1802710d35e94656ca5aea02b`
- Purpose: local LLM inference for the Sprint 3 PoC
- GPU access: the base Compose file is CPU-safe. Use
  `docker-compose.gpu.yml` when Docker Desktop exposes the NVIDIA runtime.

## Pull a Local Model

The Ollama container starts the runtime, but it does not automatically pull a
model. For the Sprint 3 test machine, `qwen3:14b` is the recommended default
because the hardware check confirmed an RTX 5080 with 16 GB VRAM.

```powershell
docker compose exec ollama ollama pull qwen3:14b
```

Fallback model for machines with less VRAM:

```powershell
docker compose exec ollama ollama pull qwen3:8b
```

## Default Connection Values

- PostgreSQL host inside Docker: `postgres`
- ChromaDB host inside Docker: `chromadb`
- Ollama base URL inside Docker: `http://ollama:11434`

## Known Scope Limitations for Batch 2

- No dedicated `Dockerfile` yet
- No notebook or backend application code wired in yet
- No automatic model pull on startup
- GPU access depends on Docker Desktop exposing the NVIDIA runtime correctly.
  Confirm with `docker compose exec ollama ollama ps` after generation; it
  should not show `100% CPU` for the selected model when the GPU override is
  active.

Those are expected to be handled in later Sprint 3 batches, not in this Docker
bundle.
