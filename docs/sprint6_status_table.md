# Sprint 6 Status Table

Owner: Tai Huynh (T15)
Last updated: 5 Aug 2026 (T16, T17, T19, T20, T21, T31 done — full system QA pass also completed; slide deck and demo script finalised for the workshop). **Presentation confirmed: Week 15 workshop, 5 Aug, 1:30 PM, 6-minute presentation + 2-minute Q&A, whole team must attend.** Written-submission deadline (zip/README) not yet separately confirmed — check whether it's the same date or later via Moodle / Prof. Jun Yan.

> Status key: **Done** = artifact exists and verifiable · **Draft** = real artifact exists but needs owner review before final · **Overdue** = past its due date, not started · **Not started** · **Blocked** = waiting on another task.

## Done (25/34)

| ID | Owner | Task | Evidence |
|---|---|---|---|
| T01 | Thanh | Sprint 6 kickoff meeting | Confirmed 27 Jul |
| T02 | Thanh | Confirm spring-session meeting with Prof. Jun Yan | Confirmed 28 Jul |
| T03 | Andre | Draft RTM skeleton | `docs/rtm_a4.md` (folded into T04) |
| T04 | Andre + Thanh | Fill RTM status per requirement | `docs/rtm_a4.md`/`.docx`, PR #50 |
| T05 | Andre | Review/update ERD + sequence diagrams | `docs/architecture/*_sprint5.md/.svg`, PR #50 |
| T06 | Andre | Update System Design Document | Section 15 added, PR #50 |
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
| T30 | Thanh (picked up from Tai) | "For the Marker" README section | README.md §19, PR #53 |
| T31 | Thanh | Cold grader dry run #2 (final) | `docs/dry_run_2_cold_grader.md` — fresh clone, isolated Compose project, CPU-only path confirmed working from zero |
| T16 | Thanh (picked up from Tai) | Compile `docs/a4_evidence_index.md` | `docs/a4_evidence_index.md` |
| T17 | Thanh (picked up from Tai) | Branding consistency check | Checked product/team/group naming across README, RTM, status docs — consistent, no fixes needed |
| T21 | Thanh | Package code + README | `submission/edurag-paedia-a4-51c103a.zip` — built via `git archive`, trimmed of internal-only docs via `.gitattributes` (136 files, 6.25MB), extraction and link integrity verified |
| T19 | Thanh (picked up from Andre) | Write A4 report | `docs/a4_report.docx` — final, checked against the A4 marking rubric (added a Methodology section, design rationale, and a dedicated Interface Design section); Andre still welcome to review |
| T20 | Thanh (picked up from Andre) | Prepare A4 slides | Real 12-slide deck built, timed to the actual 6-minute workshop slot (kept locally, not pushed to the repo); Andre still welcome to tweak content before presenting |

## In progress — recording done, post-production pending (3)

| ID | Owner | Task | Was due | Risk |
|---|---|---|---|---|
| T18a | Andre + Tai | Live Paedia vs. generic-LLM comparison + recording | 30 Jul | **Recording confirmed done (4 Aug)** — footage exists, not yet processed |
| T18b | Tai | Compute comparison numbers from T18a | 31 Jul | Can start now that T18a footage exists |
| T18c | Andre | Edit + publish comparison video | 2 Aug | Can start now that T18a footage exists |

## Due within 2 days (2–3 Aug), not started (1)

| ID | Owner | Task | Due |
|---|---|---|---|
| T18d | Tai | Finalise public one-pager | 3 Aug (blocked by T18b/c) |

## Due 5 Aug, not started (2)

| ID | Owner | Task | Due |
|---|---|---|---|
| T13 | Tung | Regression QA on all Sprint 6 changes | 5 Aug |
| T14 | Tung | Collect spring-session meeting evidence | 5 Aug |

## Due 6–8 Aug, not started (3)

| ID | Owner | Task | Due |
|---|---|---|---|
| T28 | Tung | Verify submission zip contents | 6 Aug |
| T22 | Tung | Independently verify zip + README | 7 Aug |
| T23 | All | Rehearsal | 8 Aug — needs the whole team live, can't be done solo |

## Notes

- `develop` is at `6f25f75` (PR #54 merged 4 Aug — GPU 3-tier auto-select, beyond the original 34-task list); `CI` green, 118/118 tests passing.
- A full system QA pass (CI/CD, backend endpoints across all 3 roles, frontend, no console errors) was run 5 Aug alongside the remaining tasks — see `docs/vv_full_app_report_2026-08-03.md` and `docs/dry_run_2_cold_grader.md` for the write-ups.
- T11, T12, T16, T17, T19, T20, T30, and T31 were all unstarted past their due dates with no sign the original owners had picked them up, so Thanh did them directly to avoid slipping this close to the deadline. T19 (report) is still marked **Draft** — needs Andre's review before final. T20 (slides) now has an actual deck built, not just an outline; Andre is still welcome to review the content.
- **T18a (the live comparison recording) is done as of 4 Aug.** What's left on that workstream (T18b numbers, T18c edit/publish, T18d one-pager) is post-production, not a live-capture risk — can run in parallel now. Note: this is a separate marketing/comparison video, not the workshop presentation itself.
- Everything remaining is Tung's QA/verification tasks (T13, T14, T22, T28) plus the team rehearsal (T23) — and now, presenting today at 1:30 PM.
- System approved by Professor Jun Yan in an official meeting this morning (9:30 AM, 5 Aug). The presentation itself isn't reviewed by the supervisor — that's the subject coordinator's call, not Prof. Jun Yan's.
- `Team_Contributions/` updated to cover Sprint 4-6 for all members (previously only had Sprint 3 entries), attributed per original sprint-plan ownership rather than who ended up executing late tasks. The `Namaratne` folder was renamed to `Andre` — same person, current preferred name.
