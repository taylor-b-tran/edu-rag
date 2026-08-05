# Sprint 7 Plan

Owner: Thanh Binh Tran
Duration: 5 Aug – 18 Aug 2026 (13 days)
Source: Sprint 6 sponsor review meeting with Prof. Jun Yan, 5 Aug 2026 — see `docs/meetings/sprint6_sponsor_review.docx`

## Why this scope

Two items from the sponsor review turned out to be the same underlying work. The professor asked the team to make EduRAG configurable for multiple subjects and student cohorts, not just one fixed course. Separately, the Sprint 6 known-limitations list already flagged that 7 of 9 designed Postgres tables (users, courses, enrollments, etc.) aren't wired up. Building real multi-subject support means wiring exactly those tables — so Sprint 7's main technical track closes a known gap and delivers the sponsor's stretch goal at the same time.

The professor also confirmed the team is ahead of schedule and encouraged pursuing stretch goals over minor polish, so Sprint 7 runs two tracks in parallel rather than sequencing them.

## Team for Sprint 7

| Member | Focus this sprint |
|---|---|
| Thanh Binh Tran | Team lead, expanded task load — owns auth + API wiring end to end, coordination, final packaging |
| Andre (Kahavidanage Namaratne) | Data & architecture — schema design only (implementation handed to Thanh), RTM — plus marketing video (joint with Tai) |
| Anmoldeep Singh | UI / frontend |
| Tai Huynh | Support tasks — plus marketing video (joint with Andre) |
| Tung Phuong Anh Huynh | Testing / QA |
| Thi Hong Ngoc Nguyen | RAG / document processing, retrieval tuning and benchmarking |

## Track A — Multi-subject expansion (full depth)

| ID | Owner | Task | Depends on | Target |
|---|---|---|---|---|
| T01 | Andre | Design/extend Postgres schema for real `users`, `courses`, `enrollments` (design only) | — | 8 Aug |
| T02 | Thanh | Wire real authentication to Postgres, replacing the fixture-based auth in `src/api/state.py` | T01 | 10 Aug |
| T03 | Thanh | API CRUD for courses/enrollments, admin-manageable | T01 | 12 Aug |
| T04 | Thanh | Confirm the upload/ingest path scopes correctly to the selected course | T03 | 13 Aug |
| T05 | Anmoldeep | Subject-selector UI + admin course/user management panel | T03 (can start UI mockup earlier) | 14 Aug |
| T06 | Tung | Regression test the full multi-subject flow end to end | T04, T05 | 16 Aug |

Admin write actions (the other Sprint 6 known limitation — admin dashboard is read-only) are folded into T03/T05 rather than tracked separately, since it's the same course/user management work.

## Track B — Retrieval accuracy benchmark

| ID | Owner | Task | Target |
|---|---|---|---|
| T07 | Ngoc | Formal retrieval accuracy benchmark — labelled test set, precision/recall against the current pipeline | 13 Aug |

## Marketing video re-record (sponsor-mandated fix)

| ID | Owner | Task | Depends on | Target |
|---|---|---|---|---|
| T08 | Tai + Andre | Re-record comparison video: animations, slower mouse pacing, stronger problem-statement opening | — | 15 Aug |
| T09 | Tai | Update the public one-pager with the re-recorded video link | T08 | 16 Aug |

## Wrap-up

| ID | Owner | Task | Target |
|---|---|---|---|
| T10 | Thanh | Final QA pass, documentation update, sprint wrap-up | 17-18 Aug |

## Notes

- Andre's scope on T01 is design only — Thanh owns the actual auth/API implementation (T02, T03) that builds on it. Andre's remaining bandwidth goes to T08 (video re-record), which he and Tai are already doing well.
- Database hosting: sponsor confirmed free local or AWS free-tier is fine, no paid cloud infrastructure needed.
- T07 (retrieval benchmark) is independent of Track A and can run fully in parallel.
