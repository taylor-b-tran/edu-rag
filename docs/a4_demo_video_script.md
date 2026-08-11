# A4 Submission Video — Script & Shot List

This is the script for the demo video, whether it ends up recorded ahead of time as the actual video submitted for A4, or run live from the browser during the workshop if that's the format on the day. Same beats, same timing either way — **2:45**, sitting inside the "Live demo" slide of `a4_slides.pptx`. The full talking script for the rest of the presentation is in `a4_presenter_script.md`.

Not pushed to the repo — kept local for the team to work from.

---

## Before recording (or before walking into the room)

Skipping this caused a real ~4-minute stall during testing — GPU passthrough degrades over long container uptimes and quietly falls back to CPU.

```powershell
# 1. Force Ollama to re-negotiate GPU (fixes silent CPU fallback)
docker compose restart ollama

# 2. Confirm everything is actually healthy
python scripts/check_demo_ready.py

# 3. Warm the model once so the first question isn't slow
curl -s -X POST http://localhost:11434/api/generate -d "{\"model\":\"qwen2.5:7b\",\"prompt\":\"hi\",\"stream\":false}" > $null

# 4. Make sure the seed corpus is in a known state
docker compose exec api python -m src.document_processor.ingest_corpus --force
```

Use a normal desktop window size — text wraps badly below ~1200px. Close other GPU-heavy apps. Record or present from whichever machine has the GPU tier that gives fast answers; on CPU-only, every question turns into dead air.

---

## The two moments that matter

Everything else is scaffolding. If only two things land, they should be:

1. A student asks a real question and gets an answer with a citation attached.
2. A lecturer uploads something new and it's immediately queryable — no rebuild, no restart.

Session History and My Uploads are cut to make room for those two beats.

| Time | Action | What to say |
|---|---|---|
| 0:00–0:10 | Sign in as `student@uow.edu.au` | "Starting as a student." |
| 0:10–1:05 | Ask **"What is Retrieval-Augmented Generation and how does it differ from standard LLMs?"** | "This is a live call to ChromaDB for retrieval and a local LLM for generation, not a canned response." *(let the answer render, then point at the citation)* "Every claim is tagged back to a source — file, page, similarity score. If nothing in the course material clears the confidence threshold, it says so instead of guessing." |
| 1:05–1:20 | Sign out, sign in as `lecturer@uow.edu.au` | "Switching roles." |
| 1:20–2:10 | Upload a short PDF in Document Manager, then ask a question that depends on it | "As a lecturer I can add material directly — it's chunked, embedded, and indexed live." *(ask the question, point at the citation on the new filename)* "Picked up immediately." |
| 2:10–2:25 | Sign out, sign in as `admin@uow.edu.au` | "And finally, admin." |
| 2:25–2:45 | Admin Dashboard | "System-wide view across users, courses, and usage — that's all three roles." |

**Running short on time:** drop the admin beat first, then trim the lecturer narration. Keep the citation moment on both remaining beats no matter what — that's the point of the whole video.

---

## Recording notes

- Type the question live rather than pasting it — it gives retrieval a natural beat to land on and looks less staged.
- If a response takes more than ~5 seconds, pause instead of talking over dead air — cut the gap out in editing.
- Use a course document that isn't already in the seed corpus for the upload beat, so the citation obviously points at something just added on camera.
- Keep the citation and confidence chips fully visible in frame — that's the single most important thing for someone watching to actually see.
- On CPU-only hardware, don't try to demo the wait as part of the experience — narrate through it briefly and let editing shorten it, or cut that machine from consideration entirely.
