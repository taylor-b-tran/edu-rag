# Installation and configuration

[Back to README](README.md) · [Operations](docs/operations.md) · [Architecture](docs/architecture.md)

Use this guide to install a standalone development or demonstration stack. People using the shared instance only need the [shared-access instructions](README.md#shared-access).

Run commands from the repository root. For a fresh installation: configure passwords → start the selected CPU/GPU stack → provision the embedding cache → ensure the selected Ollama model is pulled → upload material or optionally seed a fresh demo → verify the result. Model and image downloads require network access during setup.

Jump to [prerequisites](#install-the-prerequisites), [configuration](#clone-and-configure), [startup](#first-time-startup), [embedding cache](#provision-the-embedding-model-cache), [model pull](#pull-the-llm-model), [sample corpus](#seed-the-course-corpus), [verification](#verify-the-stack-works) or [demo accounts](#demo-credentials).

## System requirements

| Resource | Minimum | Recommended | Notes |
|---|---|---|---|
| **OS** | Windows with Docker Desktop and WSL 2 | Windows 11 | This guide uses PowerShell; other hosts need Docker Engine/Compose and compatible scripts |
| **CPU** | 4 cores | 8 cores | Inference is mostly GPU, but PDF chunking + embeddings use CPU |
| **RAM** | 16 GB | 32 GB | Leave enough headroom for the configured Ollama model and the other services |
| **Disk** | 25 GB free | 40 GB free | Allow for Ollama models, Docker images, ChromaDB, PostgreSQL, source, and the embedding cache |
| **GPU** | None (CPU-only works, slow) | NVIDIA RTX with **≥ 12 GB VRAM** | The PowerShell wrapper selects one of three model tiers below |
| **Network** | Once for image pulls + model download | — | Local inference requires a complete embedding cache and downloaded Ollama model |

**Three model tiers**, selected by `scripts/start_stack.ps1`. Model fit and latency depend on context length, available VRAM and concurrent workloads; these are selection rules, not performance guarantees:

| Tier | Hardware detected by the PowerShell wrapper | Model | Notes |
|---|---|---|---|
| Low | No NVIDIA GPU | `llama3.2` | CPU inference; expect slower answers |
| Mid | NVIDIA GPU, < 12 GB VRAM | `qwen2.5:7b` | Smaller model for lower VRAM |
| High | NVIDIA GPU, ≥ 12 GB VRAM | `gemma4:12b` | Current PowerShell/Compose default |

> The wrapper uses a 12 GB cutoff. If a model partially offloads to CPU or does not fit alongside other workloads, select a smaller model and check `ollama ps`.


## Install the prerequisites

Run these once per machine. All commands here are PowerShell unless noted. `pwsh` means PowerShell 7; if it is not installed, run the Windows setup script as `.\scripts\start_stack.ps1` from Windows PowerShell.

### Docker Desktop (required)

1. Download **Docker Desktop for Windows** from <https://www.docker.com/products/docker-desktop>.
2. Run the installer. When prompted, **enable "Use WSL 2 instead of Hyper-V"**. This is required for NVIDIA GPU passthrough to Linux containers.
3. After install, reboot.
4. Launch Docker Desktop. Wait until the whale icon in the system tray shows "Engine running" (≈ 30 s on first launch).
5. Verify from PowerShell:

```powershell
docker --version
docker compose version     # expect: Docker Compose version v2.x
docker run --rm hello-world
```

If `hello-world` prints "Hello from Docker!" you are good. If not, restart Docker Desktop and re-try.

> **Docker Desktop resource settings.** Open Docker Desktop → Settings → Resources → Advanced. Bump **Memory to ≥ 8 GB** and **Disk image size to ≥ 60 GB**. Allocate enough memory and disk for the selected model and the other services; WSL 2 resource limits may also apply.

### Git (required)

Install **Git for Windows** from <https://git-scm.com/download/win>. Default settings are fine. Verify:

```powershell
git --version              # expect: git version 2.40+
```

### NVIDIA GPU stack (recommended — skip if CPU-only)

If you have an NVIDIA GPU, check the driver, WSL 2 backend and container GPU access below. Skip this section for a CPU-only deployment using `llama3.2`.

#### NVIDIA driver and WSL 2

Install an NVIDIA driver that supports your GPU and Docker's WSL 2 backend, then reboot if the installer requires it. Enable the WSL 2 engine in Docker Desktop.

```powershell
nvidia-smi
wsl --version
wsl --update
```

If WSL is not installed, run `wsl --install` and follow its restart instructions.

#### Verify container GPU access

```powershell
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

The command should show the GPU. If it fails, use [Verify your GPU setup (NVIDIA)](#verify-your-gpu-setup-nvidia) before starting the GPU stack. Linux Docker Engine hosts also need NVIDIA Container Toolkit configuration appropriate to their installation.

---

### Python 3.11 (optional)

You do **not** need Python locally — everything runs in Docker. Install Python 3.11 only if you want to:

- Run the Jupyter notebook in `notebooks/rag_poc.ipynb` directly on host.
- Run pytest outside the api container.
- Debug `src/document_processor/` modules with breakpoints in your IDE.

Get it from <https://www.python.org/downloads/release/python-3119/> (3.11.9 or any 3.11.x). Tick **"Add python.exe to PATH"** during install.

```powershell
python --version           # expect: Python 3.11.x
```


## Verify your GPU setup (NVIDIA)

Verify GPU passthrough before choosing the GPU overlay. Skip this section for CPU-only installation.

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
- Check that the installed Docker Desktop and NVIDIA driver support your GPU and WSL configuration.

If step 2 still fails with `could not select device driver`:

- Open PowerShell **as Administrator** and run `wsl --shutdown`, then relaunch Docker Desktop.
- Reinstall the NVIDIA driver, this time **rebooting before launching Docker Desktop**.


## Clone and configure

```powershell
# 1. Pick a working directory and clone
cd C:\Users\$env:USERNAME\Desktop
git clone https://github.com/taylor-b-tran/edu-rag.git
cd edu-rag

# 2. Use the integration branch
git checkout develop

# 3. Copy the example environment file
Copy-Item .env.example .env
```

**Grading from the submitted zip instead of a git clone?** Skip steps 1-2, you already have the code — extract the zip and run step 3 (`Copy-Item .env.example .env`) from that folder.

Before starting, set the three `PAEDIA_DEMO_*_PASSWORD` variables in `.env` if you need the seeded demo accounts. Blank values create accounts without a known sign-in password. See [Demo credentials](#demo-credentials). Review these configuration values as well:

| Variable | Default | When to change |
|---|---|---|
| `PAEDIA_BIND_ADDR` | `127.0.0.1` | Bind address for the UI/API. Shared access requires administrator configuration |
| `APP_PORT` | `8501` | Streamlit UI port. Change if 8501 is in use |
| `API_PORT` | `5000` | Flask API port |
| `POSTGRES_PORT` | `5432` | Change if you have local Postgres running |
| `CHROMA_PORT` | `8000` | Change if 8000 is in use (Jupyter often grabs this) |
| `OLLAMA_PORT` | `11434` | Rarely conflicts |
| `DEFAULT_OLLAMA_MODEL` | `gemma4:12b` | The wrapper script in [Automatic startup](#automatic-startup) overwrites this automatically based on your GPU tier. Set it manually only when using [Manual startup](#manual-startup) manual compose. |
| `POSTGRES_PASSWORD` | `edurag_dev_password` | Dev-only password. Do not commit changes |

> **Never commit `.env`** — it is gitignored. If you add secrets, they stay local. No cloud API keys are needed: generation runs through Ollama only.


## First-time startup

Choose automatic startup for hardware detection, or manual startup for explicit model and Compose selection.

### Automatic startup

```powershell
pwsh scripts/start_stack.ps1
```

The wrapper detects your GPU and selects a model tier. Run it after cloning and configuring `.env`. It saves the model choice, but does not save the GPU Compose overlay; use the matching CPU/GPU command in [Daily operations](docs/operations.md#daily-operations) for later starts.

**What the wrapper does, in order:**

1. **Detects GPU VRAM** via `nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits` (rounded to nearest GB).
2. **Picks the model and Compose overlay** using the [model-tier table](#system-requirements).
3. **Writes `DEFAULT_OLLAMA_MODEL=<chosen>` into `.env`** (creates `.env` from `.env.example` if missing; **overwrites** any existing value of that key). The model value persists for subsequent starts; NVIDIA GPU access still requires the GPU overlay.
4. **Brings the stack up:** `docker compose <compose-args> up -d --build`.
5. **Waits up to 60 s** for Ollama to answer `http://localhost:11434/api/tags`.
6. **Pulls the chosen model** via `docker compose exec ollama ollama pull <model>` (cached if already present). Skip with `-SkipPull`.

**Overrides** (handy when you know better than the defaults):

```powershell
# Raise the cutoff and reuse already-downloaded model weights.
pwsh scripts/start_stack.ps1 -VramThresholdGb 16 -SkipPull

# Optional model parameters: -HighVramModel, -MidVramModel, -LowVramModel
```

**When to re-run the wrapper:**

- You switch machines (different GPU).
- You change GPU (new card, BIOS-disabled card, etc.).
- You want to manually change models — easier to edit `.env` directly though.

**You do NOT need to re-run it for:**

- Daily start of an already-configured machine. Use the CPU or GPU command in [Daily operations](docs/operations.md#daily-operations); the GPU overlay remains required on the GPU path.
- Code changes in `src/` or `apps/` — those are volume-mounted, restart with `docker compose restart api streamlit`.

**Caveats** the wrapper does not handle:

- **Multi-GPU hosts:** it only reads `nvidia-smi` index 0 (the first GPU). On a 2× 8 GB host, you will be classified as 8 GB, not 16 GB total. Choose the model and GPU configuration manually for a multi-GPU deployment.
- **Runtime VRAM changes:** the wrapper does not monitor memory after setup. Choose a smaller model if available memory drops; global model settings can also override the environment default.
- **Bash wrapper:** `scripts/start_stack.sh` uses environment-variable overrides, not PowerShell flags. Its current high-tier default is `qwen3:14b`; use `HIGH_VRAM_MODEL=gemma4:12b bash scripts/start_stack.sh` to align with the PowerShell/Compose default. NVIDIA GPU support depends on the host; CPU-only hosts should use the manual CPU path.

### Manual startup

Use this if you are debugging the stack itself, or you have specific requirements the wrapper does not cover (multi-GPU, non-default ports, custom models).

**Important:** manual compose **does not detect anything**. It uses `DEFAULT_OLLAMA_MODEL` from your `.env` as-is. If you have an 8 GB GPU and keep the `gemma4:12b` default, it may partially offload and queries may be slow. Either:

- Edit `.env` to set `DEFAULT_OLLAMA_MODEL=qwen2.5:7b` (8 GB-class GPU) or `llama3.2` (no GPU) before bringing the stack up, OR
- Use [Automatic startup](#automatic-startup) to detect hardware, write the model setting, start services and pull that model. The wrapper performs all of these actions.

```powershell
# CPU-only (safe everywhere — no GPU passthrough)
docker compose up -d --build

# NVIDIA GPU (after verifying container GPU access)
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
edurag-api-1         Up 1 minute (healthy)        127.0.0.1:5000->5000/tcp
edurag-chromadb-1    Up 1 minute                  127.0.0.1:8000->8000/tcp
edurag-ollama-1      Up 1 minute                  127.0.0.1:11434->11434/tcp
edurag-postgres-1    Up 1 minute (healthy)        127.0.0.1:5432->5432/tcp
edurag-streamlit-1   Up 1 minute (healthy)        127.0.0.1:8501->8501/tcp
```

If anything is `Restarting` or `Exited`, jump to [Troubleshooting](docs/operations.md#troubleshooting).

---

### Provision the embedding model cache

The embedding cache lives at `./models/embedder_cache` by default, or at
`EMBEDDER_CACHE_DIR` when configured. The `models/` directory is deliberately
gitignored, so a fresh clone does not contain `all-MiniLM-L6-v2`.

On a host with internet access, populate the cache once from the API image:

```powershell
docker compose run --rm --no-deps -e HF_HUB_OFFLINE=0 -e TRANSFORMERS_OFFLINE=0 api python -c "import os; from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2', cache_folder=os.getenv('EMBEDDER_CACHE_DIR', './models/embedder_cache'))"
```

Preserve the complete Hugging Face cache layout. Snapshot files may link to
weight blobs, so copying only part of the directory can leave the weights
present but unusable. A complete cache may be mounted read-only at runtime.

The embedder loads lazily on the first retrieval request. Afterwards,
`GET /api/health` should report `embedder.status: "ok"`,
`model_name: "all-MiniLM-L6-v2"`, `dim: 384`, and
`retrieval_quality: "ok"`. Before first use, `embedder.status: "not_loaded"`
is expected. If it reports `offline_fallback`, read the accompanying `reason`;
retrieval is degraded even if `rag_available` is still true.

Collections record the embedder that created their vectors. A different active
embedder is refused until the matching model is restored or the collection is
deliberately rebuilt. A legacy collection without a stamp adopts the active
model with a warning; that adoption does not prove the provenance of its old
vectors.


## Pull the LLM model

The automatic wrapper pulls the selected model unless `-SkipPull` is used. For manual startup, pull the same model you selected in `.env`.

```powershell
# Pick ONE based on your tier (see [System requirements](#system-requirements)):

# High tier — RTX 5080 / 4080 / 3090 (>= 12 GB VRAM):
docker compose exec ollama ollama pull gemma4:12b

# Mid tier — RTX 5060 / 4060 / 3060 (< 12 GB VRAM):
docker compose exec ollama ollama pull qwen2.5:7b

# Low tier — no GPU:
docker compose exec ollama ollama pull llama3.2
```

Download takes 3–10 minutes depending on connection. Confirm:

```powershell
docker compose exec ollama ollama list
```

Then update `.env` so `DEFAULT_OLLAMA_MODEL` matches what you pulled. After editing `.env`, recreate the API so its container receives the new environment:

```powershell
# CPU deployment
docker compose up -d --force-recreate api

# GPU deployment
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --force-recreate api
```

An administrator-selected model in global settings takes precedence over this default. A simple `restart` does not reload Compose environment values.

**Verify the model loads onto GPU** (skip if CPU-only):

```powershell
docker compose exec ollama ollama ps
```

Run this after a warm-up or query so the model is loaded. `100% GPU` indicates full GPU residency. CPU use can mean missing GPU passthrough or a model that exceeds available VRAM; check [Verify your GPU setup (NVIDIA)](#verify-your-gpu-setup-nvidia), the overlay and the chosen model.


## Seed the course corpus

A fresh vector-store volume contains no indexed course content. After provisioning the embedding cache, optionally load the sample corpus once for a standalone demo. For real courses, use lecturer uploads instead:

```powershell
docker compose exec api python -m src.document_processor.ingest_corpus
```

Expected output ends with:

```
  [OK] Upserted 46 chunks  (…s)
  [OK] Collection total: <number of chunks in the collection> chunks
```

This loads 46 hand-prepared seed chunks (CSIT321 22, CSIT214 10, CSCI369 10, MATH202 4) into ChromaDB using `sentence-transformers/all-MiniLM-L6-v2` (384-dim embeddings). The collection stays alive in the `chromadb_data` Docker volume between restarts.

> **You only need to run this once per fresh ChromaDB volume**. After `docker compose down -v` (which drops the volume), re-run it.


## Verify the stack works

### Health checks

```powershell
curl.exe http://localhost:5000/api/health    # API, warm-up and retrieval status
curl.exe http://localhost:8000/api/v2/heartbeat  # ChromaDB
curl.exe http://localhost:11434/api/tags          # Ollama — lists pulled models
curl.exe http://localhost:8501/_stcore/health     # Streamlit
```

These endpoints check service availability. `warmup.status: "ok"` records a successful warm-up; it does not guarantee the model is still resident later. After a retrieval request, also check the embedder and `retrieval_quality` fields described in [First-time startup](#first-time-startup). A healthy endpoint alone does not establish grounded answers or end-to-end readiness.

### End-to-end smoke test (browser)

For the shared team deployment:

1. Connect to Tailscale.
2. Open the shared Paedia host address on port `8501`.
3. Sign in with a student account.
4. Ask: "What is Retrieval-Augmented Generation?"
5. Confirm that Paedia returns a grounded answer with source citations.

When testing directly on the GPU host or a standalone local deployment, `http://localhost:8501` may be used instead.

### End-to-end upload flow (browser)

1. Sign out, sign in as **`lecturer@uow.edu.au`** — password from your `.env`.
2. Navigate to **Document Manager** in the sidebar.
3. Course selector: pick **CSIT321 – Project**.
4. Drop in any small PDF (try a 1–3 page handout to keep indexing fast).
5. Watch the status: `queued → processing → indexed`. Indexing time depends on file contents and host load; a failed job should show its error.
6. Switch to **Q&A Chat**, ask a question that depends on the file's content. Citation should point at your uploaded filename.

If you do not see the upload appear, see [Upload flow broken](docs/operations.md#upload-flow-broken).


## Demo credentials

These accounts are seeded in the PostgreSQL `users` table at API startup, with bcrypt password hashes configured by the environment variables below. Sign-in tokens are opaque rows in the `access_tokens` and `refresh_tokens` tables. The fixture login in `fixtures/sample_responses.json` applies only when there is no database and `PAEDIA_ALLOW_FIXTURE_AUTH=1`. Fixture mode is for isolated development; it is disabled by default.

| Email | Password | Role | Enrolled courses |
|---|---|---|---|
| `student@uow.edu.au` | `PAEDIA_DEMO_STUDENT_PASSWORD` | Student | CSIT321, CSCI203 |
| `lecturer@uow.edu.au` | `PAEDIA_DEMO_LECTURER_PASSWORD` | Lecturer | CSIT321, CSCI203 |
| `admin@uow.edu.au` | `PAEDIA_DEMO_ADMIN_PASSWORD` | Admin | All (bypasses enrollment check) |

**More accounts.** Anyone can sign up as a student and then join any active course. A new **lecturer** account is created in a waiting state: it cannot sign in until an administrator approves it on the Admin Dashboard (accounts that existed before this rule count as approved). The email address is not case-sensitive at sign-in.

**Passwords are no longer written down here.** They come from the three
variables above, set in your own gitignored `.env`. Leave one empty and that
account is created with a random password nobody knows — it exists, but cannot
be signed into until the variable is set and the API recreated with the updated environment. There is no
fallback to a known value. For shared-instance credentials, ask the host administrator.

**Wrong password returns 401.** **Logout invalidates the token** — subsequent API calls return 401 until you log back in.

## Service contract

The normal stack runs `api`, `streamlit`, `postgres`, `chromadb` and `ollama`. An optional `app` shell is available through `docker compose --profile tools run --rm app sh`; it is not part of the normal application path.

- `api` and `streamlit` build from `docker/Dockerfile.demo`. The API runs Gunicorn with `src.api.wsgi:app`; Streamlit runs `apps/streamlit/main.py`.
- Within the Compose network, Streamlit uses `http://api:5000`; the API uses `postgres:5432`, `chromadb:8000` and `http://ollama:11434`. Host port overrides do not change these internal addresses.
- The source tree is mounted at `/workspace`. Named volumes preserve PostgreSQL data, vector data, uploads and Ollama weights; the embedding cache is under the host checkout's `models/` directory.
- PostgreSQL uses `postgres:16-alpine`. ChromaDB and Ollama images are pinned by digest in [docker-compose.yml](docker-compose.yml); consult that file for the exact image identities.
- Default host bindings are loopback. `PAEDIA_BIND_ADDR` changes the UI/API binding; PostgreSQL, ChromaDB and Ollama remain mapped to loopback by the tracked configuration.

See the [architecture service table](docs/architecture.md#services-and-data-flow) for ports, and [operations](docs/operations.md) for subsequent starts, environment changes, persistence and troubleshooting.
