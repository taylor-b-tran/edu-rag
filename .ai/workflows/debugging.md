# Debugging Workflow

## Debugging Rules

1. Reproduce the issue in the smallest path possible.
2. Identify failing layer: UI, integration adapter, notebook pipeline, database, vector store, or model runtime.
3. Check logs and command output before modifying code.
4. Make minimal targeted fixes.
5. Re-run the failing command/scenario.

## Common Failure Areas

- Missing or wrong `PAEDIA_BACKEND_URL` when running Streamlit UI.
- Fixture path mismatches causing empty/mock-only responses.
- Docker services not healthy (`postgres`, `chromadb`, `ollama`).
- Model unavailable in Ollama because pull step was skipped.
- Response shape drift between fixture mode and real pipeline mode.
- Branch workflow confusion when local branch tracking is stale.

## Quick Triage Commands

```bash
# Service status
docker compose ps

# Backend health
Invoke-WebRequest http://localhost:5000/api/health

# Ollama model list
Invoke-WebRequest http://localhost:11434/api/tags

# Unit tests
pytest
```
