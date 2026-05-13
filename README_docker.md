# EduRAG Docker Demo Bundle

This Docker bundle is the Sprint 5 local demo baseline. It keeps the core
infrastructure services and the runnable demo application services in one
Compose contract:

- `api`
- `streamlit`
- `postgres`
- `chromadb`
- `ollama`

The older `app` container is retained only as a lightweight tools/debug profile.
The demo path now uses the explicit `api` and `streamlit` services.

## Files

- `docker-compose.yml`: Sprint 5 demo stack with `api`, `streamlit`, `postgres`,
  `chromadb`, `ollama`, and the optional `tools` profile
- `docker-compose.gpu.yml`: optional NVIDIA GPU override for Ollama
- `docker/Dockerfile.demo`: shared Python image for the API and Streamlit demo
- `.env.example`: example environment variables for local development
- `.github/workflows/docker-demo.yml`: Sprint 5 demo-readiness smoke test for
  the Compose infrastructure

## Prerequisites

- Docker Desktop or Docker Engine
- Docker Compose v2+
- Python dependencies from `requirements.txt` if running notebooks or services
  outside Docker

## Quick Start

1. Copy the example environment file:

```powershell
Copy-Item .env.example .env
```

2. Build and start the demo stack:

```powershell
docker compose up -d --build
```

This default command is CPU-safe for teammates who do not have an NVIDIA Docker
runtime. On a machine with NVIDIA GPU support, start the stack with the GPU
override instead:

```powershell
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
```

3. Check service status:

```powershell
docker compose ps
```

Compose uses project-scoped container names instead of fixed global container
names. This keeps the Sprint 5 stack from colliding with older stopped local
containers from previous sprint experiments.

4. Validate PostgreSQL health:

```powershell
docker compose exec postgres pg_isready -U edurag -d edurag
```

5. Check ChromaDB:

```powershell
Invoke-WebRequest http://localhost:8000/api/v2/heartbeat
```

6. Check Ollama:

```powershell
Invoke-WebRequest http://localhost:11434/api/tags
```

7. Check the Flask API:

```powershell
Invoke-WebRequest http://localhost:5000/api/health
```

8. Check the Streamlit UI:

```powershell
Invoke-WebRequest http://localhost:8501/_stcore/health
```

9. Enter the lightweight tools container if needed:

```powershell
docker compose --profile tools run --rm app sh
```

## Service Contract

### `api`

- Image: built from `docker/Dockerfile.demo`
- Purpose: Flask API service from `apps/integration/backend/api.py`
- Host port: `5000` by default, configurable through `API_PORT`
- Health check: `/api/health`

### `streamlit`

- Image: built from `docker/Dockerfile.demo`
- Purpose: student/lecturer/admin UI from `apps/streamlit/main.py`
- Host port: `8501` by default, configurable through `APP_PORT`
- API target inside Docker: `http://api:5000`

### `postgres`

- Image: `postgres:16-alpine`
- Default database: `edurag`
- Purpose: users, sessions, audit logs, document metadata, and future indexing jobs

### `chromadb`

- Image: `chromadb/chroma@sha256:607103123fbd79794e3cd8029e16137031a464551e3a61df77191627a9d23c72`
- Purpose: vector storage for chunk embeddings and metadata

### `ollama`

- Image: `ollama/ollama@sha256:d3d553bdfbcc7f55dd5ddf42c4cbe3a927aa9bb1802710d35e94656ca5aea02b`
- Purpose: local LLM inference for the Sprint 5 demo path
- GPU access: the base Compose file is CPU-safe. Use
  `docker-compose.gpu.yml` when Docker Desktop exposes the NVIDIA runtime.

### `app`

- Profile: `tools`
- Purpose: lightweight Python shell for quick container checks
- Not part of the main demo path

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
- Flask API inside Docker: `http://api:5000`
- Streamlit host URL: `http://localhost:8501`

## Known Scope Limitations

- No automatic model pull on startup
- The current Flask query route can still fall back to fixture mode until the
  live ChromaDB plus Ollama path is fully wired behind `/api/query`
- GPU access depends on Docker Desktop exposing the NVIDIA runtime correctly.
  Confirm with `docker compose exec ollama ollama ps` after generation; it
  should not show `100% CPU` for the selected model when the GPU override is
  active.

## Sprint 5 CI/CD Note

Sprint 5 starts using GitHub Actions as a demo-readiness gate:

- `.github/workflows/ci.yml` runs Python tests, compile checks, JSON validation,
  Docker Compose config validation, and a Sprint 5 demo service contract check
  on PRs and pushes to `develop` or `main`.
- `.github/workflows/docker-demo.yml` can be run manually before demo rehearsal
  and smoke-tests PostgreSQL, ChromaDB, Ollama service readiness, Flask API
  health, Streamlit health, and the tools container.

This is not a public deployment pipeline yet. It is a controlled local-demo
pipeline so the team can prove the infrastructure layer is reproducible before
recording Assessment 3 evidence.
