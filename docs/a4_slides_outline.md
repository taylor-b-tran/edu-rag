# A4 Slides — Outline (draft for Andre/team)

~10-12 slides, matches the [`a4_demo_video_script.md`](a4_demo_video_script.md) narrative so the deck and the live demo tell the same story.

| # | Slide | Content |
|---|---|---|
| 1 | Title | Paedia — Group 19, Aletheia's Zetetes, CSIT321 Project 37 |
| 2 | Problem | Students ask AI tools course questions and get confident-sounding but unverifiable (sometimes wrong) answers. No way to check the source. |
| 3 | What Paedia does | One diagram: upload → chunk → embed → retrieve → generate → **cite**. Every answer traces to a file + page. |
| 4 | Progress since A2/A3 | Fixture prototype (A3) → fully live pipeline (Sprint 5) → production-hardening this sprint (Sprint 6, 19/34 tasks). Point at `docs/rtm_a4.md`. |
| 5 | Architecture | As-implemented sequence diagram (`seq_api_query_sprint5.svg`). Call out what changed from the original design (ambiguous-question short-circuit, fallback path). |
| 6 | Honest data-model note | 1 slide, don't skip it: only 2/9 designed Postgres tables are actually live; rest are fixture/in-memory. Better to say it than have a marker find it. |
| 7 | Live demo | Switch to the actual app — this is the centerpiece, budget the most time here. Follow `a4_demo_video_script.md`'s beats: student asks a grounded question → lecturer uploads new material → ask about it live → citation updates immediately. |
| 8 | What's new this sprint (with evidence, not just claims) | Batch-embedding speedup (8.6-15.5x), 3-tier GPU auto-select, 2 real UI bugs found+fixed via live testing, grading-machine safety confirmed via fresh-clone dry run. |
| 9 | Verification | 118/118 tests, CI green, full V&V pass across all 3 roles, 2 independent cold-start dry runs. |
| 10 | Known limitations | Same 3 bullets as the report §6 — say them out loud before a marker asks. |
| 11 | What's next | T18 marketing comparison (recording done, post-production in progress), remaining Sprint 6 polish, A5/A6 roadmap items not yet in scope. |
| 12 | Questions | Contact/team slide. |

**Presenter note:** slide 7 (live demo) should be run from the actual browser, not a video, if the room's Wi-Fi/hardware allows — the video (`a4_demo_video_script.md`) is the fallback if live isn't feasible on presentation day. Whoever presents should run `python scripts/check_demo_ready.py` and `docker compose restart ollama` right before walking in (see the video script's pre-recording checklist — same advice applies to a live run).
