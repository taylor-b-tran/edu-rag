# T26 — Cold Grader Dry Run #1

**Task:** T26
**Owner:** Tung Phuong Anh Huynh
**Sprint:** 6 (27 Jul – 7 Aug 2026)
**Due:** 30 Jul 2026
**Branch tested:** `develop` (fresh clone — see Section 6.2 procedure)
**Log recorded on branch:** `feature/tung-sprint6`

> Per Section 6.3 of the Sprint 6 plan: "It works on my machine" is not proof.
> This run must be performed by someone other than the code's author (Thanh), on a
> genuinely fresh checkout, following only `README.md` and `README_docker.md`.
> No Slack, no asking teammates, no memory of prior setups.

---

## 0. Run metadata

| Field | Value |
|---|---|
| Date | 29 Jul 26 |
| Start time | 21:07 |
| End time | 21:32 |
| Machine used | Windows laptop |
| OS / Docker version | Windows 11, Docker 28.5.1, Docker Compose v2.40.2-desktop.1 |
| GPU present? | No (Intel Iris Xe integrated graphics; CPU-only test) |
| `develop` branch | `develop` |
| `develop` commit hash tested | `2616d8a` |
| Commit subject | Merge pull request #47 from taylor-b-tran/fix/s5-final-fix-wave |

---

## 1. Pre-run notes (known repo state at time of writing)

These are **not yet in the repo** as of this dry run and their absence is expected,
not a failure — they belong to later Sprint 6 tasks:

- `scripts/check_demo_ready.py` — does not exist yet (built for T29, owned by Thanh, due 3 Aug)
- A **"For the Marker"** quick-start section in `README.md` — not added yet (T30, owned by Tai, due 4 Aug)

If either has landed by the time you run this, use it — just note that in the log below.

---

## 2. Step-by-step log

| # | Step | Command run | Start | End | Result (PASS/FAIL) | Verbatim output / error |
|---|---|---|---|---|---|---|
| 1 | New empty folder, no reused checkout | `mkdir edurag-coldrun-1; cd edurag-coldrun-1` | 21:07 | 21:08 | PASS | Fresh empty test folder created successfully |
| 2 | Fresh clone of `develop` | `git clone https://github.com/taylor-b-tran/edu-rag.git .` | 21:08 | 21:10 | PASS | Repository cloned successfully |
| 3a | Confirm branch | `git branch` | 21:10 | 21:10 | PASS | `* develop` |
| 3b | Confirm commit | `git log -1 --oneline` | 21:10 | 21:11 | PASS | `2616d8a Merge pull request #47 from taylor-b-tran/fix/s5-final-fix-wave` |
| 4 | Copy `.env.example` to `.env` | `cp .env.example .env` (or `Copy-Item .env.example .env`) | 21:11 | 21:12 | PASS | `.env` file created successfully — `DEFAULT_OLLAMA_MODEL=qwen3:14b` (unedited default) |
| 5 | Read README top-to-bottom, follow install prerequisites (Docker Desktop, Git) if not already present | — | 21:12 | 21:20 | PASS | README instructions reviewed and prerequisites confirmed |
| 6 | Start the stack, CPU-only (no `-f docker-compose.gpu.yml`) | `docker compose up -d --build` | 21:20 | 21:25 | PASS | Docker images built successfully; network and volumes created; all containers started successfully; API and PostgreSQL health reported healthy status |
| 7 | Confirm all 5 services healthy | `docker compose ps` | 21:25 | 21:26 | PASS | All five services (`postgres`, `chromadb`, `ollama`, `api`, `streamlit`) were running; API, PostgreSQL and Streamlit reported healthy status |
| 8 | Pull Ollama model per hardware table (no GPU → `llama3.2`) | `docker compose exec ollama ollama pull llama3.2` | 21:25 | 21:26 | PASS | pulling manifest — pulling dde5aa3fc5ff: 100% 2.0 GB; pulling 966de95ca8a6: 100% 1.4 KB; pulling fcc5a6bec9da: 100% 7.7 KB; pulling a70ff7e570d9: 100% 6.0 KB; pulling 56bb8bd477a5: 100% 96 B; pulling 34bb5ab01051: 100% 561 B; verifying sha256 digest; writing manifest; success |
| 9 | Health check — API | `curl http://localhost:5000/api/health` | 21:26 | 21:27 | FAIL | `"status": "ok"`, `"warmup": {"status": "degraded", "error": "pull_failed: ReadTimeout: HTTPConnectionPool(host='ollama', port=11434): Read timed out. (read timeout=600)", "model": "qwen3:14b"}` |
| 10 | Health check — Streamlit | `curl http://localhost:8501/_stcore/health` | 21:27 | 21:28 | PASS | `ok` |
| 11 | Open UI in browser | `http://localhost:8501` | 21:28 | 21:29 | PASS | Streamlit application loaded successfully |
| 12 | Log in as demo student | `student@uow.edu.au` / `student123` | 21:28 | 21:29 | PASS | Login successful |
| 13 | Ask one CSIT321 question | "What is Retrieval-Augmented Generation?" | 21:29 | 21:31 | FAIL | Response fell back to general knowledge instead of course materials |
| 14 | Confirm answer is grounded + cited | — | 21:31 | 21:32 | FAIL | `⚠️ Based on general knowledge — not verified against course materials. [LLM Error: 404 Client Error: Not Found for url: http://ollama:11434/api/generate]` |

---

## 3. Result summary

**Total elapsed time (clone → cited answer):** 24 minutes

**Overall result:** FAIL

**Success criterion met** (Section 6.2, Step 5 — open browser, ask one CSIT321
question, get a cited answer): No

---

## 4. Errors found (each becomes a separate T27 fix, owned jointly with Thanh)

| Error ID | Step # | Verbatim error | Root cause (confirmed via source inspection) | Assigned fix commit |
|---|---|---|---|---|
| DR1-01 | 9 | `pull_failed: ReadTimeout: HTTPConnectionPool(host='ollama', port=11434): Read timed out. (read timeout=600)` | `.env` defaults to `qwen3:14b`, which failed to be pulled during warm-up | *[Thanh — T25/T27]* |
| DR1-02 | 13–14 | `404 Client Error: Not Found for url: http://ollama:11434/api/generate` | The application attempted to use `qwen3:14b`, which was unavailable so generation failed | *[Thanh — T25/T27]* |

---

## 5. Sign-off

- [x] Log sent to Thanh same day as the run
- [x] Errors entered into T27 tracking
- [x] This file committed to `feature/tung-sprint6` and pushed