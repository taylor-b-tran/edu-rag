# Sprint 6 Status Table

Owner: Tai Huynh (T15)
Last updated: 3 Aug 2026 (T10, T11, T12, T24 done). Deadline still assumed ~8 Aug — **confirm with Prof. Jun Yan / Moodle.**

> Status key: **Done** = artifact exists and verifiable · **Overdue** = past its due date, not started · **Due soon** = due within 3 days, not started · **Not started** · **Blocked** = waiting on another task.

## Done (18/34)

| ID | Owner | Task | Evidence |
|---|---|---|---|
| T01 | Thanh | Sprint 6 kickoff meeting | Confirmed 27 Jul |
| T02 | Thanh | Confirm spring-session meeting with Prof. Jun Yan | Confirmed 28 Jul |
| T03 | Andre | Draft RTM skeleton | `docs/rtm_a4.md` (folded into T04) |
| T04 | Andre + Thanh | Fill RTM status per requirement | `docs/rtm_a4.md`/`.docx`, PR #50 |
| T05 | Namaratne | Review/update ERD + sequence diagrams | `docs/architecture/*_sprint5.md/.svg`, PR #50 |
| T06 | Namaratne | Update System Design Document | Section 15 added, PR #50 |
| T07 | Ngoc | Model fine-tuning investigation | PR #49 — evidence-cited/few-shot prompt strategies |
| T08 | Ngoc | Benchmark before/after fine-tuning | PR #49 — `docs/finetuning_benchmark_sprint6.md/.json` |
| T15 | Tai | Create this file | PR #50 |
| T25 | Thanh | Base compose runs GPU-free | PR #50 — `.env.example` fix, verified via Docker |
| T26 | Tung | Cold grader dry run #1 | PR #48 — `docs/dry_run_1_cold_grader.md`, found DR1-01/02 |
| T27 | Thanh + Tung | Fix all T26 errors | PR #50 — same commit as T25, both DR1-01/02 fixed and re-verified |
| T09 | Thanh | Vector DB chunking/embedding optimisation | `docs/t09_vector_db_optimisation.md` — batch encoding in seed ingest + live upload path, verified via real upload/query/cleanup |
| T29 | Thanh | One-command health-check script | `scripts/check_demo_ready.py` — tested both PASS and FAIL paths live |
| T10 | Thanh | Benchmark speed before/after (T09) | `docs/t10_embedding_benchmark.md` — 8.6x/15.5x speedup, measured live in the api container |
| T24 | Thanh | Confirm CI green on final commit | Confirmed green on develop @ 952ddb4 (PR #51) — re-check again right before code freeze |
| T11 | Thanh (picked up from Anmoldeep, unstarted at due date) | UI polish for tech expo | `docs/t11_t12_ui_polish.md` — fixed frozen-looking generation state + frontend/backend timeout mismatch, found via live testing |
| T12 | Thanh (picked up from Anmoldeep, unstarted at due date) | Before/after UI screenshots | `docs/t11_t12_ui_polish.md` — captured during T11 verification |

## Overdue — not started (2)

| ID | Owner | Task | Was due | Risk |
|---|---|---|---|---|
| T18a | Namaratne + Tai | Live Paedia vs. generic-LLM comparison + recording | 30 Jul | **High** — blocks T18b/c/d; needs a human to actually run + record the session, cannot be automated |
| T18b | Tai | Compute comparison numbers from T18a | 31 Jul | Blocked by T18a |

## Due within 2 days (2–3 Aug), not started (2)

| ID | Owner | Task | Due |
|---|---|---|---|
| T18c | Namaratne | Edit + publish comparison video | 2 Aug (blocked — T18a hasn't run yet) |
| T18d | Tai | Finalise public one-pager | 3 Aug (blocked by T18b/c) |

## Due 4–6 Aug, not started (7)

| ID | Owner | Task | Due |
|---|---|---|---|
| T30 | Tai | "For the Marker" README section | 4 Aug |
| T13 | Tung | Regression QA on all Sprint 6 changes | 5 Aug |
| T14 | Tung | Collect spring-session meeting evidence | 5 Aug |
| T16 | Tai | Compile `docs/a4_evidence_index.md` | 6 Aug |
| T17 | Tai | Branding consistency check | 6 Aug |
| T28 | Tung | Verify submission zip contents | 6 Aug |
| T31 | Thanh | Cold grader dry run #2 (final) | 6 Aug |

## Due 7–8 Aug, not started (5)

| ID | Owner | Task | Due |
|---|---|---|---|
| T19 | Andre | Write A4 report draft | 7 Aug |
| T20 | Andre | Prepare A4 slides | 7 Aug |
| T21 | Thanh | Package code + README | 7 Aug |
| T22 | Tung | Independently verify zip + README | 7 Aug |
| T23 | All | Rehearsal | 8 Aug |

## Notes

- `develop` is at `952ddb4` (PR #51 merged 2 Aug); `CI` is green on this commit. `Docker Demo Readiness` last ran green on `d9665a8` (PR #50) — it only triggers on docker/compose/env-file changes, and none have landed since.
- T11 and T12 were still unstarted past their due dates (3 Aug, 4 Aug) with no sign Anmoldeep had picked them up, so Thanh did them directly rather than risk them slipping further this close to the deadline.
- **T18a/b/c/d is now the single biggest risk** — it's the only remaining CRITICAL workstream where no code/doc progress can substitute for a human actually running the live comparison and recording it. Everything else remaining is either routine engineering (T13-T14, T16-T17, T28, T31) or writing (T19-T20) that can be parallelised across the team.
