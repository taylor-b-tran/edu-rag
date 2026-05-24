# Sprint 5 Runtime Notes — Demo Setup and Operation

**Task:** S5-T13
**Owner:** Tai Huynh
**Date:** 24 May 2026

> Operational reference for the Sprint 5 demo stack. Read top-to-bottom on a clean machine to reach the point where a CSIT321 query returns a grounded answer with citations.

---

## 1. Prerequisites

| Component | Minimum | Notes |
|---|---|---|
| Docker Desktop | 4.30+ (Engine 26+) | Tested with 29.4.2 on Windows 11 |
| RAM | 16 GB | 8 GB for Ollama + 4 GB for other services |
| Disk | 20 GB free | `qwen3:14b` is ~9 GB; `llama3.2` is ~2 GB; ChromaDB + Postgres ~1 GB |
| Python | 3.11 | For direct-run debugging only; Docker path does not need local Python |

---

## 2. First-time setup

```bash
# 1. Clone and check out develop
git clone https://github.com/taylor-b-tran/edu-rag.git
cd edu-rag
git checkout develop

# 2. Create environment file
cp .env.example .env
# Edit .env if you need to change ports or model

# 3. Build and start the core services
docker compose up -d --build postgres chromadb ollama

# 4. Pull a generation model (one of these)
docker exec edurag-ollama-1 ollama pull llama3.2     # 2 GB, fast inference
# OR
docker exec edurag-ollama-1 ollama pull qwen3:14b    # 9 GB, higher quality

# 5. Start API and Streamlit
docker compose up -d --build api streamlit

# 6. Ingest the seed corpus into ChromaDB
docker compose exec api python -m src.document_processor.ingest_corpus
```

After step 6, the Streamlit UI at <http://localhost:8501> can serve grounded CSIT321 queries.

---

## 3. Service map

| Service | Container name | Host port | Health endpoint | Depends on |
|---|---|---|---|---|
| `postgres` | `edurag-postgres-1` | 5432 | `pg_isready` | — |
| `chromadb` | `edurag-chromadb-1` | 8000 | `GET /api/v2/heartbeat` | — |
| `ollama` | `edurag-ollama-1` | 11434 | `GET /api/tags` | — |
| `api` | `edurag-api-1` | 5000 | `GET /api/health` | postgres, chromadb, ollama |
| `streamlit` | `edurag-streamlit-1` | 8501 | `GET /_stcore/health` | api |

Inside the Compose network, services use service names (e.g. `chromadb:8000`). The API reads `CHROMA_HOST=chromadb` and `OLLAMA_HOST=http://ollama:11434` to reach them.

---

## 4. Environment variables that matter

Defaults live in `.env.example`. Common overrides:

| Variable | Default | Effect |
|---|---|---|
| `DEFAULT_OLLAMA_MODEL` | `qwen3:14b` | Model used by `rag_pipeline.py` for generation |
| `OLLAMA_MODEL` | (unset → `llama3.2`) | Direct override read by `rag_pipeline.py:11` |
| `CHROMA_HOST` | (Compose: `chromadb`) | Empty string falls back to local `PersistentClient` against `./chroma_data` |
| `CHROMA_PORT` | `8000` | ChromaDB HTTP port |
| `CHROMA_PATH` | `./chroma_data` | Local persistence (untracked since PR #33) |
| `SIMILARITY_THRESHOLD` | `0.35` | Min similarity for a chunk to count as "good" |
| `DISTANCE_THRESHOLD` | `0.65` | Inverse of similarity for distance-based filters |
| `TOP_K` | `5` | Number of chunks returned by retriever |
| `PAEDIA_USE_FIXTURES` | `false` | Streamlit toggle to bypass live API and use fixtures |
| `EDURAG_OFFLINE_EMBEDDER` | (unset) | If set, uses FNV-1a hash embedder instead of SentenceTransformers (CI without network) |

---

## 5. Backend mode selection

The API picks its backend at first `/api/query` call (lazy init in `state.get_generator()`):

| Condition | Backend | `model_used` in response |
|---|---|---|
| `chromadb`, `sentence-transformers`, and seeded corpus all available | ChromaDB + Ollama | `qwen3:14b` / `llama3.2` |
| `VectorRetriever()` init raises any exception | `_FixtureGenerator` (PR #37) | `fixture` |
| `_call_ollama` hits `ConnectionError` | ChromaDB retrieval succeeds, fallback text in answer | model name, but `is_fallback=true` |

The fixture fallback path means **the API never returns 500 from a missing dependency**. It returns a working response with `model_used="fixture"` instead.

---

## 6. Demo command reference

### Daily restart (everything cached)

```bash
docker compose up -d
```

### Clean re-ingest

```bash
docker compose exec api python -m src.document_processor.ingest_corpus
```

### Smoke checks

```bash
curl http://localhost:5000/api/health        # API
curl http://localhost:8000/api/v2/heartbeat  # ChromaDB
curl http://localhost:11434/api/tags          # Ollama (lists pulled models)
curl http://localhost:8501/_stcore/health     # Streamlit
```

### Stop everything

```bash
docker compose down                 # keeps volumes (ChromaDB data, Ollama models)
docker compose down -v              # also drops volumes (full reset)
```

---

## 7. Direct-run fallback (Docker debugging)

If Docker stack is broken and you need to debug locally:

```bash
docker compose up -d postgres chromadb ollama       # infra only
python -m src.api.app                                # Flask on :5000
PAEDIA_API_URL=http://localhost:5000 PAEDIA_USE_FIXTURES=false \
  streamlit run apps/streamlit/main.py --server.port 8501
```

---

## 8. Common issues

| Symptom | Likely cause | Fix |
|---|---|---|
| `/api/query` returns `model_used="fixture"` unexpectedly | `chromadb` package missing or `chroma_data/` corrupt | `docker compose exec api pip show chromadb`; re-ingest corpus |
| Ollama returns "[Ollama not running]" | Model not pulled, or container down | `docker exec edurag-ollama-1 ollama list`; pull model |
| Streamlit shows empty citations | Seed corpus not ingested or similarity threshold too high | Run ingest step; lower `SIMILARITY_THRESHOLD` to `0.25` for sanity check |
| `docker compose up` says "address already in use" | Local Postgres/ChromaDB on host ports 5432/8000 | Stop local processes or change `*_PORT` in `.env` |
| Container name collision (`edurag-chromadb` already exists) | Old Sprint 3 containers from before the project name change | `docker rm -f edurag-chromadb edurag-ollama-cpu edurag-postgres` |
| ChromaDB version mismatch error | Volume from older Chroma image | `docker compose down -v` then `up -d --build` |

---

## 9. What is NOT covered here

- CI workflow internals → see [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) and [`docs/ci_test_validation_sprint5.md`](ci_test_validation_sprint5.md).
- Live retrieval benchmark procedure → see [`docs/rag_benchmark_sprint5.md`](rag_benchmark_sprint5.md).
- Sprint plan, acceptance criteria, scope → see [`docs/sprint_5_kickoff.md`](sprint_5_kickoff.md).
- Per-task status → see [`docs/sprint5_status_table.md`](sprint5_status_table.md).
- A3 implementation summary → see [`docs/sprint5_implementation_summary.md`](sprint5_implementation_summary.md).
