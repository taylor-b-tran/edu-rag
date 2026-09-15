# EduRAG / Paedia

> A course-aware AI assistant that answers student questions from lecturer-uploaded materials — grounded in documents, not general web knowledge.

EduRAG (product name: **Paedia**) is a six-person team project applying **Retrieval-Augmented Generation (RAG)** to higher education. Students ask questions in natural language; the system retrieves the most relevant passages from indexed course documents and generates an answer with inline source citations. Off-topic or unsupported questions are explicitly labelled as fallback responses rather than presented as course-authoritative answers.

This README is the **single entry point** for new team members.  Team members and testers should use the shared Paedia instance through Tailscale. The local Docker setup instructions below are intended for development, host administration, and standalone deployments.

---
## Access the Shared Paedia Instance
Paedia is currently deployed on one shared GPU host. Team members and testers do not need to run the Docker stack locally to use the system.

Access to the shared instance is provided through Tailscale. Each person must be individually given access to the Paedia host before they can connect.

## Requirements

Before accessing Paedia:
1. Install Tailscale on your system.
2. Sign in to Tailscale using the account that has been given access to Paedia host.
3. Make sure the shared Paedia host appears in Tailscale.
4. Make sure Tailscale is connected.

## Connecting to Paedia
1. Open Tailscale and confirm that you are connected.
2. Open a web browser such as Microsoft Edge or Google Chrome.
3. Enter the shared Paedia host address and Streamlit port in the browser address bar (Host_Address:Port)
4. The Paedia login page should appear
5. Sign in with an existing account or create a new account.

The Paedia web interface uses port '8501'.

The shared deployment is accessed through the Tailscale host address, not 'localhost'. References to 'localhost' later in this README are for development or administration performed directly on the host machine

### Troubleshooting Shared Access

If Paedia does not load:

- Check that Tailscale is running and connected.
- Check that the Paedia host has been shared with your Tailscale account.
- Check that the shared host appears online in Tailscale.
- Check that you are using the correct Tailscale host address and port '8501'
- Check with the team member managing the GPU host that the Paedia Docker services are running.

If Tailscale is connected but the browser connection times out, the share or Paedia service may be unavailable.

---

## Table of Contents

1. [What you are about to run](#1-what-you-are-about-to-run)
2. [System requirements](#2-system-requirements)
3. [Install the prerequisites](#3-install-the-prerequisites)
4. [Verify your GPU setup (NVIDIA)](#4-verify-your-gpu-setup-nvidia)
5. [Clone and configure](#5-clone-and-configure)
6. [First-time startup](#6-first-time-startup)
7. [Pull the LLM model](#7-pull-the-llm-model)
8. [Seed the course corpus](#8-seed-the-course-corpus)
9. [Verify the stack works](#9-verify-the-stack-works)
10. [Demo credentials](#10-demo-credentials)
11. [Daily operations](#11-daily-operations)
12. [Troubleshooting](#12-troubleshooting)
13. [Architecture overview](#13-architecture-overview)
14. [Repository layout](#14-repository-layout)
15. [Tech stack reference](#15-tech-stack-reference)
16. [Contributing](#16-contributing)
17. [Team](#17-team)
18. [Project context](#18-project-context)
19. [For the Marker](#19-for-the-marker)

---

## 1. What you are about to run

When the setup is complete, your machine will be running a **five-service Docker stack**:

| Service | Purpose | Port | Container name |
|---|---|---|---|
| `streamlit` | Student / lecturer / admin web UI (Paedia) | `8501` | `edurag-streamlit-1` |
| `api` | Flask REST API (auth, query, upload, sessions) | `5000` | `edurag-api-1` |
| `chromadb` | Vector database — stores chunk embeddings | `8000` | `edurag-chromadb-1` |
| `ollama` | Local LLM inference (`qwen3:14b` or `llama3.2`) | `11434` | `edurag-ollama-1` |
| `postgres` | Relational DB — auth, sessions, upload metadata | `5432` | `edurag-postgres-1` |

The Streamlit UI talks to the Flask API. The API talks to ChromaDB (retrieval), Ollama (generation), and PostgreSQL (persistence). Nothing leaves your machine — both the embedding model (`all-MiniLM-L6-v2`) and the LLM (`qwen3:14b`) run locally.

End-to-end demo flow:

1. Lecturer logs in, uploads a PDF.
2. API chunks it, generates 384-dimensional embeddings, writes to ChromaDB. Upload metadata is persisted to PostgreSQL so a `docker compose restart` does not lose it.
3. Student logs in, asks a question.
4. API retrieves top-5 most similar chunks (course-scoped via `course_id` metadata filter), formats them into a prompt, sends to Ollama.
5. Ollama returns a grounded answer; the API returns it to Streamlit with file + page citations.

---

## 2. System requirements

| Resource | Minimum | Recommended | Notes |
|---|---|---|---|
| **OS** | Windows 11 23H2 | Windows 11 24H2 | Tested on Windows 11 Pro 26200. Linux/macOS work but this guide is PowerShell-first |
| **CPU** | 4 cores | 8 cores | Inference is mostly GPU, but PDF chunking + embeddings use CPU |
| **RAM** | 16 GB | 32 GB | Ollama needs ~10 GB for `qwen3:14b` working set, leave 6 GB for other services |
| **Disk** | 25 GB free | 40 GB free | `qwen3:14b` ~9 GB, `qwen2.5:7b` ~4.7 GB, `llama3.2` ~2 GB, Docker images ~6 GB, ChromaDB+Postgres ~1 GB, source ~500 MB, model cache ~5 GB |
| **GPU** | None (CPU-only works, slow) | NVIDIA RTX with **≥ 12 GB VRAM** | Three supported tiers — see below. RTX 5080 (16 GB) is the dev host |
| **Network** | Once for image pulls + model download | — | After first setup the stack runs fully offline |

**Three supported tiers**, auto-detected by `scripts/start_stack.ps1` — you do not need to pick one manually:

| Tier | Hardware | Model | Measured speed |
|---|---|---|---|
| Low | No GPU (CPU-only) | `llama3.2` (3B) | 60–180 s/query |
| Mid | NVIDIA GPU, < 12 GB VRAM (e.g. RTX 5060 8 GB) | `qwen2.5:7b` (7.6B) | ~1–2 s/query, ~71 tok/s |
| High | NVIDIA GPU, ≥ 12 GB VRAM (e.g. RTX 5080) | `qwen3:14b` (14B) | ~10 s/query |

> **Why the tiers split at 12 GB:** `qwen3:14b`'s ~10 GB KV cache + weights need that much VRAM to stay fully resident. Below 12 GB it partially offloads layers to CPU and loses the latency advantage it's picked for — worse than just running a smaller model that fits entirely in VRAM. `qwen2.5:7b` (~4.7 GB) is sized to fit comfortably in 8 GB-class cards with headroom for context, which is why it's the mid-tier pick rather than a scaled-down `qwen3`.

---

## 3. Install the prerequisites

Run these once per machine. All commands here are PowerShell unless noted.

### 3.1 Docker Desktop (required)

1. Download **Docker Desktop for Windows** from <https://www.docker.com/products/docker-desktop>.
2. Run the installer. When prompted, **enable "Use WSL 2 instead of Hyper-V"**. This is required for NVIDIA GPU passthrough to Linux containers.
3. After install, reboot.
4. Launch Docker Desktop. Wait until the whale icon in the system tray shows "Engine running" (≈ 30 s on first launch).
5. Verify from PowerShell:

```powershell
docker --version           # expect: Docker version 26.x or 29.x
docker compose version     # expect: Docker Compose version v2.x
docker run --rm hello-world
```

If `hello-world` prints "Hello from Docker!" you are good. If not, restart Docker Desktop and re-try.

> **Docker Desktop resource settings.** Open Docker Desktop → Settings → Resources → Advanced. Bump **Memory to ≥ 8 GB** and **Disk image size to ≥ 60 GB**. Default 2 GB RAM will OOM-kill Ollama mid-query.

### 3.2 Git (required)

Install **Git for Windows** from <https://git-scm.com/download/win>. Default settings are fine. Verify:

```powershell
git --version              # expect: git version 2.40+
```

### 3.3 NVIDIA GPU stack (recommended — skip if CPU-only)

If you have an NVIDIA GPU, install **all three** of the following, in order. Skip if you do not have an NVIDIA GPU; the stack will run CPU-only with `llama3.2`.

#### 3.3.1 NVIDIA driver

1. Open the **NVIDIA App** (or download from <https://www.nvidia.com/en-us/geforce/drivers/>).
2. Install the **latest Game Ready Driver** (or Studio Driver — either works). Minimum version: **551.xx** (CUDA 12.4) for RTX 50-series.
3. Reboot.
4. Verify:

```powershell
nvidia-smi
```

Expected output (yours will differ in card name / VRAM):

```
+-----------------------------------------------------------------------------+
| NVIDIA-SMI 551.xx       Driver Version: 551.xx       CUDA Version: 12.4    |
|-------------------------------+----------------------+----------------------+
| GPU  Name             | Bus-Id    | Memory-Usage    | GPU-Util  |
|   0  NVIDIA GeForce RTX 5080  ...  | 16384MiB total                        |
+-------------------------------+----------------------+----------------------+
```

If `nvidia-smi` is not recognised, the driver did not install — re-run the installer, choose **Custom (Advanced)** and tick all components.

#### 3.3.2 WSL 2 backend (already enabled with Docker Desktop)

If you enabled WSL 2 during Docker Desktop install, this is done. Otherwise:

```powershell
wsl --install              # installs Ubuntu by default, requires reboot
wsl --update               # ensure the latest kernel
wsl --version              # expect: WSL version 2.x
```

#### 3.3.3 NVIDIA Container Toolkit (auto via Docker Desktop)

On **Windows with Docker Desktop + WSL 2 + NVIDIA driver ≥ 551**, the Container Toolkit is bundled. You do **not** install it separately. The driver inside WSL is provided by `nvidia-smi.exe` on the host.

Verify GPU is visible to Docker:

```powershell
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

If this command shows your GPU, you are ready for the GPU compose overlay. If you get `could not select device driver "" with capabilities: [[gpu]]`, see [§4 Troubleshooting GPU setup](#4-verify-your-gpu-setup-nvidia) below.

### 3.4 Python 3.11 (optional)

You do **not** need Python locally — everything runs in Docker. Install Python 3.11 only if you want to:

- Run the Jupyter notebook in `notebooks/rag_poc.ipynb` directly on host.
- Run pytest outside the api container.
- Debug `src/document_processor/` modules with breakpoints in your IDE.

Get it from <https://www.python.org/downloads/release/python-3119/> (3.11.9 or any 3.11.x). Tick **"Add python.exe to PATH"** during install.

```powershell
python --version           # expect: Python 3.11.x
```

---

## 4. Verify your GPU setup (NVIDIA)

This step is critical — a wrong setup means your queries take 45–180 seconds each instead of 5–15 seconds. Skip if CPU-only.

```powershell
# 1. Driver works on host
nvidia-smi

# 2. GPU is visible to a Docker container (this is what Ollama uses)
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

Both commands must print a GPU table. If only step 1 works:

- Confirm **Docker Desktop → Settings → General → Use the WSL 2 based engine** is ticked.
- Confirm **Docker Desktop → Settings → Resources → WSL Integration → Enable integration with my default WSL distro** is ticked.
- Restart Docker Desktop (Quit Docker Desktop from system tray, relaunch).
- Update Docker Desktop to the latest version. NVIDIA support landed in 4.30.

If step 2 still fails with `could not select device driver`:

- Open PowerShell **as Administrator** and run `wsl --shutdown`, then relaunch Docker Desktop.
- Reinstall the NVIDIA driver, this time **rebooting before launching Docker Desktop**.

---

## 5. Clone and configure

```powershell
# 1. Pick a working directory and clone
cd C:\Users\$env:USERNAME\Desktop
git clone https://github.com/taylor-b-tran/edu-rag.git
cd edu-rag

# 2. Switch to the integration branch (or develop for the current release line)
git checkout develop

# 3. Copy the example environment file
Copy-Item .env.example .env
```

**Grading from the submitted zip instead of a git clone?** Skip steps 1-2, you already have the code — extract the zip and run step 3 (`Copy-Item .env.example .env`) from that folder.

Edit `.env` if you need non-default ports — most teammates leave it as-is. Defaults:

| Variable | Default | When to change |
|---|---|---|
| `APP_PORT` | `8501` | Streamlit UI port. Change if 8501 is in use |
| `API_PORT` | `5000` | Flask API port |
| `POSTGRES_PORT` | `5432` | Change if you have local Postgres running |
| `CHROMA_PORT` | `8000` | Change if 8000 is in use (Jupyter often grabs this) |
| `OLLAMA_PORT` | `11434` | Rarely conflicts |
| `DEFAULT_OLLAMA_MODEL` | `qwen3:14b` | The wrapper script in §6.1 will **overwrite** this automatically based on your GPU tier. Only set this by hand if you are running §6.2 manual compose — use `qwen2.5:7b` on an 8 GB-class GPU or `llama3.2` with no GPU, otherwise `qwen3:14b` partially offloads to RAM and silently loses the speedup |
| `POSTGRES_PASSWORD` | `edurag_dev_password` | Dev-only password. Do not commit changes |

> **Never commit `.env`** — it is gitignored. If you add secrets (e.g. `OPENAI_API_KEY` for optional GPT fallback), they stay local.

---

## 6. First-time startup

There are two ways to start the stack. **For new team members, use 6.1.** It's the safe default.

### 6.1 Auto-wrapper (recommended, GPU-aware) — `scripts/start_stack.ps1`

```powershell
pwsh scripts/start_stack.ps1
```

This is the only path that **automatically detects your GPU** and picks the right model. Run it once after `git clone`. Subsequent daily restarts can use plain `docker compose up -d` because the wrapper persists its decision into `.env`.

**What the wrapper does, in order:**

1. **Detects GPU VRAM** via `nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits` (rounded to nearest GB).
2. **Picks the model + compose overlay** using this decision rule:

   | Detected VRAM | Compose overlay | Selected model | Why |
   |---|---|---|---|
   | **≥ 12 GB** (high tier) | `docker-compose.gpu.yml` | `qwen3:14b` | Full 14 B model fits in VRAM; ~10 s/query |
   | **0 < VRAM < 12 GB** (mid tier) | `docker-compose.gpu.yml` | `qwen2.5:7b` | Fits fully in VRAM (~4.7 GB) with headroom — no CPU offload; ~1–2 s/query |
   | **No NVIDIA GPU** (low tier) | base Compose only (CPU mode) | `llama3.2` | ~60–180 s/query — slow but functional |
3. **Writes `DEFAULT_OLLAMA_MODEL=<chosen>` into `.env`** (creates `.env` from `.env.example` if missing; **overwrites** any existing value of that key). After this step, plain `docker compose up -d` will use the right model without re-running the wrapper.
4. **Brings the stack up:** `docker compose <compose-args> up -d --build`.
5. **Waits up to 60 s** for Ollama to answer `http://localhost:11434/api/tags`.
6. **Pulls the chosen model** via `docker compose exec ollama ollama pull <model>` (cached if already present). Skip with `-SkipPull`.

**Overrides** (handy when you know better than the defaults):

```powershell
pwsh scripts/start_stack.ps1 `
  -VramThresholdGb 16 `             # raise cutoff (e.g., still pick qwen2.5:7b on 12-15 GB)
  -HighVramModel "mixtral:8x7b" `   # use a different big model
  -MidVramModel "gemma2:9b" `       # use a different mid-tier model
  -LowVramModel "phi3:mini" `       # use a different small model
  -SkipPull                         # skip the ollama pull at the end
```

**When to re-run the wrapper:**

- You switch machines (different GPU).
- You change GPU (new card, BIOS-disabled card, etc.).
- You want to manually change models — easier to edit `.env` directly though.

**You do NOT need to re-run it for:**

- Daily restart of an already-configured machine. Use `docker compose up -d` (or with the GPU overlay if you want to reload it explicitly).
- Code changes in `src/` or `apps/` — those are volume-mounted, restart with `docker compose restart api streamlit`.

**Caveats** the wrapper does not handle:

- **Multi-GPU hosts:** it only reads `nvidia-smi` index 0 (the first GPU). On a 2× 8 GB host, you will be classified as 8 GB, not 16 GB total. Set `DEFAULT_OLLAMA_MODEL` and the compose overlay manually if you want to run the big model with NCCL-style multi-GPU.
- **Runtime VRAM changes:** the API does not re-detect after startup. Models are bound at API start via env var. If a process eats your VRAM mid-session, restart the stack.
- **Linux/macOS:** PowerShell is the supported path on Windows. For other OSes use `bash scripts/start_stack.sh` (same logic, same flags).

### 6.2 Manual compose (when you want explicit control)

Use this if you are debugging the stack itself, or you have specific requirements the wrapper does not cover (multi-GPU, non-default ports, custom models).

**Important:** manual compose **does not detect anything**. It uses `DEFAULT_OLLAMA_MODEL` from your `.env` as-is. If you have an 8 GB GPU and you forgot to edit `.env`, you will silently get `qwen3:14b` partially-offloaded and queries will be slow. Either:

- Edit `.env` to set `DEFAULT_OLLAMA_MODEL=qwen2.5:7b` (8 GB-class GPU) or `llama3.2` (no GPU) before bringing the stack up, OR
- Run `pwsh scripts/start_stack.ps1` once first (just for the detection), then drop back to manual.

```powershell
# CPU-only (safe everywhere — no GPU passthrough)
docker compose up -d --build

# NVIDIA GPU (requires §3.3 done; adds GPU overlay)
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
```

The first run downloads ~6 GB of Docker images and builds the api+streamlit image. Expect **5–15 minutes** depending on network. Subsequent runs reuse the cache and are ~30 seconds.

Then verify all five containers are healthy:

```powershell
docker compose ps
```

Expected output (all five rows must show `Up ... (healthy)` or just `Up`):

```
NAME                 STATUS                       PORTS
edurag-api-1         Up 1 minute (healthy)        0.0.0.0:5000->5000/tcp
edurag-chromadb-1    Up 1 minute                  0.0.0.0:8000->8000/tcp
edurag-ollama-1      Up 1 minute                  0.0.0.0:11434->11434/tcp
edurag-postgres-1    Up 1 minute (healthy)        0.0.0.0:5432->5432/tcp
edurag-streamlit-1   Up 1 minute (healthy)        0.0.0.0:8501->8501/tcp
```

If anything is `Restarting` or `Exited`, jump to [§12 Troubleshooting](#12-troubleshooting).

---

## 7. Pull the LLM model

If you used §6.1 (auto-wrapper), this is already done — skip to §8. If you used §6.2 (manual compose), pull the model yourself.

```powershell
# Pick ONE based on your tier (see §2):

# High tier — RTX 5080 / 4080 / 3090 (>= 12 GB VRAM):
docker compose exec ollama ollama pull qwen3:14b

# Mid tier — RTX 5060 / 4060 / 3060 (< 12 GB VRAM):
docker compose exec ollama ollama pull qwen2.5:7b

# Low tier — no GPU:
docker compose exec ollama ollama pull llama3.2
```

Download takes 3–10 minutes depending on connection. Confirm:

```powershell
docker compose exec ollama ollama list
```

Then update `.env` so `DEFAULT_OLLAMA_MODEL` matches what you pulled. After editing `.env`, restart the api:

```powershell
docker compose restart api
```

**Verify the model loads onto GPU** (skip if CPU-only):

```powershell
docker compose exec ollama ollama ps
```

You want `PROCESSOR=100% GPU`. Anything showing `% CPU` means GPU passthrough is broken — go back to [§4](#4-verify-your-gpu-setup-nvidia).

---

## 8. Seed the course corpus

The stack starts empty. To get grounded answers about CSIT321, ingest the seed corpus once:

```powershell
docker compose exec api python -m src.document_processor.ingest_corpus
```

Expected output ends with:

```
Upserted: 18 chunks into 'csit321_documents'
Collection total: 90
```

This loads 18 hand-prepared CSIT321 lecture chunks (Weeks 1–7) into ChromaDB using `sentence-transformers/all-MiniLM-L6-v2` (384-dim embeddings). The collection stays alive in the `chromadb_data` Docker volume between restarts.

> **You only need to run this once per fresh ChromaDB volume**. After `docker compose down -v` (which drops the volume), re-run it.

---

## 9. Verify the stack works

### 9.1 Health checks

```powershell
curl http://localhost:5000/api/health        # API — expect status=ok, warmup.status=ok or running
curl http://localhost:8000/api/v2/heartbeat  # ChromaDB
curl http://localhost:11434/api/tags          # Ollama — lists pulled models
curl http://localhost:8501/_stcore/health     # Streamlit
```

All four should return 200. The `/api/health` response includes a `warmup` block — once it shows `"status": "ok"` (within ~10 s of API startup), the model is hot in VRAM and your first query will not pay cold-start latency.

### 9.2 End-to-end smoke test (browser)

For the shared team deployment:

1. Connect to Tailscale.
2. Open the shared Paedia host address on port `8501`.
3. Sign in with a student account.
4. Ask: "What is Retrieval-Augmented Generation?"
5. Confirm that Paedia returns a grounded answer with source citations.

When testing directly on the GPU host or a standalone local deployment, `http://localhost:8501` may be used instead.

### 9.3 End-to-end upload flow (browser)

1. Sign out, sign in as **`lecturer@uow.edu.au`** — password from your `.env`.
2. Navigate to **Document Manager** in the sidebar.
3. Course selector: pick **CSIT321 – Project**.
4. Drop in any small PDF (try a 1–3 page handout to keep indexing fast).
5. Watch the status: `queued → processing → indexed`. Indexing a small PDF takes 5–15 s.
6. Switch to **Q&A Chat**, ask a question that depends on the file's content. Citation should point at your uploaded filename.

If you do not see the upload appear, see [§12.5](#125-upload-flow-broken).

---

## 10. Demo credentials

These users live in `fixtures/sample_responses.json`. Auth is in-memory — see [§19.4](#194-known-limitations) for why, and what is actually Postgres-backed.

| Email | Password | Role | Enrolled courses |
|---|---|---|---|
| `student@uow.edu.au` | `PAEDIA_DEMO_STUDENT_PASSWORD` | Student | CSIT214, CSIT321 |
| `lecturer@uow.edu.au` | `PAEDIA_DEMO_LECTURER_PASSWORD` | Lecturer | CSIT214, CSIT321 |
| `admin@uow.edu.au` | `PAEDIA_DEMO_ADMIN_PASSWORD` | Admin | All (bypasses enrollment check) |

**Passwords are no longer written down here.** They come from the three
variables above, set in your own gitignored `.env`. Leave them empty and
`src/api/db.py` falls back to the old published values — acceptable for a
checkout only you can reach, never for an instance anyone else can open. On the
shared host they are set to generated values; ask the team lead for them.

**Wrong password returns 401.** **Logout invalidates the token** — subsequent API calls return 401 until you log back in.

---

## 11. Daily operations

### Start (everything cached)

```powershell
docker compose up -d                                                    # CPU mode
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d    # GPU mode
```

### Stop (keep data)

```powershell
docker compose down
```

Your uploaded documents, indexed vectors, demo session history all survive.

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

> **No need to rebuild for code changes**: source is volume-mounted, so editing `src/` or `apps/` and running `docker compose restart api` (or `streamlit`) reloads it. Only run `docker compose build` after editing `requirements.txt` or `docker/Dockerfile.demo`.

### Rebuild after dependency change

```powershell
docker compose build api streamlit
docker compose up -d
```

### Run tests inside the api container

```powershell
docker compose exec api pytest test -q                    # full suite (112 tests)
docker compose exec api pytest test/test_api.py -q        # API tests only
docker compose exec api pytest -k "test_query_returns" -q  # filtered
```

### Warm the LLM manually (cold container, before recording)

```powershell
curl -X POST http://localhost:5000/api/warmup `
  -H "Authorization: Bearer <admin or lecturer JWT>"
```

The API auto-warms on startup, but `/api/warmup` is available if VRAM gets evicted (Ollama unloads idle models after `OLLAMA_KEEP_ALIVE=5m`).

### Re-ingest the seed corpus (after dropping volumes or pulling new seed files)

```powershell
docker compose exec api python -m src.document_processor.ingest_corpus
```

### Open a shell inside a container

```powershell
docker compose exec api bash                  # api container
docker compose exec postgres psql -U edurag   # Postgres CLI
docker compose exec ollama bash               # Ollama container
```

---

## 12. Troubleshooting

### 12.1 `docker compose up` says "address already in use"

A local process is holding one of the ports (5000, 5432, 8000, 8501, 11434).

```powershell
# Find what owns the port
Get-NetTCPConnection -LocalPort 5432 | Select-Object OwningProcess
Get-Process -Id <PID>
```

Either stop that process, or change the port mapping in `.env` (e.g. `POSTGRES_PORT=15432`).

### 12.2 Container name collision

```
Error: Container "edurag-chromadb-1" already exists
```

Old Sprint 3 containers from before the project name change are still on the machine:

```powershell
docker rm -f edurag-chromadb edurag-ollama-cpu edurag-postgres
docker compose up -d
```

### 12.3 Ollama returns `[Ollama not running]` in the chat

The model is not pulled, or the Ollama container is unhealthy.

```powershell
docker compose ps ollama                       # status?
docker compose exec ollama ollama list         # is the model present?
docker compose logs ollama --tail=50           # any errors?
```

Common fix:

```powershell
docker compose exec ollama ollama pull qwen3:14b   # or llama3.2
docker compose restart api
```

### 12.4 Getting fixture fallback instead of live answers

The chat returns a generic-sounding answer with `model_used: "fixture"` in the network tab. ChromaDB or Ollama is unreachable at API startup.

```powershell
# Check what backend the API selected
curl http://localhost:5000/api/health
# Look for: "mode": "chromadb", "rag_available": true

# If mode=fixture, force the API to retry
docker compose restart api
# Then make any query — the API initialises the RAG pipeline lazily on first /api/query

# Still failing? Re-seed the corpus
docker compose exec api python -m src.document_processor.ingest_corpus
```

### 12.5 Upload flow broken

Lecturer uploads a PDF but it does not appear in the student's document list.

1. Confirm the lecturer selected a course they are enrolled in (CSIT321 or CSIT214 — see [§10](#10-demo-credentials)).
2. Confirm the upload returned 202:
   ```powershell
   docker compose logs api --tail=50 | Select-String upload
   ```
3. Confirm indexing completed:
   ```powershell
   curl http://localhost:5000/api/documents?course_id=CSIT321 `
     -H "Authorization: Bearer <lecturer JWT>"
   ```
   Look for the file with `"status": "indexed"`. If stuck on `processing` for > 60 s, check `docker compose logs api --tail=200 | Select-String "Error in background indexing"`.
4. As student, confirm visibility:
   ```powershell
   curl http://localhost:5000/api/documents?course_id=CSIT321 `
     -H "Authorization: Bearer <student JWT>"
   ```

### 12.6 First query takes 45 s

The model is cold-loading into VRAM. This should NOT happen with revision 3 — `APIState.__post_init__` triggers a background warm-up on API startup. Check:

```powershell
curl http://localhost:5000/api/health
# Expect warmup.status=ok (and warmup.generated=true)
```

If `warmup.status` is not `ok`, the warm-up failed. Re-warm manually:

```powershell
docker compose restart api ollama
# Wait 60 s, then:
curl http://localhost:5000/api/health
```

To bypass warm-up (useful for CPU-only smoke runs), set `EDURAG_OLLAMA_WARMUP=false` in `.env` and restart api.

### 12.7 ChromaDB version mismatch on startup

```
ValueError: You are using a deprecated configuration of Chroma
```

Old volume from a previous Chroma image version.

```powershell
docker compose down -v
docker compose up -d --build
docker compose exec api python -m src.document_processor.ingest_corpus
```

### 12.8 GPU shows 100% CPU under `ollama ps`

The GPU compose overlay is not applied.

```powershell
# Confirm both compose files are loaded
docker compose -f docker-compose.yml -f docker-compose.gpu.yml config | Select-String -Pattern "gpu" -Context 2

# Re-up with the overlay
docker compose down
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
docker compose exec ollama nvidia-smi   # GPU must be visible inside the container
```

If `nvidia-smi` inside the container fails, see [§4](#4-verify-your-gpu-setup-nvidia).

### 12.9 "Account is suspended" in CI

This is a GitHub-side temporary block on `taylor-b-tran` — happens occasionally during high-traffic moments. Re-run the failed jobs after a few minutes:

```powershell
gh run rerun <run-id> --failed
```

### 12.10 Streamlit page is blank or shows raw HTML

Hard-refresh the browser (Ctrl+Shift+R). Streamlit's hot-reload sometimes leaves stale cached JS after a code change. If the page is still broken:

```powershell
docker compose restart streamlit
```

### 12.11 PowerShell can't run `start_stack.ps1`

```
File ... cannot be loaded because running scripts is disabled on this system.
```

Run **once** in an Administrator PowerShell:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Then re-run the script.

---

## 13. Architecture overview

```
Student / Lecturer / Admin
          │
          ▼
   ┌──────────────────┐
   │   Streamlit UI   │   apps/streamlit/main.py
   │   (port 8501)    │   Light-theme overrides, native Enter-login component
   └─────────┬────────┘
             │  HTTP + JWT
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
        │  │ qwen3:14b   │        │  vector store       │
        │  │ (port 11434)│        └──────────┬──────────┘
        │  └─────────────┘                   │ top-k chunks
        │                          ┌─────────▼─────────┐
        │                          │  Ollama generate  │
        │                          │  with citations   │
        │                          └───────────────────┘
        │
        ▼
   ┌─────────────────┐
   │   PostgreSQL    │   uploaded_documents, indexing_jobs — the only
   │   (port 5432)   │   tables actually wired up (see §19.4). Users,
   │                 │   courses, and sessions are still fixture/in-memory.
   └─────────────────┘
```

**Data flow on query** (`POST /api/query`):

1. Auth: JWT validated against `APIState.access_tokens`.
2. Enrollment: `APIState.is_enrolled(user, course_id)` — UUID/code normalization via `resolve_course()`.
3. Embedding: query string → `all-MiniLM-L6-v2` → 384-dim vector.
4. Retrieval: `VectorRetriever.search(query, course_id, top_k=5)` against ChromaDB with metadata filter `where={"course_id": {"$eq": course_id}}`.
5. Confidence: average similarity of retrieved chunks → Low/Medium/High.
6. Prompt: chunks + question + system instruction → `qwen3:14b` via Ollama.
7. Response: answer text + source_references (file + page + similarity) + confidence + latency.

**Data flow on upload** (`POST /api/upload`):

1. Auth + RBAC: lecturer/admin only.
2. Per-course enrollment check.
3. File written to `<repo>/data/uploads/<filename>` (Docker: `/workspace/data/uploads/`).
4. `APIState.queue_upload()` inserts rows into PostgreSQL `uploaded_documents` + `indexing_jobs`.
5. Background daemon thread:
   - chunker → 1024-char chunks
   - embedder → 384-dim vectors
   - ChromaDB `upsert` with course_id metadata
   - PostgreSQL `update_job(status=completed)` + `update_document_status(status=indexed)`.

---

## 14. Repository layout

```
edu-rag/
├── apps/
│   ├── streamlit/                # Streamlit UI prototype
│   │   ├── main.py               # entry point (1400+ lines, includes all pages)
│   │   ├── api_client.py         # HTTP client to Flask API
│   │   └── components/login_form/  # native Streamlit Enter-login component
│   └── integration/
│       ├── backend/api.py        # Flask entry point
│       ├── start.sh / stop.sh    # legacy start scripts
│       └── logs/                 # gitignored
├── src/
│   ├── api/
│   │   ├── app.py                # Flask app factory
│   │   ├── state.py              # APIState: hot cache, PG hydration, warmup trigger
│   │   ├── db.py                 # PostgreSQL persistence (Sprint 5 rev 2)
│   │   ├── warmup.py             # Background Ollama warm-up (Sprint 5 rev 3)
│   │   └── routes/               # auth, query, documents, sessions, health
│   ├── document_processor/
│   │   ├── chunker.py            # PDF/PPTX/DOCX → chunks
│   │   ├── ingest_corpus.py      # seed corpus loader
│   │   ├── offline_embedder.py   # FNV-1a fallback when sentence-transformers missing
│   │   ├── rag_pipeline.py       # VectorRetriever + LLMResponseGeneration
│   │   └── seed_documents.py     # in-repo CSIT321 chunks
│   └── vector_retriever/embedder.py
├── db/
│   ├── migrations/               # PostgreSQL schema (users, courses, sessions, audit log)
│   └── seed/                     # development seed data
├── docs/
│   ├── api/api_spec.yaml         # OpenAPI 3.0
│   ├── governance/               # privacy policy, ethics review
│   ├── sprint5_handover.md       # ← QA snapshot — read this for current state
│   ├── sprint5_runtime_notes.md  # operational deep-dive (complements this README)
│   ├── sprint5_implementation_summary.md
│   ├── sprint5_status_table.md
│   ├── a3_demo_script.md
│   ├── rag_benchmark_sprint5.md
│   ├── rag_limitations.md
│   └── system_design/            # system design v2
├── fixtures/sample_responses.json    # demo users, demo responses
├── notebooks/rag_poc.ipynb           # original RAG PoC
├── scripts/
│   ├── start_stack.ps1 / .sh     # GPU-aware wrapper (Option A)
│   └── sprint5_integration_gate.py   # CI demo-readiness gate
├── test/                          # pytest: 112 tests (rev 3)
├── docker/Dockerfile.demo
├── docker-compose.yml             # base stack (CPU-safe)
├── docker-compose.gpu.yml         # GPU overlay (NVIDIA only)
├── requirements.txt               # runtime deps + pytest (rev 3)
├── requirements-dev.txt           # CI-only deps (-r requirements.txt + pytest)
├── .env.example                   # copy to .env
└── README.md                      # this file
```

---

## 15. Tech stack reference

| Layer | Choice | Version | Why |
|---|---|---|---|
| Language | Python | 3.11 | Compatible with Docker base image, pinned for CI |
| UI | Streamlit | 1.51.0 | Fast iteration; native Python; no separate frontend build |
| API | Flask + Blueprints | 3.1.2 | Lightweight; team-familiar; easy testing |
| Text extraction | PyMuPDF (`fitz`) | 1.27.2.2 | Fast, reliable PDF text; better than pdfminer for layouts |
| Chunking | LangChain `RecursiveCharacterTextSplitter` | 1.1.0 | 1024-char chunks, 0 overlap (Sprint 3 benchmark default) |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` | 5.4.1 | 384-dim, fully local, ~22 MB model |
| Vector store | ChromaDB | 1.5.8 | Metadata filtering, simple HTTP API, Docker-ready |
| Relational DB | PostgreSQL | 16-alpine | Standard; auth/sessions/audit; psycopg3 with `dict_row` |
| Local LLM | Ollama + `qwen3:14b` (16 GB GPU) or `llama3.2` (8 GB or CPU) | Latest | Self-hosted; no external API; GPU-optional |
| Containerisation | Docker Compose | v2 | CPU + GPU overlay variants |
| Testing | Pytest + labelled query corpus | 8.3.3 | Unit, integration, retrieval evaluation; 112 tests pass on rev 3 |
| CI | GitHub Actions | — | Python tests + fixture validation + Compose validation + Sprint 5 integration gate |

---

## 16. Contributing

### Branching workflow

```
feature/task-branch  →  develop  →  main
       ↑                    ↑
       └─ PR with CI green  └─ PR after develop has cumulative changes
```

- All changes merge through **pull requests into `develop`**. Direct pushes to `main` or `develop` are not permitted.
- Sprint-specific branches use `feature/sN-...` or `fix/sN-...` (e.g. `fix/s5-final-fix-wave`).
- PR template: short summary + test plan + link to relevant Sprint task (e.g. S5-T11).
- Full convention documented in `SPRINT_BRANCH_WORKFLOW.md` (internal team doc, not included in the grading package).

### Local-development workflow

```powershell
# 1. Make sure your branch is up to date
git checkout develop
git pull
git checkout -b feature/s6-mytask

# 2. Run tests after each non-trivial change
docker compose exec api pytest test -q

# 3. Commit small, focused changes
git add <specific files>
git commit -m "feat(s6): one-line summary"

# 4. Push and create PR via GitHub UI or gh
git push -u origin feature/s6-mytask
gh pr create --base develop --title "..." --body "..."

# 5. Wait for CI green before requesting review
gh pr checks <pr-number>
```

### Code conventions

- **Python**: 4-space indent, type hints where they help, no f-string in log messages (use `%s` placeholders for lazy formatting).
- **No global mutable state in routes** — go through `APIState`.
- **Tests**: every new route gets a happy-path test and at least one auth/permission test.
- **Commits**: small and focused. The Sprint 5 final fix wave (PR #47) split into three commits by concern (rev 2 / rev 3 / docs) for reviewability.

### CI gates before merge

| Check | What it does | How to debug locally |
|---|---|---|
| Python tests and fixture validation | `pytest -q` + JSON schema check + Sprint 5 integration gate | `docker compose exec api pytest test -q` |
| Docker Compose validation | `docker compose config` on both base + GPU overlay | `docker compose config --quiet`; `docker compose -f docker-compose.yml -f docker-compose.gpu.yml config --quiet` |
| Demo stack smoke test | Spins up full stack on the runner, hits all health endpoints | Compose up locally and hit each `/health` route by hand |

If CI fails on something unrelated to your change (account suspension, disk-full runner), it is OK to `gh run rerun --failed` once.

---

## 17. Team

| Name | Module ownership |
|---|---|
| Thanh Binh Tran | Team Lead — RAG pipeline, prompt strategy, retrieval benchmark, system integration |
| Tai Huynh | Module 4 — API specification, privacy policy, ethics review, Sprint 4 kickoff, runtime notes, A3 demo script |
| Tung Phuong Anh Huynh | Testing — test query corpus, corpus manifest, evaluation methodology, QA checklist |
| Andre (Kahavidanage Namaratne) | Data & requirements — ERD, DFD, risk register, storage sizing, PostgreSQL schema, requirements traceability matrix |
| Thi Hong Ngoc Nguyen | Document processing — retrieval edge cases, RAG configuration contribution, RAG limitations doc |
| Anmoldeep Singh | UI — Streamlit wireframes, design system, UI state model, contrast fixes |

---

## 18. Project context

| Item | Value |
|---|---|
| Subject | CSIT321 Annual Session 2026 — Project 37 |
| Campus | University of Wollongong, Liverpool Campus (SWS) |
| Group | Group 19 — Aletheia's Zetetes |
| Supervisor | Prof. Jun Yan |
| Sprint cadence | 4 × 2-week sprints (Sprint 3 was the architecture sprint; Sprint 4 wired the API + UI; Sprint 5 wires live RAG end-to-end; Sprint 6 is post-A3) |

This is an assessed final-year project but the engineering work — system design, API specification, retrieval tuning, privacy modelling, sprint delivery, and QA evidence — reflects professional software development practice rather than tutorial exercises.

---

## 19. For the Marker

This section is a fast path for grading. It assumes you've already done the setup in [§1–§9](#1-what-you-are-about-to-run) and the stack is running. If not, start there — this section does not repeat setup steps.

### 19.1 60-second orientation

- **Product:** Paedia — a course Q&A assistant. A lecturer uploads course material; a student asks a question; the answer is generated only from that material, with page-level citations.
- **What's real vs. simulated:** document upload, chunking, embedding, retrieval, and LLM generation are all live (ChromaDB + Ollama, no mocking). Authentication and course/session records are **fixture-backed**, not a real database — see [§19.4](#194-known-limitations).
- **Where to look first:** [`docs/rtm_a4.md`](docs/rtm_a4.md) maps every A2 requirement to its current status and evidence file. If you only read one document, read that one.

### 19.2 Fastest path to a live demo

```powershell
docker compose up -d --build
docker compose exec api python -m src.document_processor.ingest_corpus   # once, if not already seeded
python scripts/check_demo_ready.py                                       # confirms all 5 services are healthy
```

Then in a browser:

1. Open <http://host:8501>, sign in as `student@uow.edu.au` (passwords in [§10](#10-demo-credentials)).
2. Ask: *"What is Retrieval-Augmented Generation?"* — expect an answer citing `Week1_RAG_Introduction.pdf`, confidence label, and model name shown in the response footer.
3. Sign out, sign in as `lecturer@uow.edu.au`, open **Document Manager**, upload a short PDF, watch it go `queued → processing → indexed`.
4. Ask a question that depends on that file — the citation should point at your filename.

If any of this doesn't work, [§12 Troubleshooting](#12-troubleshooting) covers the common failure modes.

### 19.3 What to check, mapped to requirements

| Area | Where to verify | Evidence |
|---|---|---|
| Functional requirements (all 33, individually) | Live demo per [§19.2](#192-fastest-path-to-a-live-demo) | [`docs/rtm_a4.md`](docs/rtm_a4.md) |
| Non-functional requirements | — | [`docs/rtm_a4.md`](docs/rtm_a4.md) (NFR-001 to NFR-008) |
| System architecture, as actually implemented | — | [`docs/architecture/erd_reconciliation_sprint5.md`](docs/architecture/erd_reconciliation_sprint5.md), [`docs/architecture/seq_api_query_sprint5.md`](docs/architecture/seq_api_query_sprint5.md) |
| Retrieval/generation performance | — | [`docs/t10_embedding_benchmark.md`](docs/t10_embedding_benchmark.md), [`docs/finetuning_benchmark_sprint6.md`](docs/finetuning_benchmark_sprint6.md) |
| Runs without a GPU (grading-machine safety) | `docker compose up -d` with no GPU overlay | [`docs/t25_gpu_free_verification.md`](docs/t25_gpu_free_verification.md) |
| Fresh-machine setup actually works | — | [`docs/dry_run_2_cold_grader.md`](docs/dry_run_2_cold_grader.md) |
| Full end-to-end sanity pass (all 3 roles, upload pipeline, what's real vs. fixture) | — | [`docs/vv_full_app_report_2026-08-03.md`](docs/vv_full_app_report_2026-08-03.md) |
| Automated tests | `docker compose exec api pytest` | 118 tests, see [§11](#11-daily-operations) |

### 19.4 Known limitations

Stated here rather than left for you to discover:

- **Auth, courses, and chat sessions are fixture/in-memory, not a real database.** Only document upload metadata (`uploaded_documents`, `indexing_jobs`) is actually persisted to PostgreSQL. The other 7 tables in `db/migrations/001_initial_schema.sql` were designed but never wired up. Full detail: [`docs/architecture/erd_reconciliation_sprint5.md`](docs/architecture/erd_reconciliation_sprint5.md).
- **Retrieval accuracy has not been formally benchmarked** against a labelled query set (precision/recall). What's benchmarked is generation quality and speed, not retrieval correctness — see `rtm_a4.md` FR-028.
- **Admin dashboard is read-only** — user management actions are disabled in this build, not wired to a backend.

None of these block the core demo flow (upload → index → ask → grounded answer with citations), which is fully live end to end.

---

## Further reading

When this README is not enough:

- **Full evidence index**: [`docs/a4_evidence_index.md`](docs/a4_evidence_index.md) — every artifact backing the A4 submission, grouped by topic.
- **Docker bundle reference**: [`README_docker.md`](README_docker.md) — service contract for the Compose stack.
- **API contract**: [`docs/api/api_spec.yaml`](docs/api/api_spec.yaml) — OpenAPI 3.0.

---

## License

University of Wollongong course project repository. Licensing and reuse terms are not yet finalised.
