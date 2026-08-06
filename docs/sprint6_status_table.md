# Sprint 6 Status Table

Owner: Tai Huynh (T15)
Last updated: 6 Aug 2026 (T13, T14, T22, T28 all landed — 29/34 done). Presentation held 5 Aug as scheduled. Written-submission deadline (zip/README) not yet separately confirmed — check whether it's the same date or later via Moodle / Prof. Jun Yan.

> Status key: **Done** = artifact exists and verifiable · **Draft** = real artifact exists but needs owner review before final · **Overdue** = past its due date, not started · **Not started** · **Blocked** = waiting on another task.

## Done (29/34)

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
| T21 | Thanh | Package code + README | `submission/edurag-paedia-a4-<commit>.zip` — built via `git archive`, trimmed of internal-only docs via `.gitattributes`, rebuilt on every content change; extraction, contents, and link integrity re-verified each time |
| T19 | Thanh (picked up from Andre) | Write A4 report | `docs/a4_report.docx` — final, checked against the A4 marking rubric (added a Methodology section, design rationale, and a dedicated Interface Design section); Andre still welcome to review |
| T20 | Thanh (picked up from Andre) | Prepare A4 slides | Real 12-slide deck built, timed to the actual 6-minute workshop slot (kept locally, not pushed to the repo); Andre still welcome to tweak content before presenting |
| T13 | Tung | Regression QA on all Sprint 6 changes | PR #59/#60 — `docs/regression_qa_sprint6.md`, 118/118 tests, no regressions vs. Sprint 5 |
| T14 | Tung | Collect spring-session meeting evidence | PR #57 — `docs/meetings/sprint5_sponsor_review.docx`, `sprint6_sponsor_review.docx` |
| T22 | Thanh (Tung hadn't started with the deadline close) | Independently verify zip + README | `docs/t22_t28_zip_verification.md` — ran the stack from the zip alone (no git), 118/118 tests, live query matched README's promised result |
| T28 | Thanh (Tung hadn't started with the deadline close) | Verify submission zip contents | `docs/t22_t28_zip_verification.md` — no secrets/`.env`/`.git`, all required deliverables present, no broken README links |

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

## Remaining (1)

| ID | Owner | Task | Due |
|---|---|---|---|
| T23 | All | Rehearsal | 8 Aug — needs the whole team live, can't be done solo |

## Notes

- `develop` is at `6f25f75` (PR #54 merged 4 Aug — GPU 3-tier auto-select, beyond the original 34-task list); `CI` green, 118/118 tests passing.
- A full system QA pass (CI/CD, backend endpoints across all 3 roles, frontend, no console errors) was run 5 Aug alongside the remaining tasks — see `docs/vv_full_app_report_2026-08-03.md` and `docs/dry_run_2_cold_grader.md` for the write-ups.
- T11, T12, T16, T17, T19, T20, T30, and T31 were all unstarted past their due dates with no sign the original owners had picked them up, so Thanh did them directly to avoid slipping this close to the deadline. T19 (report) is still marked **Draft** — needs Andre's review before final. T20 (slides) now has an actual deck built, not just an outline; Andre is still welcome to review the content.
- **T18a (the live comparison recording) is done as of 4 Aug.** What's left on that workstream (T18b numbers, T18c edit/publish, T18d one-pager) is post-production, not a live-capture risk — can run in parallel now. Note: this is a separate marketing/comparison video, not the workshop presentation itself.
- Presentation held 5 Aug, 1:30 PM as scheduled. System approved by Professor Jun Yan in an official meeting that morning (9:30 AM). The presentation itself isn't reviewed by the supervisor — that's the subject coordinator's call, not Prof. Jun Yan's.
- `Team_Contributions/` updated to cover Sprint 4-6 for all members (previously only had Sprint 3 entries), attributed per original sprint-plan ownership rather than who ended up executing late tasks. The `Namaratne` folder was renamed to `Andre` — same person, current preferred name.
- Tung landed T13 and T14 on 5-6 Aug. T22/T28 (zip/README verification) hadn't started with the deadline close, so Thanh ran both directly against the built zip — see `docs/t22_t28_zip_verification.md`. No blockers found; one real fixture inconsistency noted (login's `enrolled_courses` uses UUIDs, retrieval everywhere else uses string course codes) — doesn't affect the documented demo path, and gets resolved by Sprint 7's courses/enrollments work.
- Only T18b/c/d (marketing video post-production) and T23 (team rehearsal) remain.
