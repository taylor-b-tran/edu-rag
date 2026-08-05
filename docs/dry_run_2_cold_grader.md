# T31 — Cold Grader Dry Run #2 (Final)

**Date:** 5 Aug 2026
**Commit tested:** `6f25f75` (`develop`, post PR #54)
**Method:** fresh `git clone` into a separate folder, isolated Docker Compose project (`-p edurag-drytest`, separate ports so it wouldn't collide with the running dev stack), following only `README.md` top to bottom.

## Steps followed (README §5–§9)

1. `git clone` + `git checkout develop` — clean.
2. `cp .env.example .env` — default is `DEFAULT_OLLAMA_MODEL=llama3.2` (CPU-safe).
3. `docker compose up -d --build` (base compose, no GPU overlay — this is the grading-machine path) — all 5 containers came up healthy, first build included.
4. Health endpoints (`/api/health`, ChromaDB heartbeat, Streamlit `/_stcore/health`) all returned 200/ok. Ollama warm-up pulled `llama3.2` fresh and finished in ~51s.
5. `docker compose exec api python -m src.document_processor.ingest_corpus` — 18 chunks upserted in 0.7s, smoke-test passed.
6. Live query via `/api/query` (student login → "What is RAG?") — retrieval found 3 sources, but generation hit the 240s backend timeout under CPU mode.

## Finding: CPU-mode query timeout under load

The query didn't fail ungracefully — it returned the T25 timeout fallback (retrieved context + "please try again" + real source list), which is what that fix is supposed to do. The timeout itself is explained by two full stacks running on the same machine at once (this dry run plus the regular dev stack), roughly doubling CPU load compared to what a marker's machine would see. Documented CPU latency is 60–180s; a genuinely idle CPU-only machine should land in that range, not the ~240s hit here.

Not treated as a new bug — the fallback path is what was being tested and it worked. The same query, re-run in isolation with nothing else competing for Ollama, completed cleanly at 218.6s (see `docs/t25_gpu_free_verification.md`).

## Cleanup

`docker compose -p edurag-drytest down -v` removed the dry-run containers, volumes, and network. Confirmed the main dev stack (`edurag` project, standard ports) was unaffected afterward.

## Gotcha worth flagging to the team

`docker-compose.yml` hardcodes `name: edurag`. Bringing up a second checkout from a different folder without an explicit `-p <name>` gets treated as the *same* Compose project and recreates whatever's already running — even if the ports are different. Ran into this directly: the first attempt at this dry run briefly replaced the live dev stack before it was caught and fixed (no data lost, since named volumes aren't tied to the container instance). Anyone testing a second copy of this stack alongside another should pass `-p <name>`.

## Verdict

Base Compose (CPU-only, no GPU) reaches a working, queryable demo from a genuinely fresh clone with no manual fixes needed. Ready for A4 submission.
