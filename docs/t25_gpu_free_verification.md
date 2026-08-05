# T25 — Base Compose GPU-Free Verification

**Task:** T25
**Owner:** Thanh Binh Tran
**Sprint:** 6 (27 Jul – 7 Aug 2026)
**Due:** 30 Jul 2026 (completed 1 Aug — overdue by 2 days, backfilled)
**Branch:** `feature/s6-thanh-t25-gpu-free-default`

## Why this run happened

T26 (Tung, PR #48, `docs/dry_run_1_cold_grader.md`) ran a genuine cold-grader dry run on 29 Jul and got a **FAIL**: on his no-GPU Windows laptop, the API tried to warm up and generate with `qwen3:14b` (the shipped `.env.example` default), which timed out on pull and then 404'd on generate. Both errors (`DR1-01`, `DR1-02`) were assigned to Thanh. This document is that fix, verified against a real Docker run.

## Root cause

1. `.env.example` shipped `DEFAULT_OLLAMA_MODEL=qwen3:14b` — wrong default for any machine without a ≥12 GB GPU, which includes most graders.
2. `docker-compose.yml` sets the container's `OLLAMA_MODEL` from `${DEFAULT_OLLAMA_MODEL:-llama3.2}` — so once `.env` sets `DEFAULT_OLLAMA_MODEL` at all (which the shipped `.env.example` always does), the `llama3.2` fallback never triggers. Both `warmup.py` (which also prefers `DEFAULT_OLLAMA_MODEL` over `OLLAMA_MODEL`) and `rag_pipeline.py` ended up pointed at `qwen3:14b`.
3. Separately, `rag_pipeline.py::_call_ollama()` had a hardcoded `timeout=120` on the generate request, shorter than the README's own documented worst case of ~180s for CPU-only queries — a real (distinct) failure mode even after fixing (1)+(2).

## Fixes applied

| File | Change |
|---|---|
| `.env.example` | `DEFAULT_OLLAMA_MODEL` default changed from `qwen3:14b` to `llama3.2`. Does not affect GPU users who run `scripts/start_stack.ps1` (it overwrites `.env` based on detected VRAM regardless of this default). |
| `src/document_processor/rag_pipeline.py` | `_call_ollama()` timeout raised `120` → `240`; added a dedicated `requests.exceptions.Timeout` handler with a clear message pointing to the README hardware section, instead of falling through to the generic `[LLM Error: ...]` raw-exception string. |

## Verification (this machine, base compose only, no `-f docker-compose.gpu.yml`)

Host has an NVIDIA GPU, but the Ollama container has none (confirmed: `nvidia-smi` not found inside the container) — base compose genuinely does not request GPU access, matching what a no-GPU grader machine would experience.

| Step | Result |
|---|---|
| `docker compose up -d --build` | PASS — all 5 services started |
| `docker compose ps` | PASS — postgres, api, streamlit report `healthy`; chromadb, ollama running |
| `docker compose exec ollama nvidia-smi` | Confirmed no GPU access from the container (expected for base compose) |
| `/api/health` warmup | PASS — `model: llama3.2`, `pulled: true`, `generated: true`, `elapsed_ms: 12079` (after llama3.2 already cached from first run) |
| `/api/auth/login` (student) | PASS |
| `/api/query` — "What is Retrieval-Augmented Generation?" (`course_id=CSIT321`) | **PASS** — grounded answer citing `Week1_RAG_Introduction.pdf p.1`, confidence Medium (0.451), 5 source references from the seeded corpus, `backend_mode=chromadb`, `model_used=llama3.2` |
| `/_stcore/health` (Streamlit) | PASS |

**Before fix (reproduced first, same machine/session):** the same query returned `"answer": "[LLM Error: HTTPConnectionPool(host='ollama', port=11434): Read timed out. (read timeout=120)]"` after 143s — retrieval/citations worked, but the raw exception leaked to the user and no answer was produced.

**After fix:** real answer, 208.6s latency (~3.5 min). Retrieval and citation logic were never broken — this was purely a model-selection + timeout configuration issue.

## Merge with concurrent Sprint 6 work (Ngoc, PR #49)

While this fix was in progress, `origin/develop` advanced via PR #48 (Tung — T26 cold grader dry run log, see above) and PR #49 (Ngoc — T07/T08 evidence-cited/few-shot prompt strategies + tuned generation params). PR #49 modified the same `_call_ollama()` function. Merged manually (`git stash` → `git merge origin/develop` → `git stash pop` → resolve): kept Ngoc's dynamic `OLLAMA_TEMPERATURE`/`OLLAMA_TOP_P`/`OLLAMA_NUM_PREDICT` env-driven options (now defaulting `num_predict` 512 → 220, which should help latency) and layered the `timeout=120→240` change plus the new `Timeout` handler on top. No content from either side was dropped.

**Post-merge regression check:** `docker compose exec -T api python -m pytest test -q` → **118 passed, 0 failed, 10:33 min** (up from 112 baseline — the +6 are Ngoc's new `test_prompt_strategy.py` tests, all passing).

**Post-merge query re-verification — methodology note:** the first re-test was run *while the full pytest suite was still executing in the background* and showed 273s, exceeding the 240s timeout (the new graceful `Timeout` handler correctly caught this and returned retrieved context instead of a raw error — itself a good sign the fix works). That number was discarded as contaminated: two processes were competing for the same single Ollama instance. Re-running in isolation (nothing else hitting Ollama) gave a clean result:

- **218.6s latency**, real grounded answer with inline `[S1]` citation (Ngoc's new evidence-cited prompt format), `Week1_RAG_Introduction.pdf`, confidence Medium (0.451), `model_used=llama3.2`.

## Residual risk — flag for the team, not silently fixed

Clean, isolated CPU-only latency is consistently in the 208–219s range — within the new 240s timeout but above the README's advertised 60–180s range and close to the ceiling. This machine ran base compose on CPU only (GPU was available but not passed through, matching a true no-GPU grader). If the actual grading machine is slower, or the demo asks a longer/more complex question, a timeout is still plausible. Recommendation for the team:

- For the **A4 demo recording**, use a GPU host (or the `docker-compose.gpu.yml` overlay) rather than relying on this CPU path — the CPU path is now *correct*, not necessarily *fast*.
- **Do not run other Ollama-heavy processes (e.g. the full pytest suite) at the same time as a live demo query** — the false 273s reading above is a real example of how contention alone can push a borderline-timeout config over the edge.
- If T09 (vector DB/embedding optimisation) is explored further, or `num_predict` is tuned down again, re-measure this number — do not assume the fix here means CPU latency is solved, only that it no longer silently fails.

## Sign-off

- [x] Root cause confirmed via source inspection, not guessed
- [x] Both DR1-01 and DR1-02 reproduced before the fix, then re-verified fixed after
- [x] Merged cleanly with Ngoc's concurrent PR #49, conflict resolved by hand, nothing dropped
- [x] `docker compose exec -T api python -m pytest test -q` — 118 passed, 0 failed (post-merge)
- [x] Live query re-verified in isolation post-merge — 218.6s, real cited answer
- [ ] Not yet pushed / PR not yet opened — pending user confirmation
