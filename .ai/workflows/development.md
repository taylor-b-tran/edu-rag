# Development Workflow

## Setup

```bash
# 1) Install Python dependencies locally
python -m pip install -r requirements.txt

# 2) Copy local environment template
Copy-Item .env.example .env
```

## Running Locally

```bash
# Start base stack
docker compose up -d

# Optional GPU stack
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d

# Enter app workspace container
docker compose exec app sh

# Run Streamlit prototype directly from repo
streamlit run apps/streamlit/main.py
```

## Environment Variables

Required variable names (see `.env.example`):

```txt
APP_ENV=
APP_PORT=
POSTGRES_DB=
POSTGRES_USER=
POSTGRES_PASSWORD=
POSTGRES_PORT=
CHROMA_PORT=
OLLAMA_PORT=
OLLAMA_KEEP_ALIVE=
DEFAULT_OLLAMA_MODEL=
OPENAI_API_KEY=
```

## Common Development Tasks

- Add/update API contract docs -> `docs/api/`
- Add/update architecture/governance docs -> `docs/architecture/`, `docs/governance/`
- Add UI behavior -> `apps/streamlit/main.py`
- Add integration behavior -> `apps/integration/backend/api.py`
- Add fixture responses -> `fixtures/sample_responses.json`
- Add corpus validation inputs -> `tests/test_queries.json`
