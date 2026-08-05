# A4 Demo Video — Script & Shot List

**Target length:** 5:30–6:00
**Goal:** walk through the working prototype across all 3 roles (Student, Lecturer, Admin), showing real retrieval + generation, not slides.
**Narration language:** English (matches product/course audience).

---

## Pre-recording checklist (do this every time, in order)

Skipping this caused a real ~4-minute stall during testing today — GPU passthrough degrades over long container uptimes and silently falls back to CPU.

```powershell
# 1. Force Ollama to re-negotiate GPU (fixes silent CPU fallback)
docker compose restart ollama

# 2. Confirm everything is actually healthy before hitting record
python scripts/check_demo_ready.py

# 3. Warm the model once so the FIRST on-camera query isn't slow
curl -s -X POST http://localhost:11434/api/generate -d "{\"model\":\"qwen2.5:7b\",\"prompt\":\"hi\",\"stream\":false}" > $null

# 4. Make sure the seed corpus + course content are in a known state
docker compose exec api python -m src.document_processor.ingest_corpus --force
```

Also: record at a normal desktop window size (not a narrow/split window — text wraps badly below ~1200px), close other GPU-heavy apps (games, other browser tabs doing video), and record on whichever machine actually has the GPU tier you want to show off (mid or high tier — CPU-only will make every query feel like dead air on camera).

---

## Script

| Time | Screen / Action | Narration |
|---|---|---|
| 0:00–0:20 | Title card or login screen, Paedia logo visible | "This is Paedia — an AI course assistant that answers student questions using only the lecturer's own course material, with a citation for every answer. Here's the working prototype end to end." |
| 0:20–0:35 | Sign in as `student@uow.edu.au` | "Starting as a student." *(type email/password on camera, don't paste — feels more real)* |
| 0:35–1:25 | Q&A Chat: ask **"What is Retrieval-Augmented Generation and how does it differ from standard LLMs?"** | "I'll ask a real question. This isn't a demo script — it's a live call to ChromaDB for retrieval and a local LLM for generation." *(let the answer render on screen, then:)* "Notice it's not just an answer — every claim is tagged back to a source: file, page, and similarity score. If Paedia can't find a confident match, it says so instead of guessing." |
| 1:25–1:55 | Click **Session History** | "Every conversation is saved per course, so students can pick up where they left off." *(hover a past session, click Continue on one)* |
| 1:55–2:10 | Click **My Uploads** | "Students can see what material is loaded for their course — read-only, since only lecturers manage content." |
| 2:10–2:20 | Sign out | "Now switching roles." |
| 2:20–2:35 | Sign in as `lecturer@uow.edu.au` | |
| 2:35–3:35 | **Document Manager** → upload a real PDF | "As a lecturer, I can upload new material directly." *(drag a short PDF in, narrate while it processes)* "It's chunked, embedded, and indexed into the vector store live — watch the status go from queued to processing to indexed." |
| 3:35–4:05 | Back to Q&A Chat, ask a question that depends on the just-uploaded file | "Now I'll ask something only in the file I just uploaded." *(show the citation pointing at the new filename)* "The system picked it up immediately — no rebuild, no restart." |
| 4:05–4:15 | Sign out | |
| 4:15–4:30 | Sign in as `admin@uow.edu.au` | |
| 4:30–5:00 | **Admin Dashboard** | "Admins get a system-wide view — users, courses, and usage metrics across the platform." |
| 5:00–5:40 | Closing — back to a clean chat screen or logo | "Three roles, one grounded answer engine: retrieval you can verify, running on infrastructure the team controls end to end. That's Paedia." |

---

## Notes for whoever records

- **Type questions live**, don't paste — looks more authentic and gives the retrieval a natural beat to land on.
- If a query response takes more than ~5s on camera, pause narration rather than talking over dead air — cut the silence in editing instead.
- Use a **different course document** for the upload demo than what's already seeded, so the citation obviously traces to something just added on camera (a short 1–3 page PDF indexes fastest).
- Keep the confidence bar / citation chips fully visible in frame — that's the single most important visual proof point for the whole video.
- If recording on a CPU-only machine, cut the pre-roll checklist's Ollama-warm step and expect to edit out the wait — do **not** try to demo the wait itself as "the experience," it undersells the product.
