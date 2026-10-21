# Operations and troubleshooting

[Back to README](../README.md) · [Installation](../README_docker.md) · [Architecture](architecture.md)

Run commands from the repository root on the machine hosting your stack. Use the same CPU/GPU Compose files chosen during installation. For shared-instance access from another computer, use the [README access steps](../README.md#shared-access); administration commands below apply to the host.

Jump to [daily operations](#daily-operations), [troubleshooting](#troubleshooting) or the [demo checklist](#demo-checklist).

## Daily operations

### Start (everything cached)

```powershell
docker compose up -d                                                    # CPU mode
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d    # GPU mode
```

### Stop (keep data)

```powershell
docker compose down
```

Named volumes preserve uploaded documents, indexed vectors, accounts and conversation history when containers are removed without `-v`.

### Stop and wipe (full reset)

```powershell
docker compose down -v
```

This drops the `postgres_data`, `chromadb_data`, `ollama_data`, and `uploads_data` volumes. You will need to re-pull the Ollama model and re-seed the corpus.

### View live logs

```powershell
docker compose logs -f api streamlit          # follow both
docker compose logs --tail=100 api             # last 100 lines of api
docker compose logs ollama | Select-String error
```

### Restart a single service

```powershell
docker compose restart api                     # picks up code changes in src/
docker compose restart streamlit               # picks up changes in apps/streamlit
```

> Environment changes require `docker compose up -d --force-recreate <service>` with the same CPU/GPU Compose files used at startup. A restart alone keeps the old container environment.

> **No need to rebuild for code changes**: source is volume-mounted, so editing `src/` or `apps/` and running `docker compose restart api` (or `streamlit`) reloads it. Only run `docker compose build` after editing `requirements.txt` or `docker/Dockerfile.demo`.

### Rebuild after dependency change

```powershell
docker compose build api streamlit
# CPU deployment
docker compose up -d
# GPU deployment: use this instead of the preceding line
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
```

### Run tests inside the api container

```powershell
docker compose exec api pytest test -q                    # full suite (`pytest --collect-only -q` shows the count)
docker compose exec api pytest test/test_api.py -q        # API tests only
docker compose exec api pytest -k "test_query_returns" -q  # filtered
```

### Warm the LLM manually (cold container, before recording)

```powershell
curl.exe -X POST http://localhost:5000/api/warmup `
  -H "Authorization: Bearer <admin or lecturer access token>"
```

The API auto-warms on startup, but `/api/warmup` is available if VRAM gets evicted (Ollama unloads idle models after `OLLAMA_KEEP_ALIVE=5m`).

### Re-ingest the seed corpus (after dropping volumes or pulling new seed files)

```powershell
docker compose exec api python -m src.document_processor.ingest_corpus
```

> The seed corpus is 46 hand-written sample chunks for CSIT321, CSIT214, CSCI369 and MATH202. On a system that already holds real course material, running it adds those sample chunks to the same collection, so run it on a fresh volume only. Never add `--force`: it deletes and re-creates the whole collection, including everything lecturers have uploaded.

### Open a shell inside a container

```powershell
docker compose exec api bash                  # api container
docker compose exec postgres psql -U edurag   # Postgres CLI
docker compose exec ollama bash               # Ollama container
```

## Troubleshooting

### `docker compose up` says "address already in use"

A local process is holding one of the ports (5000, 5432, 8000, 8501, 11434).

```powershell
# Find what owns the port
Get-NetTCPConnection -LocalPort 5432 | Select-Object OwningProcess
Get-Process -Id <PID>
```

Either stop that process, or change the port mapping in `.env` (e.g. `POSTGRES_PORT=15432`).

### Container name collision

Inspect the existing containers and their Compose project before starting another copy:

```powershell
docker ps -a --filter name=edurag
docker compose ls
```

Use the intended checkout and project. Remove an obsolete container only after checking its mounts and confirming its data is preserved; do not remove a shared deployment to resolve a local naming collision.

---

### Answer generation is temporarily unavailable

An unavailable model, timeout, error response or empty model answer returns HTTP
503 without storing a chat message. The API logs the failure; students receive a
neutral retry message. Check API logs to distinguish model failures from a
retrieval dependency outage. The model may not be pulled, or Ollama may be unhealthy.

```powershell
docker compose ps ollama                       # status?
docker compose logs api --tail=50              # generation or retrieval failure?
docker compose exec ollama ollama list         # is the model present?
docker compose logs ollama --tail=50           # any errors?
```

Common fix:

```powershell
docker compose exec ollama ollama pull gemma4:12b   # or llama3.2
docker compose restart api
```

### Questions fail because the live pipeline did not start

Questions come back as `generation_unavailable` (HTTP 503) and `/api/health` reports a `mode` other than `chromadb`. ChromaDB or Ollama was unreachable at API startup. (Answers with `model_used: "fixture"` appear only when the API runs with `PAEDIA_USE_FIXTURES=true`.)

```powershell
# Check what backend the API selected
curl.exe http://localhost:5000/api/health
# Look for: "mode": "chromadb", "rag_available": true

# If mode is not_initialized, force the API to retry
docker compose restart api
# Then make any query — the API initialises the RAG pipeline lazily on first /api/query

# Inspect dependency/model errors before changing data
docker compose logs --tail=100 api chromadb ollama
```

### Upload flow broken

Lecturer uploads a PDF but it does not appear in the student's document list.

1. Confirm the lecturer selected a course they are enrolled in (CSIT321 or CSCI203 — see [Demo credentials](../README_docker.md#demo-credentials)).
2. Confirm the upload returned 202:
   ```powershell
   docker compose logs api --tail=50 | Select-String upload
   ```
3. Confirm indexing completed:
   ```powershell
   curl.exe http://localhost:5000/api/documents?course_id=CSIT321 `
     -H "Authorization: Bearer <lecturer access token>"
   ```
   Look for the file with `"status": "indexed"`. If stuck on `processing` for > 60 s, check `docker compose logs api --tail=200 | Select-String "Error in background indexing"`.
4. As student, confirm visibility:
   ```powershell
   curl.exe http://localhost:5000/api/documents?course_id=CSIT321 `
     -H "Authorization: Bearer <student access token>"
   ```

### First query takes 45 s

Model loading can add latency after startup or idle eviction. The API requests a background warm-up at startup; check its outcome and current model residency:

```powershell
curl.exe http://localhost:5000/api/health
# Expect warmup.status=ok (and warmup.generated=true)
```

If warm-up is still running, wait for it to finish. If it failed, inspect the API/Ollama logs. An administrator or lecturer can request a new warm-up:

```powershell
curl.exe -X POST http://localhost:5000/api/warmup `
  -H "Authorization: Bearer <admin or lecturer access token>"
docker compose exec ollama ollama ps
```

Warm-up may need repeating after Ollama unloads an idle model. `OLLAMA_KEEP_ALIVE` controls retention; changing it in `.env` requires recreating the affected services with the matching Compose files.

### ChromaDB version mismatch on startup

```
ValueError: You are using a deprecated configuration of Chroma
```

Check the pinned image and Python client versions, then inspect logs. An older data volume may need a supported migration or restoration from backup.

```powershell
docker compose images chromadb
docker compose exec api python -c "import chromadb; print(chromadb.__version__)"
docker compose logs --tail=100 chromadb api
```

Back up the vector-store volume before migration. `docker compose down -v` removes all project volumes, including accounts, uploads and downloaded models; it is not a routine version-mismatch fix.

---

### GPU shows 100% CPU under `ollama ps`

Check whether the GPU overlay is applied and the model fits available VRAM.

```powershell
# Confirm both compose files are loaded
docker compose -f docker-compose.yml -f docker-compose.gpu.yml config | Select-String -Pattern "gpu" -Context 2

# Apply the GPU overlay
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
docker compose exec ollama nvidia-smi   # GPU must be visible inside the container
```

If `nvidia-smi` inside the container fails, see [Verify your GPU setup (NVIDIA)](../README_docker.md#verify-your-gpu-setup-nvidia).

### "Account is suspended" in CI

Read the GitHub Actions error and repository/account status. Resolve the reported restriction before rerunning; do not assume it is a transient test failure:

```powershell
gh run rerun <run-id> --failed
```

### Streamlit page is blank or shows raw HTML

Hard-refresh the browser (Ctrl+Shift+R). Streamlit's hot-reload sometimes leaves stale cached JS after a code change. If the page is still broken:

```powershell
docker compose restart streamlit
```

### PowerShell can't run `start_stack.ps1`

```
File ... cannot be loaded because running scripts is disabled on this system.
```

If allowed by your organisation, set the policy for your own Windows user:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Then re-run the script.

## Demo checklist

Complete [setup](../README_docker.md#first-time-startup), provision the embedding cache, pull the selected model and upload course material (or seed a fresh standalone demo) before this check. Start with the matching CPU/GPU command in [Daily operations](#daily-operations).

For a locally installed stack, the readiness helper uses Python on the host and reads its password and port overrides from the shell, not automatically from `.env`:

```powershell
$env:PAEDIA_DEMO_STUDENT_PASSWORD = "<the student password from your .env>"
# If ports differ, also set API_PORT, APP_PORT, CHROMA_PORT and OLLAMA_PORT here.
python scripts/check_demo_ready.py
```

Inspect each result: the helper can exit successfully with a warm-up warning. It also sends a demo question and can create a conversation; use an appropriate demo account. Its service checks target local ports, so it is not a remote shared-instance test.

Then verify in the browser:

1. Open the shared host address or `http://localhost:8501` for your own stack.
2. Sign in as a student, select an enrolled course and ask a question supported by its indexed material. Check the answer, filename and available page/slide citation.
3. Sign in as an approved lecturer, select an authorised course and upload a small PDF. Follow `queued → processing → indexed`, or inspect an indexing error.
4. Ask a question that depends on that upload. Open the cited source and compare the answer with it.
5. Check a follow-up and an unsupported question. A fallback must be labelled; it is not evidence of a course-grounded answer.
