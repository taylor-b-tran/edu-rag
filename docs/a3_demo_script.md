# Assessment 3 Demo Script (Sprint 5 Recording)

**Task:** S5-AC-11 (A3 demo script labels each step as implemented / fixture / planned)
**Owner:** Tai Huynh
**Sprint:** 5 (14 May – 28 May 2026)
**Last updated:** 26 May 2026
**Recording window:** 27 – 28 May 2026
**Demo host:** GPU-enabled (NVIDIA RTX 5060, 8 GB VRAM) — see `sprint5_runtime_notes.md` §6

> Use this script as the narration backbone for the A3 video. Every spoken claim must match a state label in this file so the panel can tell what is live, what is fixture-backed, and what is planned for the next sprint.

---

## Pre-recording checklist (15 min before)

| # | Action | Why |
|---|---|---|
| 1 | `docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d` | Ensure Ollama runs on GPU (without overlay it silently falls back to CPU and queries take 96 s+) |
| 2 | `docker exec edurag-ollama-1 nvidia-smi` | Confirm RTX 5060 visible inside container |
| 3 | Warm Ollama: send one throwaway query to load `llama3.2` into VRAM (avoids ~40 s cold-start on first recorded query) | Hidden in screen recording |
| 4 | Browser to `http://localhost:8501`, clear cache, full-screen | Clean UI for capture |
| 5 | Open second tab to GitHub Actions and one to `docs/rag_benchmark_sprint5.md` | For steps 1 and 10 |

---

## 1. CI status — **Implemented**

**Action:** Open GitHub Actions, show latest green run on `develop`.

**Narration:**
> "Every pull request to `develop` triggers our CI workflow. It runs the 108-test pytest suite, validates JSON fixtures, compiles all Python modules cold, and validates both the CPU and GPU Docker Compose files. The latest run on `develop` is green — that's our gate before any code reaches the demo branch."

**Evidence:** `.github/workflows/ci.yml`, latest run URL (paste during recording).

---

## 2. Compose validation — **Implemented**

**Action:** `docker compose -f docker-compose.yml config | head -40`

**Narration:**
> "The Compose file resolves cleanly with no environment-variable gaps. This is the same validation CI runs on every PR — it's how we catch drift between the demo file and the documented runtime contract."

**Evidence:** `docker-compose.yml`, `docker-compose.gpu.yml` overlay (GPU-only line).

---

## 3. Stack startup — **Implemented**

**Action:** Show `docker compose ps`; all 5 services healthy.

**Narration:**
> "Five services: Postgres for persistence, ChromaDB as the vector store, Ollama as the local LLM, the Flask API as the orchestration layer, and Streamlit as the front end. The stack starts from a clean checkout in under five minutes once the Ollama model is cached."

**Evidence:** `docker compose ps` output.

---

## 4. Login as student — **Implemented (fixture-backed auth)**

**Action:** Streamlit at `http://localhost:8501`. Log in with `student@uow.edu.au / student123`.

**Narration:**
> "Login is currently fixture-backed — demo accounts come from `sample_responses.json` rather than a Postgres `users` table. Auth flow, role enforcement, and JWT token issuance are all real; only the user store is in-memory. Postgres-backed users land in Sprint 6."

**Label:** Auth flow = **Implemented**; user store = **Fixture-backed**; Postgres-backed users = **Planned (Sprint 6)**.

---

## 5. Grounded query — **Implemented (live RAG)**

**Action:** Ask *"What is Retrieval-Augmented Generation?"*

**Expected response:** Answer cites `Week1_RAG_Introduction.pdf p.1` at similarity ≈ 0.68, returns in 8–15 s on the GPU host.

**Narration:**
> "This is the real RAG pipeline. The query goes to ChromaDB, which returns the top-5 most similar chunks from the seeded CSIT321 corpus. Those chunks are formatted into a prompt and sent to llama3.2 running on Ollama. The answer cites the source document and page number directly from the retrieval metadata — there's no fabrication. Confidence is calculated from the average similarity of the retained chunks."

**Label:** **Implemented** — see `rag_pipeline.py` `VectorRetriever.search()` + `LLMResponseGeneration.generate()`.

---

## 6. Off-topic query — **Implemented (fallback path)**

**Action:** Ask *"Best chocolate cake recipe?"*

**Expected response:** `FALLBACK_LABEL` text, zero source references, `is_fallback=true`.

**Narration:**
> "When no chunk passes our similarity threshold of 0.35, the system declines to answer rather than hallucinate. No fake citations, no made-up sources. This is the fallback path — important for trust because students will absolutely try to use Paedia as ChatGPT."

**Label:** **Implemented** — `FALLBACK_LABEL` in `rag_pipeline.py`.

---

## 7. Login as lecturer — **Implemented**

**Action:** Log out, log in as `lecturer@uow.edu.au / lecturer123`. Show upload button now visible.

**Narration:**
> "Same authentication flow, different role. The lecturer role exposes the upload control that students don't see — role-based access control is enforced at the API layer, not just the UI."

**Label:** **Implemented** — RBAC test `test_upload_returns_403_for_student_role` ✅.

---

## 8. Document upload — **Implemented (queue) + Fixture-backed (indexing worker)**

**Action:** Pick any sample PDF, upload it. Show `indexing_status: queued` in the documents list.

**Narration (must say this part explicitly):**
> "Upload returns 202 Accepted and queues an indexing job. **The chunker and embedder exist as standalone tested components, but the queue worker that runs them is fixture-backed in Sprint 5.** What this means for the demo: a lecturer's upload right now does not appear in retrieval results — only the seeded corpus does. Wiring the chunker into the queue worker is the first task of Sprint 6."

**Label:** Upload + RBAC + queue = **Implemented**; queue worker → ChromaDB ingestion = **Fixture-backed**; full upload-to-retrieval = **Planned (Sprint 6)**.

---

## 9. Session history — **Implemented (in-memory)**

**Action:** Show prior queries persist for the session.

**Narration:**
> "Sessions are maintained in-memory in the API state for Sprint 5 — they survive between queries but not API restarts. The PostgreSQL schema for sessions and messages is already in `db/migrations/` and lands in Sprint 6."

**Label:** Session display = **Implemented**; persistence = **Planned (Sprint 6)**.

---

## 10. Benchmark summary — **Implemented**

**Action:** Open `docs/rag_benchmark_sprint5.md`, show the 5-query results table.

**Narration:**
> "We ran a 5-query benchmark across the seeded corpus: 2 easy factual, 1 hard reasoning, 1 procedural, 1 off-topic. Retrieval correctly handled all 5 — citations matched the expected source documents, and the off-topic query correctly returned zero chunks above threshold. The CPU baseline showed 2 generation timeouts on hard-reasoning prompts; after enabling GPU (RTX 5060) on the demo host, all 5 complete inside the LLM timeout in 8 to 30 seconds. A 14-billion-parameter benchmark on a higher-VRAM machine is the next data point."

**Label:** 5-query benchmark = **Implemented**; 31-query live benchmark = **Implemented (fixture-mode) / Planned (live extension)**; `qwen3:14b` extension = **Planned (separate GPU host)**.

---

## 11. Limitations + next sprint — **Honesty checkpoint**

**Action:** Read `sprint5_implementation_summary.md` §5 verbatim or paraphrase the five rows.

**Narration:**
> "We are explicit about what is live and what is fixture-backed: (1) the demo GPU is 8 GB VRAM, so qwen3:14b runs on a separate machine; (2) seeded corpus is 18 chunks across Weeks 1–7, not the full CSIT321 lecture set — that's a Sprint 6 ingestion task; (3) lecturer uploads queue but don't yet flow to ChromaDB — also Sprint 6; (4) auth and sessions are in-memory — the Postgres schema is staged; (5) ambiguous-question clarification is a confidence label only — an explicit clarification prompt is deferred."

**Label:** All five limitations = **Planned (Sprint 6 or deferred)**, all documented.

---

## State-summary table

| Step | Capability | State |
|---|---|---|
| 1 | CI pipeline | Implemented |
| 2 | Compose validation | Implemented |
| 3 | Stack startup | Implemented |
| 4 | Auth flow | Implemented |
| 4 | User store | Fixture-backed |
| 5 | Live ChromaDB retrieval | Implemented |
| 5 | Ollama generation with citations | Implemented |
| 6 | Off-topic fallback | Implemented |
| 7 | Role-based access control | Implemented |
| 8 | Upload + queue + RBAC | Implemented |
| 8 | Indexing worker → ChromaDB | Fixture-backed |
| 9 | Session display | Implemented |
| 9 | Session persistence | Planned (Sprint 6) |
| 10 | 5-query live benchmark | Implemented |
| 10 | 31-query live benchmark | Planned |
| 10 | `qwen3:14b` benchmark | Planned (separate GPU host) |
| 11 | Limitations declared | Implemented (doc) |

---

## Failure-mode contingencies (rehearse these)

| If… | Then… |
|---|---|
| Ollama cold-start takes 40 s on first query | Warm-up before recording — never on camera |
| ChromaDB returns 0 chunks for an on-topic query | Lower `SIMILARITY_THRESHOLD` to 0.25 temporarily and explain in narration |
| Container collision on `edurag-chromadb` | `docker rm -f edurag-chromadb edurag-ollama-cpu edurag-postgres` — see `sprint5_runtime_notes.md` §8 |
| Upload UI shows "indexing complete" instead of "queued" | The state label is the literal demo — narrate the fixture-backed line anyway, show the JSON response in network tab |

---

## Post-recording

1. Cut the warm-up query from the start of the recording.
2. Verify every "implemented" call-out in the narration matches a green check in this script.
3. Upload to the shared drive; paste the link into `a3_evidence_index.md` §11.
