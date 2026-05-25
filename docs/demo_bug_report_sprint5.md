# Sprint 5 Demo Bug Report

**Task:** S5-T08
**Sprint:** 5 (14 May – 28 May 2026)
**Last updated:** 24 May 2026
**Sign-off target:** Demo freeze 27–28 May

> Log every observed defect found during Sprint 5 QA, integration, or rehearsal. Mark as **Open**, **Fix in progress**, or **Resolved** with the PR or commit reference. A failing item in `docs/qa_checklist_sprint5.md` must appear here before the demo freeze.

---

## Severity key

- **Blocker** — prevents demo recording or A3 evidence collection
- **High** — degrades the demo experience materially
- **Medium** — visible but does not block the script
- **Low** — cosmetic / cleanup

---

## 1. Active bugs

| ID | Severity | Title | Found | Owner | Status | Fix |
|---|---|---|---|---|---|---|
| _none currently open_ | | | | | | |

## 2. Resolved during Sprint 5

| ID | Severity | Title | Resolved | Fix |
|---|---|---|---|---|
| DEMO-001 | High | `requirements.txt` contained leftover `<<<<<<< HEAD` conflict markers, breaking CI install | 19 May | PR #30 (Tung) — remove conflict markers + restore `python-pptx`, `python-docx` |
| DEMO-002 | High | `/api/query` returned `backend_mode: "fixture"` regardless of ChromaDB state | 23 May | PR #35 (Ngoc) — switch route to call `_state().get_generator().generate(...)` |
| DEMO-003 | High | ChromaDB binary persistence files committed to `develop` after PR #31 | 22 May | PR #33 (Tai) — `git rm -r --cached chroma_data/` + `.gitignore` entry |
| DEMO-004 | High | `ingest_corpus.py` imported `chromadb` at module level, breaking CI when chromadb not installed | 23 May | PR #37 (Tung) — lazy import inside `get_chroma_client()` |
| DEMO-005 | High | API returned 5xx if `chromadb` package or ChromaDB service unavailable | 23 May | PR #37 (Tung) — `state.get_generator()` now wraps init in try/except with `_FixtureGenerator` fallback |
| DEMO-006 | Medium | Sprint 5 integration gate caught `===` separator lines in `ci_pytest_raw_sprint5.txt` as conflict markers | 23 May | PR #38 + #39 (Tung) — remove the raw output file from tracking |
| DEMO-007 | Medium | `docker-compose.yml` set `OLLAMA_BASE_URL` but `rag_pipeline.py` reads `OLLAMA_HOST` — API never reached Ollama inside Compose network | 24 May | This PR — rename to `OLLAMA_HOST` and add `OLLAMA_MODEL` env override |
| DEMO-008 | Low | `rag_pipeline._call_ollama` fallback message iterated `for c in []` instead of the retrieved chunks list, so citations were never printed in Ollama-down branch | 24 May | This PR — pass `chunks=good` from `generate()` |

## 3. Known limitations (not bugs, documented in `sprint5_implementation_summary.md` §5)

| Item | Behaviour | Documented in |
|---|---|---|
| Upload pipeline is queued only, not indexed | `/api/upload` returns `indexing_status: queued`, no chunker invoked | implementation_summary §3, §5 |
| In-memory sessions | Restart loses session history | implementation_summary §3 |
| CPU-bound LLM | First query 60–90 s, warm queries 10–30 s | implementation_summary §4.2 |
| No ambiguous-question clarification path (S5-AC-09) | Low-confidence answers still generated | implementation_summary §5 |

## 4. Open follow-ups (post-Sprint 5)

- Rename `test_query_returns_fixture_answer_when_authenticated` → split into `test_query_returns_grounded_answer_when_chromadb_available` + `test_query_falls_back_to_fixture_when_chromadb_unavailable`
- Wire the indexing-job worker to call `chunker.chunk_file()` → `embedder.embed_chunks()` → `collection.add(...)` for live uploads
- Add explicit "ask to clarify" code path when `confidence_score < 0.40`
- Pull `qwen3:14b` on a GPU host for higher answer quality
- `rag_pipeline.py` style refactor (one statement per line, docstrings) — defer until after A3

## 5. How to log a new bug

1. Reproduce locally if possible.
2. Add a row to §1 with the next `DEMO-NNN` ID, severity, short title, date, owner, and "Open".
3. If reproduction needs a code change, include the file path and line.
4. When fixed, move the row from §1 to §2 with the commit / PR reference.
5. Update the matching row in `docs/qa_checklist_sprint5.md` if it was a FAIL.
