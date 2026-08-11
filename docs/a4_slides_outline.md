# A4 Slides — Content Reference

The actual deck is `a4_slides.pptx` (same folder). This file is the content/timing reference behind it — keep both in sync if either changes.

Total workshop slot: **6:00 presentation, then 2:00 Q&A**, whole team in attendance. 12 slides, timed so slide 7 (live demo) lines up with `a4_demo_video_script.md`.

| # | Time | Slide | Content |
|---|---|---|---|
| 1 | 0:00–0:15 | Title | Paedia — Group 19, Aletheia's Zetetes, CSIT321 Project 37 |
| 2 | 0:15–0:45 | Problem | Students ask AI tools course questions and get confident-sounding but unverifiable (sometimes wrong) answers. No way to check the source. |
| 3 | 0:45–1:15 | What Paedia does | upload → chunk → embed → retrieve → generate → **cite**. Every answer traces to a file + page. |
| 4 | 1:15–1:35 | Progress since A2/A3 | Fixture prototype (A3) → live pipeline (Sprint 5) → production-hardening (Sprint 6, 25/34 tasks). Points at `docs/rtm_a4.md`. |
| 5 | 1:35–1:50 | Architecture | As-implemented query path. What changed from the original design (ambiguous-question short-circuit, fallback path). |
| 6 | 1:50–2:00 | Honest data-model note | Only 2/9 designed Postgres tables are actually live; rest are fixture/in-memory. Said out loud, not left for a marker to find. |
| 7 | 2:00–4:45 | **Live demo** | Switch to the actual app — the centerpiece. Follows `a4_demo_video_script.md`: grounded student question → citation → lecturer uploads new material → asks about it live → citation updates immediately. |
| 8 | 4:45–5:05 | What's new this sprint | Batch-embedding speedup (8.6–15.5x), 3-tier GPU auto-select, 2 real UI bugs found+fixed via live testing, grading-machine safety confirmed via fresh-clone dry run. |
| 9 | 5:05–5:20 | Verification | 118/118 tests, CI green, full pass across all 3 roles, 2 independent cold-start dry runs. |
| 10 | 5:20–5:35 | Known limitations | Same 3 points as the report §6. |
| 11 | 5:35–5:50 | What's next | Marketing comparison video (recorded, post-production in progress), remaining Sprint 6 polish, later-sprint roadmap items not yet in scope. |
| 12 | 5:50–6:00 | Questions | Thank you / team. |

**Presenter note:** slide 7 should run from the actual browser, not a video, if the room's Wi-Fi/hardware allows — a recording of the same script is the fallback. Whoever presents should run `python scripts/check_demo_ready.py` and `docker compose restart ollama` right before walking in (see `a4_demo_video_script.md`'s pre-flight checklist).
