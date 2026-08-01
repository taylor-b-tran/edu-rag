# Sprint 6 Status Table

Owner: Tai Huynh (T15) — this file was overdue (due 27 Jul) and is created now, 1 Aug, backfilled against actual work done so far.
Last updated: 1 Aug 2026. Deadline still assumed ~8 Aug — **confirm with Prof. Jun Yan / Moodle.**

> Status key: **Done** = artifact exists and verifiable · **Overdue** = past its due date, not started · **Due soon** = due within 3 days, not started · **Not started** · **Blocked** = waiting on another task.

## Done (6/34)

| ID | Task | Evidence |
|---|---|---|
| T01 | Sprint 6 kickoff meeting | Confirmed by user, 27 Jul |
| T02 | Confirm spring-session meeting with Prof. Jun Yan | Confirmed by user, 28 Jul |
| T03 | Draft RTM skeleton | `docs/rtm_a4.md` |
| T04 | Fill RTM status per requirement | `docs/rtm_a4.md`/`.docx` — 33 FR + 8 NFR, 3 stale statuses corrected |
| T05 | Review/update ERD + sequence diagrams | `docs/architecture/seq_api_query_sprint5.md`/`.svg`, `erd_reconciliation_sprint5.md`/`.svg` — found and documented real drift |
| T06 | Update System Design Document | Section 15 added to `system_design_document_v2_source.md` and `EduRAG_System_Design_Document_v2.docx` |

## Overdue — was due before 1 Aug, not started (5)

| ID | Owner | Task | Was due | Risk |
|---|---|---|---|---|
| T15 | Tai | This file | 27 Jul | Low now — created today |
| T25 | Thanh | Base compose runs GPU-free | 30 Jul | **High** — untested, and this is the #1 grading risk |
| T26 | Tung | Cold grader dry run #1 | 30 Jul | **High** — blocks T27 |
| T18a | Namaratne + Tai | Live Paedia vs. generic-LLM comparison + recording | 30 Jul | **High** — blocks T18b/c/d, and marketing package is not public-ready without it |
| T18b | Tai | Compute comparison numbers | 31 Jul | Blocked by T18a |

## Due within 2 days (1–3 Aug), not started (7)

| ID | Owner | Task | Due |
|---|---|---|---|
| T27 | Thanh + Tung | Fix all T26 errors | 2 Aug (blocked — T26 hasn't run yet) |
| T18c | Namaratne | Edit + publish comparison video | 2 Aug (blocked by T18a/b) |
| T07 | Ngoc | Model fine-tuning investigation | 3 Aug |
| T09 | Thanh | Vector DB chunking/embedding optimisation | 3 Aug |
| T11 | Anmoldeep | UI polish for tech expo | 3 Aug |
| T29 | Thanh | One-command health-check script | 3 Aug |
| T18d | Tai | Finalise public one-pager | 3 Aug (blocked by T18b/c) |

## Due 4–6 Aug, not started (11)

| ID | Owner | Task | Due |
|---|---|---|---|
| T08 | Ngoc | Benchmark before/after fine-tuning | 4 Aug |
| T10 | Thanh | Benchmark speed before/after | 4 Aug |
| T12 | Anmoldeep | Before/after UI screenshots | 4 Aug |
| T30 | Tai | "For the Marker" README section | 4 Aug |
| T13 | Tung | Regression QA on all Sprint 6 changes | 5 Aug |
| T14 | Tung | Collect spring-session meeting evidence | 5 Aug |
| T24 | Thanh | Confirm CI green on final commit | 5 Aug — **GitHub Actions has not run since 27 May; nothing in this conversation's work has been committed/pushed yet either** |
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

## Additional flag not on the original task list

Every file produced in this Sprint 6 work session (`docs/rtm_a4.*`, `docs/architecture/*_sprint5.*`, the updated System Design Document, the Marketing Strategy docs) is a local, **uncommitted** change — `git status` shows them all as untracked/modified, nothing pushed. These need a commit + PR before T24 (CI check) or T21 (packaging) can be meaningfully done.
