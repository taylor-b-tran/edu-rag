# Sprint 5 Sponsor Review Note

**Owner:** Thanh
**Sprint:** 5 (14 May – 28 May 2026)
**Status of this draft:** Ready for Thanh to finalise and send
**Last updated:** 26 May 2026

> Audience: project sponsor + supervisor. Purpose: a one-page snapshot of where EduRAG / Paedia is at the end of Sprint 5, what shifted from plan, what we'd ask the sponsor to back next.

---

## 1. What shipped

The Sprint 5 goal was to move Paedia from a Sprint 4 prototype that returned fixture answers into a demo-ready system where a CSIT321 query goes through real vector retrieval and a real LLM, with citations. **We met that goal.**

| Capability | Evidence |
|---|---|
| Live ChromaDB retrieval over seeded CSIT321 corpus (18 chunks, Weeks 1–7) | `docs/rag_benchmark_sprint5.md` §7 — 5/5 retrieval correct, citations grounded |
| Live Ollama generation (`llama3.2`) with file + page citations | `src/document_processor/rag_pipeline.py` `LLMResponseGeneration.generate()` |
| GPU-enabled demo host (NVIDIA RTX 5060) — Ollama latency 8–30 s/query | `docker-compose.gpu.yml` overlay; verified 25 May |
| End-to-end Docker Compose stack (Postgres, ChromaDB, Ollama, Flask API, Streamlit) | `docker-compose.yml`; 5 containers healthy; `docker compose up --build` reaches a working query in under 5 minutes |
| GitHub Actions CI on every PR (pytest 108/108, JSON validation, Compose validation) | `.github/workflows/ci.yml` — green on `develop` |
| Streamlit UI with WCAG-compliant contrast, retrieval metadata, session management | `apps/streamlit/main.py` — Anmoldeep PR #36 |
| Six A3 interface screenshots + narrative | `docs/a3_interface_demo/` |
| Fixture fallback path so the API never 5xx's on missing dependencies | `src/api/state.py` `_FixtureGenerator` (PR #37) |

## 2. What changed from the Sprint 5 plan

| Plan | Actual |
|---|---|
| Demo on CPU host with `qwen3:14b` | Demo host is GPU (RTX 5060, 8 GB VRAM); `qwen3:14b` doesn't fit cleanly — running `llama3.2` (3B) on GPU instead. `qwen3:14b` benchmark scheduled for a separate higher-VRAM machine. |
| Indexing worker wires uploaded documents into ChromaDB | Worker still queues only; chunker + embedder exist standalone and are tested, but the wiring is deferred to Sprint 6 (explicitly called out in the demo script as fixture-backed) |
| Postgres-backed auth and sessions | Both remain in-memory for Sprint 5 — schema is in `db/migrations/` ready for next sprint |
| Ambiguous-question clarification (S5-AC-09) | Confidence label is exposed in the UI; explicit "ask me to clarify" prompt is deferred — agreed acceptable trade-off given demo priorities |

## 3. Risks heading into A3 (28 May submission)

| Risk | Likelihood | Mitigation in place |
|---|---|---|
| Cold-start on first recorded query (~40 s to load model into VRAM) | High | Pre-warm Ollama before recording, cut warm-up from video |
| `qwen3:14b` GPU benchmark slips | Medium | Not a submission requirement; primary evidence is the 5-query `llama3.2` benchmark. The 14b run is a strengthening data point, not a critical path. |
| Lecturer-uploaded document doesn't appear in retrieval results during live demo | Low (we don't try) | Demo script step 8 narrates the fixture-backed worker explicitly; we never claim it works end-to-end |
| Supervisor asks for full CSIT321 lecture set in the corpus | Low | Documented limitation in `sprint5_implementation_summary.md` §5; chunker is tested for PDF/PPTX/DOCX so the path is short — Sprint 6 first task |

## 4. What we'd ask the sponsor to back for Sprint 6

In rough priority:

1. **Wire the indexing worker** so lecturer uploads land in ChromaDB. Closes the biggest fixture-backed gap and enables real lecturer testing.
2. **Postgres-backed auth + sessions.** Schema is ready; this unlocks multi-user testing and persistence across restarts.
3. **Ingest the full CSIT321 lecture set** through the existing chunker. Moves the benchmark from illustrative (18 chunks) to representative.
4. **Explicit ambiguous-question clarification path** (S5-AC-09 carried over).
5. **GPU procurement decision** if we want to demo `qwen3:14b` or larger models on the project host — current 8 GB ceiling forces a model trade-off.

## 5. Team and process notes

- Two-week sprint cadence held; all 16 named tasks completed by 26 May (24 + 4 hygiene tasks).
- CI gate caught two real regressions during the sprint (DEMO-001 conflict markers, DEMO-006 false-positive on `===` lines) — workflow is paying for itself.
- Cross-pairing worked well: Tung+Tai on QA + benchmark, Ngoc on the RAG wiring, Anmoldeep on UI, Binh on CI/Docker, Thanh on sprint planning + sponsor liaison.

## 6. Demo logistics

- Recording window: **27 – 28 May 2026** on the GPU demo host.
- Script: `docs/a3_demo_script.md` (11 steps, each labelled implemented / fixture-backed / planned).
- Recording team: whole team present, narration led by Thanh.
- Submission: A3 evidence pack indexed at `docs/a3_evidence_index.md`.

---

**Sign-off requested from sponsor:** acknowledgement that the fixture-backed items (indexing worker, auth store, session persistence, ambiguous-question prompt) are scheduled for Sprint 6 and acceptable for the A3 submission as documented limitations.
