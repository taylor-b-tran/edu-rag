# Sprint 5 Status Table

**Task:** S5-T16
**Owner:** Tai Huynh
**Sprint window:** 14 May – 28 May 2026
**Last updated:** 24 May 2026

> Status key: **Done** = file/PR/result exists and reviewed · **Ongoing** = work in progress with clear next step · **Not started** = no work begun · **Blocked** = waiting on another task or external dependency.
> Update by editing this table directly. Keep evidence column to one canonical link per row.

---

## 1. Sprint 5 Task Roster

| ID | Task | Owner | Status | Evidence |
|---|---|---|---|---|
| S5-T01 | Sprint 5 technical boundary + kickoff plan | Thanh | Done | [`docs/sprint_5_kickoff.md`](sprint_5_kickoff.md) |
| S5-T02 | GitHub Actions CI workflow | Thanh | Done | [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) · merged PR #29 |
| S5-T03 | Docker demo readiness workflow | Thanh | Done | [`.github/workflows/docker-demo.yml`](../.github/workflows/docker-demo.yml) · merged PR #29 |
| S5-T04 | Sprint 5 integration gate | Thanh | Done | [`scripts/sprint5_integration_gate.py`](../scripts/sprint5_integration_gate.py) · merged PR #29 |
| S5-T05 | QA checklist | Tung | Done | [`docs/qa_checklist_sprint5.md`](qa_checklist_sprint5.md) · merged PR #32 |
| S5-T06 | CI test validation report | Tung | Done | [`docs/ci_test_validation_sprint5.md`](ci_test_validation_sprint5.md) · merged PR #37 |
| S5-T07 | Live 5-query benchmark runbook + execution | Tung + Tai | Done | [`docs/rag_benchmark_sprint5.md`](rag_benchmark_sprint5.md) §7 + [`rag_benchmark_sprint5_results.json`](rag_benchmark_sprint5_results.json) · retrieval 5/5, generation 3/5 |
| S5-T08 | Demo bug report | Tung + Tai | Done | [`docs/demo_bug_report_sprint5.md`](demo_bug_report_sprint5.md) |
| S5-T09 | WCAG contrast fixes | Anmoldeep | Done | [`apps/streamlit/main.py`](../apps/streamlit/main.py) · merged PR #36 |
| S5-T10 | Retrieval metadata + error state cards | Anmoldeep | Done | [`apps/streamlit/main.py`](../apps/streamlit/main.py) · merged PR #36 |
| S5-T11 | Session management + query/upload animations | Anmoldeep | Done | [`apps/streamlit/main.py`](../apps/streamlit/main.py) · merged PR #36 |
| S5-T12 | 6 A3 screenshots + narrative | Anmoldeep | Done | [`docs/a3_interface_demo/`](a3_interface_demo/) · merged PR #36 |
| S5-T13 | Setup / runtime notes | Tai | Done | [`docs/sprint5_runtime_notes.md`](sprint5_runtime_notes.md) |
| S5-T14 | A3 evidence index | Tai | Done | [`docs/a3_evidence_index.md`](a3_evidence_index.md) |
| S5-T15 | Implementation summary | Tai | Done | [`docs/sprint5_implementation_summary.md`](sprint5_implementation_summary.md) |
| S5-T16 | Sprint 5 status table (this doc) | Tai | Done | This file |
| S5-T17 | Seed corpus ingestion path | Ngoc | Done | [`src/document_processor/seed_documents.py`](../src/document_processor/seed_documents.py), [`ingest_corpus.py`](../src/document_processor/ingest_corpus.py) · merged PR #27 + #31 |
| S5-T18 | Ollama generation wired into API | Ngoc | Done | [`src/api/routes/query.py`](../src/api/routes/query.py), [`rag_pipeline.py`](../src/document_processor/rag_pipeline.py) · merged PR #35 |

## 2. Hygiene / Cross-cutting

| ID | Task | Owner | Status | Evidence |
|---|---|---|---|---|
| H-01 | Untrack `chroma_data/` binaries | Tai | Done | merged PR #33 |
| H-02 | Lazy `chromadb` import (CI without Docker) | Tung | Done | [`ingest_corpus.py:43`](../src/document_processor/ingest_corpus.py#L43) · merged PR #37 |
| H-03 | Fixture fallback when RAG generator fails | Tung | Done | [`src/api/state.py:46`](../src/api/state.py#L46) `_FixtureGenerator` · merged PR #37 |
| H-04 | Anmoldeep branch cherry-pick onto canonical paths | Tai | Done | merged PR #36 |

## 3. Acceptance Criteria coverage (from `sprint_5_kickoff.md` §9)

| ID | Criterion | Status | Evidence |
|---|---|---|---|
| S5-AC-01 | Every PR runs GitHub Actions CI | Done | `.github/workflows/ci.yml` triggered on every PR |
| S5-AC-02 | CI runs pytest + fails on regression | Done | `ci.yml` `Run pytest` step · 108/108 tests pass |
| S5-AC-03 | CI validates JSON fixtures + benchmarks | Done | `ci.yml` `Validate JSON artifacts` step |
| S5-AC-04 | CI validates Compose CPU + GPU | Done | `docker-compose-validate` job |
| S5-AC-05 | Manual Docker demo workflow smoke-tests services | Ongoing | `docker-demo.yml` exists; last full run 13 May; re-run after PR #35/#37 pending |
| S5-AC-06 | Demo runbook uses clean checkout | Done | [`README_docker.md`](../README_docker.md), `apps/integration/start.sh` |
| S5-AC-07 | ≥5 seeded queries return grounded answers + citations | Ongoing | Pipeline wired (PR #35); end-to-end execution under S5-T07 |
| S5-AC-08 | Off-topic returns clear course-grounded fallback | Done | `FALLBACK_LABEL` in `rag_pipeline.py`; `_FixtureGenerator` fallback path |
| S5-AC-09 | Ambiguous questions ask for clarification / low-confidence | Not started | Confidence label exists; explicit clarification prompt not yet added |
| S5-AC-10 | Live 31-query benchmark separated from fixture-mode | Ongoing | Fixture benchmark in `rag_config_benchmark_31q.json`; live results pending S5-T07 |
| S5-AC-11 | A3 demo script states implemented / fixture / planned | Not started | Will be produced in S5-T15 |
| S5-AC-12 | No secrets / cache / agent artifacts committed | Done | `.gitignore` covers `chroma_data/`, `data/samples/`, `.agents/`, `.ai/`, `AGENTS.md`; integration gate validates |
| S5-AC-13 | Sprint 4 handoff PR includes all required artifacts | Done | merged PR #22, #23, #24 |

## 4. Workstream coverage (from `sprint_5_kickoff.md` §5)

| ID | Workstream | Status | Notes |
|---|---|---|---|
| W1 | GitHub CI workflow | Done | S5-T02 |
| W2 | Docker demo readiness workflow | Done | S5-T03 |
| W3 | Demo stack packaging | Ongoing | Thanh's part done; Tai S5-T13 in progress |
| W4 | Live RAG seed path | Done | S5-T17 + S5-T18 merged; execution under S5-T07 |
| W5 | API/UI demo flow | Done | S5-T09..T12 merged in PR #36 |
| W6 | Benchmark + test evidence | Ongoing | Fixture-mode done; live benchmark pending |
| W7 | A3 evidence pack | Ongoing | T13/T14/T15/T16 in progress |

## 5. Remaining work after 24 May (snapshot)

| Item | Owner | Target |
|---|---|---|
| Re-run QA checklist Sections 4+5 (Live RAG / Citations) | Tung | 25 May (data ready in `rag_benchmark_sprint5.md` §7) |
| Demo rehearsal | Whole team | 26–27 May |
| A3 demo recording (GPU host preferred for hard queries) | Whole team | 27–28 May |
| Sprint 5 sponsor review note | Thanh | 27 May |
| Tech debt: rename `test_query_returns_fixture_answer_when_authenticated` + add real assertions | Ngoc | 26 May |
| Optional: pull `qwen3:14b` and rerun benchmark on a GPU host | Whoever has GPU | Before 28 May |
