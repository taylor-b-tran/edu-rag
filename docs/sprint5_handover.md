# Sprint 5 Handover - Post-Fix QA Snapshot

**Project:** EduRAG / Paedia  
**Sprint:** 5 (14 May - 28 May 2026)  
**Last updated:** 26 May 2026  
**Branch at handover:** `feature/s5-gpu-model-autoselect`  
**Primary audience:** Sprint 5 demo / A3 evidence team  

> This handover captures the current state after the 26 May frontend + backend QA repair pass. It is intended to help the next teammate pick up the branch, understand what is fixed, what has been verified, and what still needs to happen before demo freeze.

---

## 1. Executive Status

The critical demo path has been repaired: Streamlit now logs in through the Flask API, receives a JWT, sends authenticated `/api/query` requests with a real `course_id`, and preserves the backend `session_id` across chat turns.

The live backend path has also been verified after rebuild. An authenticated CSIT321 query reached the RAG pipeline with:

| Field | Observed value |
|---|---|
| `backend_mode` | `chromadb` |
| `model_used` | `qwen3:14b` |
| `is_fallback` | `false` |
| `/api/health.mode` after query | `chromadb` |
| `/api/health.rag_available` after query | `true` |

No active demo blocker is known at this snapshot. The branch is not committed yet.

---

## 2. Current Working Tree

Modified repo files:

| Area | Files |
|---|---|
| Streamlit UI / API client | `apps/streamlit/main.py`, `apps/streamlit/api_client.py` |
| Flask API | `src/api/routes/query.py`, `src/api/routes/health.py`, `src/api/state.py` |
| RAG pipeline | `src/document_processor/rag_pipeline.py` |
| Wrappers / setup | `scripts/start_stack.ps1`, `scripts/start_stack.sh`, `.gitignore` |
| Tests | `test/test_api.py` |
| QA docs | `docs/demo_bug_report_sprint5.md`, `docs/qa_checklist_sprint5.md`, `docs/sprint5_handover.md` |

Parent planning memory was also updated outside the repo:

- `planning/reports/EduRAG_Project_Wrapup.md`

Local evidence note:

- `ci_pytest_raw_sprint5.txt` is Tung's QA evidence file. It is intentionally preserved locally.
- `.gitignore` now ignores `ci_pytest_raw_*.txt` so similar raw logs do not get committed accidentally.

---

## 3. What Was Fixed

| ID | Severity | Fix summary | Main files |
|---|---|---|---|
| B1 | Blocker | Streamlit login now calls Flask `/api/auth/login` first and stores the returned JWT. Fixture login is only a fallback when live API is unavailable. | `apps/streamlit/main.py`, `apps/streamlit/api_client.py` |
| B2 | Blocker | Chat state now defaults to `CSIT321`, exposes a course selector, and sends a non-empty `course_id` to `/api/query`. | `apps/streamlit/main.py` |
| M3 | Major | Backend `session_id` returned by `/api/query` is saved back into Streamlit state, so multi-turn chat can reuse the same backend session. | `apps/streamlit/main.py` |
| New blocker | Blocker | Fixed an import-time f-string `SyntaxError` in `rag_pipeline.py` that prevented ChromaDB mode from initialising. | `src/document_processor/rag_pipeline.py` |
| M1 | Major | PowerShell wrapper now writes `.env` as UTF-8 without BOM on Windows PowerShell 5.1. | `scripts/start_stack.ps1` |
| M2 | Major | `/api/health`, `/metrics`, and `/logs` now report dynamic backend mode instead of hardcoded `fixture`. | `src/api/state.py`, `src/api/routes/health.py` |
| m1 | Minor | `/api/query` now rejects non-object JSON bodies with HTTP 400 instead of raising 500. | `src/api/routes/query.py`, `test/test_api.py` |
| m2 | Minor | Suggested prompt loading is defensive if fixture keys are missing. | `apps/streamlit/main.py` |
| m3 | Minor | Bash wrapper avoids adding unnecessary blank lines when appending env values. | `scripts/start_stack.sh` |
| m4 | Minor | VRAM GB detection now rounds to nearest instead of truncating. | `scripts/start_stack.ps1`, `scripts/start_stack.sh` |
| m5 | Minor | New chat sessions now default to `CSIT321` instead of stale `CSIT214`. | `apps/streamlit/main.py` |
| m6 | Minor | Fixture generator docstring now reflects runtime fallback behaviour. | `src/api/state.py` |
| m7 | Minor | Raw CI/QA logs are ignored without deleting Tung's local file. | `.gitignore` |

Additional robustness changes:

- Streamlit API client no longer silently converts live API 4xx/5xx errors into fixture answers.
- Long RAG queries use `PAEDIA_QUERY_TIMEOUT`, default `180` seconds.
- Query calls disable retry to avoid repeating expensive LLM requests.
- Source rendering now accepts both old fixture-style and live backend citation metadata.
- Confidence rendering now handles both numeric scores and string labels such as `Medium`.

---

## 4. Validation Completed

| Check | Result | Notes |
|---|---|---|
| Python syntax compile | PASS | `py_compile` passed for modified Streamlit/API/RAG/test files |
| PowerShell parse | PASS | `scripts/start_stack.ps1` parsed successfully |
| `.env` BOM check | PASS | Local `.env` starts with `41-50-50-5F-45-4E`, not `EF-BB-BF` |
| Compose base config | PASS | `docker compose config --quiet` |
| Compose GPU config | PASS | `docker compose -f docker-compose.yml -f docker-compose.gpu.yml config --quiet` |
| Docker rebuild | PASS | `docker compose up -d --build` rebuilt API and Streamlit |
| Service health | PASS | API and Streamlit healthy; Postgres healthy; ChromaDB and Ollama running |
| Live API login | PASS | `student@uow.edu.au / student123` returned an access token |
| Live CSIT321 query | PASS | Authenticated query returned `backend_mode=chromadb`, `model_used=qwen3:14b`, `is_fallback=false` |
| Health mode after query | PASS | `/api/health` returned `mode=chromadb`, `rag_available=true` |
| Malformed JSON body | PASS | `/api/query` with JSON list body returns HTTP 400 |
| Backend session reuse | PASS | Inline API check reused one supplied `session_id` for two messages |
| Streamlit browser login | PASS | UI showed Student, Live API, and CSIT321 course selector |
| Streamlit API error rendering | PASS | Ambiguous-query response rendered without crashing |
| Diff hygiene | PASS | `git diff --check` returned exit code 0; only normal Windows LF/CRLF warnings remain |

Full pytest status:

- Earlier QA evidence reported the full suite passing on both branches.
- In this local shell, `python -m pytest test -q` cannot run because host Python lacks Flask.
- In the runtime Docker image, `pytest` is not installed because the image installs `requirements.txt` only.
- Container-side inline API regression checks were used to cover the changed API behaviours.

---

## 5. Current Stack State

At handover, the local Docker stack is running:

| Service | Status | Port |
|---|---|---|
| `api` | healthy | `5000` |
| `streamlit` | healthy | `8501` |
| `postgres` | healthy | `5432` |
| `chromadb` | running | `8000` |
| `ollama` | running | `11434` |

Useful URLs:

- Streamlit UI: <http://localhost:8501>
- API health: <http://localhost:5000/api/health>

Demo credentials:

| Role | Email | Password |
|---|---|---|
| Student | `student@uow.edu.au` | `student123` |
| Lecturer | `lecturer@uow.edu.au` | `lecturer123` |
| Admin | `admin@uow.edu.au` | `admin123` |

---

## 6. Known Limitations

These are not considered blockers for Sprint 5 demo, but they must be stated honestly in A3 evidence:

| Limitation | Current behaviour | Next-sprint direction |
|---|---|---|
| Upload indexing worker | Upload returns queued/indexing status, but uploaded files are not yet indexed into ChromaDB by a live worker | Wire the indexing job to chunk, embed, and add records to ChromaDB |
| Auth storage | Demo users are hard-coded/in-memory | Move users and refresh tokens to Postgres |
| Session persistence | Backend session history is in memory and lost on API restart | Persist sessions and messages to Postgres |
| ChromaDB init | RAG generator initialises lazily on first query | Keep lazy init for CI safety, but document it so `/api/health` can show `not_initialized` before first query |
| Long LLM calls | `qwen3:14b` can take around 90-120 seconds depending on hardware | Warm the model before recording; use GPU overlay where available |
| Full local pytest | Current runtime image does not include pytest | Use dev dependencies in CI or add a test image target |

---

## 7. Recommended Next Steps

### Must Do Before Commit / Push

1. Review the changed files with `git diff`.
2. Re-run the full pytest suite in an environment with dev dependencies installed.
3. Re-run `docker compose config --quiet` for base and GPU overlays.
4. Re-run one authenticated live query through Streamlit, not only direct API.
5. Commit the fix set with a message such as:

```text
fix: restore live Streamlit RAG demo path
```

### Must Do Before Demo Recording

1. Start the stack with GPU overlay if the host supports it.
2. Confirm Ollama has the intended model:

```bash
docker exec edurag-ollama-1 ollama list
```

3. Warm the model with one short CSIT321 query before recording.
4. Login as student in Streamlit and confirm the header shows:
   - Student role
   - Live API
   - `CSIT321` selected
5. Ask one grounded CSIT321 query and verify:
   - The answer is not fixture text.
   - Citation/source chips render.
   - The UI does not show an API error.
6. Ask one off-topic or ambiguous question and verify the graceful response path.
7. Record the demo using `docs/a3_demo_script.md`.

### Should Do Before Final A3 Submission

1. Update `docs/sprint5_implementation_summary.md` so the "what works" section reflects the 26 May fixes.
2. Update `docs/sprint5_status_table.md` remaining-work rows that are now stale after the post-fix QA pass.
3. Re-run the 5-query live benchmark on the final demo host and attach/commit the result JSON if it changed.
4. Decide whether to mention `qwen3:14b` or `llama3.2` in the demo narration based on the actual model used during recording.
5. Keep the limitations section explicit: upload indexing and persistent auth/session storage are still future work.

### Optional Hardening

1. Add a dedicated dev/test Docker image target with `requirements-dev.txt`.
2. Add Streamlit integration tests around login, course selection, and live query rendering.
3. Add a health endpoint field that separately reports `rag_initialized` and `rag_available`.
4. Add a user-facing spinner/message for long LLM calls so the UI feels intentional during 60+ second responses.
5. Persist backend sessions to Postgres once Sprint 5 evidence is frozen.

---

## 8. Handover Decision Log

| Decision | Rationale |
|---|---|
| Keep fixture fallback available, but stop silent fallback on live API errors | Fixtures are useful for offline demo safety, but they must not hide broken live wiring |
| Default Streamlit course to `CSIT321` | Sprint 5 seed corpus and demo script are CSIT321-scoped |
| Preserve Tung's raw QA file locally | It is evidence from another teammate, not junk; ignore pattern prevents accidental commit |
| Report `not_initialized` before first query | RAG generator is lazy-loaded; this is more honest than pretending the backend is fixture or chromadb before init |
| Use `PAEDIA_QUERY_TIMEOUT=180` | Live RAG with Ollama can exceed the old 10-second request timeout |

---

## 9. Related Files

| Purpose | File |
|---|---|
| Demo bug log | `docs/demo_bug_report_sprint5.md` |
| QA checklist and post-fix regression table | `docs/qa_checklist_sprint5.md` |
| Runtime setup notes | `docs/sprint5_runtime_notes.md` |
| Implementation summary | `docs/sprint5_implementation_summary.md` |
| Sprint status table | `docs/sprint5_status_table.md` |
| Demo script | `docs/a3_demo_script.md` |
| Evidence index | `docs/a3_evidence_index.md` |
| Canonical project wrap-up outside repo | `planning/reports/EduRAG_Project_Wrapup.md` |

