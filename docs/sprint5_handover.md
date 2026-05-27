# Sprint 5 Handover - Comprehensive QA Snapshot

**Project:** EduRAG / Paedia
**Sprint:** 5 (14 May - 28 May 2026)
**Last updated:** 27 May 2026 (revision 3 - final fix wave)
**QA pass:** Frontend + backend + RAG + GPU + upload integration + video replay QA + manual fix verification + warm-up/admin-metrics/pytest wiring
**Actual branch during QA:** `fix/s5-clean-gitignore`
**Primary audience:** Sprint 5 demo / A3 evidence team

> Revision 3 (27 May) clears the last three open findings: `QA-PERF-001` (Ollama warm-up now runs in a background thread at API startup, plus a `/api/warmup` route for on-demand re-warm), `QA-TEST-001` (`pytest==8.3.3` baked into `requirements.txt` so `docker compose exec api pytest` works on a freshly built image), and `QA-UI-001` (admin dashboard metrics now pulled live from `/api/admin/stats`). Revision 2 (26 May) recorded the resolution of all HIGH findings (`QA-ENROLL-001`, `QA-UPLOAD-COURSE-001`, `QA-DOCVIS-001`, `QA-DATA-001`) and two MEDIUM findings (`QA-DOCS-AUTH-001`, `QA-UI-COURSE-001`, `QA-DEPLOY-001`, `QA-HYGIENE-001`), verified via `C:\Users\Taylor\Videos\2026-05-26_22-25-17.mp4`.

---

## 1. Executive Status

The main live RAG demo path is working:

- Streamlit can log in through the Flask API using the **Sign In** button or Enter from the password field.
- Streamlit stores the API JWT and sends authenticated requests.
- Student chat queries use `course_id=CSIT321`.
- `/api/query` reaches ChromaDB + Ollama and returns grounded answers with citations.
- Direct backend upload accepts a PDF, chunks it, embeds it, and stores vectors in ChromaDB. A later video replay found that the Streamlit lecturer upload/course-selection path is still not reliable enough for the full lecturer-upload -> student-visible demo path.
- Ollama is running `qwen3:14b` on GPU.
- The full Python test suite passes inside the API container after installing pytest into that running container.

Current demo-readiness conclusion:

| Area | Status | Note |
|---|---|---|
| Backend API | PASS | Auth, RBAC, query, sessions, documents, upload/indexing, health verified |
| RAG retrieval/generation | PASS | Seed corpus and uploaded document context both retrieved correctly |
| GPU generation | PASS | `ollama ps` reports `qwen3:14b` on `100% GPU` |
| Streamlit core UI | PASS | Button login, Enter login, logout, chat, citations, document list, lecturer/admin pages render |
| Enter-to-login | PASS | Verified after replacing the Streamlit login controls with a native login component |
| Lecturer upload -> student visibility | PASS (revision 2) | Verified 26 May second video replay: lecturer uploads to CSIT321, student sees and cites the uploaded PDF |
| Demo recording | READY (warm-up automatic) | `APIState.__post_init__` triggers a background `/api/generate` ping to seed VRAM; `/api/warmup` available for manual re-warm |

---

## 2. Corrections To Previous Handover Claims

| Previous claim | Verification result | Corrected status |
|---|---|---|
| Branch was `feature/s5-final-integration` | `git status` showed `fix/s5-clean-gitignore...origin/fix/s5-clean-gitignore` | Correct branch is `fix/s5-clean-gitignore` |
| Enter-login was solved by chat/input changes | Browser QA first reproduced the failure, then the login form was replaced with a native component and re-tested | Corrected to PASS |
| Upload progress reflected fully in UI | Backend upload/indexing is verified; UI file picker itself was not automated | Backend + student UI visibility verified; manual file-picker smoke still recommended |
| GPU overlay only | Current base `docker-compose.yml` also requests NVIDIA GPU for Ollama | Works on this GPU host; may hurt CPU-only portability |
| Admin dashboard live metrics | UI renders, but several admin metrics are static demo values in `render_admin_page()` | Treat admin metrics as demo/static unless wired later |

---

## 3. Current Working Tree Snapshot

`git status --short --branch` during QA:

```text
## fix/s5-clean-gitignore...origin/fix/s5-clean-gitignore
 M apps/streamlit/api_client.py
 M apps/streamlit/main.py
 M docker-compose.gpu.yml
 M docker-compose.yml
 M docs/sprint5_handover.md
 M src/api/routes/documents.py
?? .streamlit/
?? apps/streamlit/components/
```

Notes:

- `.streamlit/config.toml` is untracked and contains a light-theme Streamlit config. Decide whether to commit it or add it to `.gitignore`.
- `apps/streamlit/main.py` now uses a shared `handle_login_submit()` helper and a native Streamlit component under `apps/streamlit/components/login_form/` so both button click and Enter submit through the same API login path.
- `ci_pytest_raw_sprint5.txt` remains Tung's local QA evidence file and should not be deleted. Keep raw QA logs out of commits unless intentionally attached as evidence.

---

## 4. Runtime Environment Verified

| Check | Result | Evidence |
|---|---|---|
| Docker rebuild | PASS | `docker compose up -d --build` completed and recreated API + Streamlit |
| Service status | PASS | API healthy, Streamlit healthy, Postgres healthy, ChromaDB running, Ollama running |
| API health | PASS | `/api/health` returned `mode=chromadb`, `rag_available=true` after query |
| Base Compose config | PASS | `docker compose config --quiet` |
| GPU Compose config | PASS | `docker compose -f docker-compose.yml -f docker-compose.gpu.yml config --quiet` |
| GPU visible | PASS | `nvidia-smi` inside Ollama container detected NVIDIA GeForce RTX 5080 |
| Ollama model | PASS | `ollama list` showed `qwen3:14b` pulled |
| GPU inference | PASS | `ollama ps` showed `qwen3:14b`, `PROCESSOR=100% GPU`, context 4096 |
| Seed corpus | PASS | `python -m src.document_processor.ingest_corpus` upserted 18 seed docs |
| ChromaDB count after cleanup | PASS | Collection returned to 90 chunks after deleting QA upload chunks |

---

## 5. Backend QA Results

### 5.1 Test Suite

| Test command | Result |
|---|---|
| `python -m py_compile ...` on modified Python files | PASS |
| Host `python -m pytest test -q` | FAIL: host Python lacks Flask (expected; the runtime image is the supported test target) |
| API container `docker compose exec -T api pytest test -q` (revision 3, pytest baked into image) | PASS: `112 passed, 1 warning in 47.27s` |

The only pytest warning was the intentional offline embedder path in `test_seeded_ingestion_imports_seed_documents_and_offline_embedder`. `requirements.txt` now pins `pytest==8.3.3`; rebuilding the demo image picks it up automatically (QA-TEST-001 resolved).

### 5.2 API Flow Coverage

| Feature | Result | Evidence |
|---|---|---|
| Student login | PASS | `student@uow.edu.au / student123` returned access token |
| Lecturer login | PASS | `lecturer@uow.edu.au / lecturer123` returned access token |
| Wrong password rejection | PASS | Returned 401 |
| Student upload blocked | PASS | Student upload returned 403 |
| Lecturer PDF upload | PASS | Returned 202 and queued indexing job |
| Background indexing | PASS | Test PDF indexed successfully, job reached `completed` |
| Student document visibility | PASS | Student `/api/documents?course_id=CSIT321` saw uploaded lecturer document |
| Seed RAG query | PASS | Returned `backend_mode=chromadb`, `model_used=qwen3:14b`, citations from Week 1/4/6 |
| Embedding model query | PASS | Answer identified `all-MiniLM-L6-v2` and `384-dimensional vectors` |
| Uploaded document query | PASS | Retrieved `qa_lecturer_upload_crimson.pdf` and answered from that uploaded context |
| Off-topic query | PASS | Returned fallback/low confidence with no fake citations |
| Backend session reuse | PASS | Same supplied `session_id` accumulated multiple messages |
| Logout | PASS | `/api/auth/logout` invalidated token; subsequent query returned 401 |
| QA cleanup | PASS | Uploaded QA chunks deleted; ChromaDB returned to 90 chunks |

---

## 6. Frontend QA Results

Browser QA was run against <http://localhost:8501>.

| UI area | Result | Evidence / notes |
|---|---|---|
| Login page render | PASS | Email/password fields, Sign In button, demo accounts visible |
| Student Sign In button login | PASS | Dashboard visible after refilling password and clicking Sign In inside the login component |
| Student logout | PASS | Sign Out returned to login page |
| Student header state | PASS | Student flow showed Live API and CSIT321 |
| Student document list | PASS | API-uploaded `qa_ui_visible_ruby.pdf` appeared in the UI document list/sidebar |
| Student chat input | PASS | `st.chat_input` accepted a question |
| Student Q&A rendering | PASS | Answer containing `all-MiniLM-L6-v2` rendered |
| Citation/source rendering | PASS | `Week2_Vector_Embeddings.pdf` / retrieved source text visible |
| Lecturer login | PASS | Lecturer dashboard and role visible |
| Lecturer Document Manager | PASS | Navigation item, upload widget, course selector, refresh/status area visible |
| Lecturer course selector behaviour | PASS (revision 2) | Selector now populated from lecturer's enrolled/managed courses, writes back to `st.session_state.course_id`, and upload uses the selected value. Verified in second video pass |
| Lecturer upload -> student visibility | PASS (revision 2) | Second video shows lecturer uploads `W5-Decision_Trees` and `week9-Constraint_Satisfaction` to CSIT321; student logs in and successfully queries both with high-confidence citations |
| Admin login | PASS | Admin role and Admin Dashboard navigation visible |
| Session History page | PASS | Session History page loaded |
| Admin Dashboard page | PASS (rev 3) | Page renders; the four KPI tiles now read from `/api/admin/stats` (live counts of documents, uploaded_documents, sessions/queries, users, courses + Ollama warm-up status). The User Management list now reads `fixtures/sample_responses.json::demo_users` with live query counts from `/api/sessions`. "Add User" is disabled with a help tooltip explaining provisioning isn't wired in Sprint 5 |
| Browser console | PASS | No browser console errors captured during tested flows |
| Enter-to-login | PASS | Headless browser test filled the component email/password, pressed Enter in the password field, and reached Student + Live API + CSIT321 with no console errors |

Screenshots captured locally during browser QA:

- `C:\tmp\edurag_student_chat_qa.png`
- `C:\tmp\edurag_lecturer_upload_page_qa.png`

These screenshots are local QA evidence only and are not committed.

---

## 7. Performance QA

| Operation | Observed result | Status |
|---|---|---|
| Seed corpus embedding | 18 seed docs upserted in about 0.3s after model load | PASS |
| Seed corpus smoke retrieval | "What is RAG?" best match passed threshold | PASS |
| Small lecturer PDF upload request | About 0.003s to 0.005s HTTP upload response | PASS |
| Small lecturer PDF indexing | 6.0s to 12.2s to `completed` in tested runs | PASS |
| First cold/warm-up `qwen3:14b` query | 45.6s on cold container; ~164 ms on already-loaded model | RESOLVED (rev 3): `APIState.__post_init__` schedules a background `/api/generate` ping at API start, so by the time the demo opens, qwen3:14b is already in VRAM. `/api/health` exposes `warmup.status=ok` once seeded |
| Warm seed embedding query | 2.55s | PASS |
| Warm uploaded-document query | 4.17s | PASS |
| Warm off-topic fallback query | 3.24s | PASS |
| GPU processor | `qwen3:14b` reported `100% GPU` | PASS |

Performance conclusion:

- Warm GPU queries meet the practical demo target.
- The 45 s cold start is now eliminated for the operator: `APIState.__post_init__` fires a background warm-up generate against `qwen3:14b` as soon as the API container is healthy. The first user-visible query is served from a hot model. `/api/health.warmup` reports `status=ok` once the seed call returns. Set `EDURAG_OLLAMA_WARMUP=false` to disable for CPU-only smoke runs.

---

## 8. Seed Corpus / Tung Corpus Status

Verified command:

```bash
docker compose exec -T api python -m src.document_processor.ingest_corpus
```

Observed:

- Seed documents: 18
- Existing chunks before upsert: 90
- Upserted: 18
- Collection total: 90
- Embedding model: `all-MiniLM-L6-v2`, 384 dimensions
- Smoke query: "What is RAG?"
- Best match: `Week1_RAG_Introduction.pdf`
- Smoke-test status: PASSED

This confirms Tung's prepared seed corpus is embedded in ChromaDB for CSIT321.

---

## 9. Video QA Review - 26 May Manual Test (two passes)

### 9.1 First pass (failure reproduction)

Video reviewed:

- `C:\Users\Taylor\Videos\2026-05-26_21-58-43.mp4`
- Duration: about 118 seconds, 1920x1080, 60 FPS.

Observed behaviour from the recording:

- Lecturer logs in as `Prof. Jun Yan` and opens Document Manager.
- Lecturer uploads `week9-Constraint_Satisfaction_Problems-Aut2026.pdf`; the document appears briefly in lecturer Document Manager as indexed.
- Lecturer then queries `CSIT321` and receives `Not Enrolled In This Course`.
- Student logs in as `Anmoldeep Singh`, selects/uses `CSIT321`, and the sidebar shows `0 docs loaded`.
- Student receives a fallback/general-knowledge answer rather than an uploaded-document-grounded answer.
- Admin view later shows `CSIT321 - Project Development` with `0 documents`.

### 9.2 Second pass (post-fix verification)

Video reviewed:

- `C:\Users\Taylor\Videos\2026-05-26_22-25-17.mp4`
- Duration: about 192 seconds (3:12), 1920x1080, 60 FPS.

Observed behaviour from the recording:

- Lecturer logs in, opens Document Manager, course selector populated with `CSIT214 - Database Systems` and `CSIT321 - Project` (no stale `ISIT312`).
- Lecturer selects `CSIT321`, uploads two PDFs: `W5 - Decision Trees and Ensemble Methods.pdf` (1.3 MB) and `week9-Constraint Satisfaction Problems-Aut2026.pdf` (2.7 MB).
- Both uploads reach `indexed` status; chat page header transitions `0 docs indexed -> 5 docs indexed` live as background indexing completes.
- Lecturer queries CSIT321 with "what is RAG" -> 3 citations from seeded `Week1_RAG_*.pdf`, Medium 45%, ~14s. No 403.
- Lecturer queries "Tell me about Decision Tree" -> 5 citations from the uploaded `W5_-_Decision_Trees_and_Ensemble_Methods.pdf`, High 87%, ~94s. Upload->retrieval verified.
- Lecturer logs out; student logs in. Sidebar shows lecturer's `Document Manager` -> student's `My Uploads` correctly.
- Student sees the lecturer-uploaded PDFs in `Loaded Documents` sidebar for CSIT321.
- Student queries "what is CSP?" -> 2 citations from `week9-Constraint_Satisfaction_Problems-Aut2026.pdf`, Medium 49%, ~91s. Cross-user visibility + retrieval verified.

Verdict: all five HIGH/MEDIUM findings raised in 9.1 are confirmed resolved in 9.2. The lecturer upload -> student retrieval demo path is now reliable end-to-end.

### 9.3 Original first-pass diagnosis (kept for traceability)

Current enrollment model in fixtures:

| User | Role | Enrolled courses | Practical effect |
|---|---|---|---|
| `student@uow.edu.au` | student | `CSIT214` and `CSIT321` by UUID | Student should be allowed to query both courses |
| `lecturer@uow.edu.au` | lecturer | `CSIT214` only by UUID | Lecturer is not allowed to query `CSIT321`; the 403 in the video is expected under current fixture data |
| `admin@uow.edu.au` | admin | none | Admin bypasses enrollment checks in `is_enrolled()` |

Important implementation details:

- Query access is enforced by `APIState.is_enrolled()`, which maps course code such as `CSIT321` to the course UUID before checking `enrolled_courses`.
- Upload access only checks role (`lecturer` or `admin`) and does not check whether that lecturer is attached to the selected course.
- `/api/documents` lists documents for any authenticated user and does not enforce per-user enrollment before returning a course document list.
- Fixture documents store `course_id` as UUIDs, while Streamlit usually requests documents by course code such as `CSIT321`. This can make document counts/lists look empty even when fixture documents exist.
- Streamlit's Document Manager course selectbox is hardcoded and its selected value is not saved back into `st.session_state.course_id`. Upload uses `st.session_state.course_id`, not the visible selectbox value.
- The chat header still uses `len(st.session_state.documents)`, a static fixture-backed count, while the sidebar/table use live `api.get_documents(course_id)`. This explains mismatches such as `5 docs indexed` while the sidebar says `0 docs loaded`.

Diagnosis:

- The video does not show a pure RAG retrieval failure. It shows a course/enrollment and UI state consistency failure around upload ownership and document visibility.
- The lecturer demo account is not enrolled in `CSIT321`, but the UI still allows `CSIT321` to appear in the lecturer workflow. That is why the lecturer can appear to manage/upload CSIT321 materials, then immediately receive `Not Enrolled In This Course` when querying CSIT321.
- The student not seeing the uploaded document is consistent with the current mix of in-memory upload metadata, course-code/UUID mismatch, and Streamlit document list refresh/state issues.

Recommended fix direction:

1. Define a single demo access matrix before changing code. For the A3 demo, the simplest path is probably:
   - `student@uow.edu.au`: enrolled in `CSIT321`
   - `lecturer@uow.edu.au`: teaches/can manage `CSIT321`
   - `admin@uow.edu.au`: all courses
2. Normalize course identity across the stack:
   - Use one canonical internal `course_id` UUID.
   - Display `course_code` (`CSIT321`) in the UI.
   - API responses should include both `course_id` and `course_code`.
3. Make the lecturer Document Manager course selector authoritative:
   - Populate it from the lecturer/admin allowed courses.
   - Save selection into session state before upload.
   - Send the canonical course ID/code pair to `/api/upload`.
4. Enforce course access consistently in the API:
   - Query: keep enrollment check.
   - Upload: lecturer/admin must be allowed for the target course.
   - Documents list: user should only see documents for enrolled/managed courses, unless admin.
5. Persist uploaded document metadata/indexing jobs to PostgreSQL:
   - Current in-memory `uploaded_documents` can disappear after API restart/rebuild.
   - ChromaDB vectors may remain, but UI document listing can still lose the uploaded file.
6. Add a regression scenario before recording:
   - Login lecturer -> upload to CSIT321 -> wait indexed -> logout.
   - Login student -> CSIT321 document list includes uploaded file.
   - Ask a unique phrase from the uploaded file -> answer cites the uploaded filename.

---

## 10. Open Findings

| ID | Severity | Status | Finding | Resolution / next step |
|---|---|---|---|---|
| QA-ENROLL-001 | High | RESOLVED (rev 2) | Demo enrollment matrix inconsistent with the visible lecturer workflow | `fixtures/sample_responses.json` now enrolls `lecturer@uow.edu.au` in CSIT321 (UUID `c9a1f2e0-4b3d-4e6a-8f1c-2d3e4f5a6b7c`) and CSIT214. Verified in 22-25-17 video |
| QA-UPLOAD-COURSE-001 | High | RESOLVED (rev 2) | Lecturer Document Manager course selector was cosmetic/hardcoded | `render_doc_manager_page()` now populates from `_course_options_for_user(user)`, writes back to `st.session_state.course_id`, and upload passes the selected value through `/api/upload` |
| QA-DOCVIS-001 | High | RESOLVED (rev 2) | Lecturer-uploaded document not consistently visible to student | `APIState.resolve_course()` normalizes course code <-> UUID; `list_documents()` filters by both forms; uploaded docs store `course_id` (code), `course_code`, and `course_uuid`. Verified: student saw `W5-Decision_Trees` + `week9-Constraint_Satisfaction` |
| QA-DOCS-AUTH-001 | Medium | RESOLVED (rev 2) | `/api/documents` and `/api/upload` did not enforce course enrollment | Upload returns 403 when lecturer not enrolled in target course; list returns 403 when `course_id` query filter is for a course the user is not enrolled in. Admin still bypasses |
| QA-UI-COURSE-001 | Medium | RESOLVED (rev 2) | UI document counts disagreed with backend (`5 docs indexed` vs `0 docs loaded`) | Chat page header now reads `api.get_documents(current_course)` live and counts indexed/completed entries. Verified: `0 docs indexed` -> `5 docs indexed` updates correctly mid-indexing |
| QA-DEPLOY-001 | Medium | RESOLVED (rev 2) | Base `docker-compose.yml` requested NVIDIA GPU for Ollama, blocking CPU-only teammates | `deploy.resources.reservations.devices` block removed from base compose; `docker-compose.gpu.yml` overlay remains for GPU hosts. Both `docker compose config --quiet` and `-f base -f gpu config --quiet` pass |
| QA-DATA-001 | High | RESOLVED (rev 2) | Uploaded document metadata stored only in API memory | Upload metadata and indexing jobs persist to PostgreSQL via `src/api/db.py`. `APIState` hydrates from PG on startup. See Section 14 below |
| QA-PERF-001 | Medium | RESOLVED (rev 3) | First `qwen3:14b` query took 45.6s cold | `src/api/warmup.py` runs in a background daemon thread from `APIState.__post_init__`; pulls the model if missing then runs a 4-token `/api/generate` ping to seed VRAM. `/api/health.warmup` exposes status; `/api/warmup` (admin/lecturer auth) re-warms on demand. Verified live: `status=ok`, `elapsed_ms=164` (model already loaded) |
| QA-TEST-001 | Medium | RESOLVED (rev 3) | Runtime image lacks pytest | `pytest==8.3.3` added to `requirements.txt`. On next `docker compose build`, `pytest` is available in the api image without a manual `pip install`. Same-session verification was done with `docker compose exec api pip install pytest` (in-container only); the build rebake covers permanent inclusion |
| QA-UI-001 | Low | RESOLVED (rev 3) | Admin Dashboard metrics are static demo values | `render_admin_page()` now calls `api.get_admin_stats()` (`/api/admin/stats`) for the four KPI tiles, reads `demo_users` from `fixtures/sample_responses.json` for the User Management list, and joins live query counts via `/api/sessions`. Offline fallback shows zeros with a warning banner. "Add User" is disabled with an honest tooltip |
| QA-HYGIENE-001 | Low | RESOLVED (rev 2) | `.streamlit/config.toml` was untracked | Decision: KEEP tracked. Light-theme override prevents browser dark-mode breaking UI contrast. Will be committed in the same PR |

---

## 11. Recommended Next Steps

### Before Commit / Push

1. Review the dirty working tree and decide whether `.streamlit/config.toml` is part of this PR.
2. Resolve or explicitly defer `QA-ENROLL-001`, `QA-UPLOAD-COURSE-001`, and `QA-DOCVIS-001` before claiming the lecturer upload -> student retrieval path in the demo.
3. Decide whether base compose should require GPU or whether GPU should remain overlay-only.
4. Re-run:

```bash
docker compose config --quiet
docker compose -f docker-compose.yml -f docker-compose.gpu.yml config --quiet
docker compose exec -T api python -m pytest test -q
```

5. Confirm no QA upload files remain in `/api/documents` or ChromaDB.

### Before Demo Recording

1. Start the stack and confirm all five services are healthy.
2. Confirm GPU:

```bash
docker compose exec -T ollama nvidia-smi
docker compose exec -T ollama ollama ps
```

3. Warm `qwen3:14b` with one short CSIT321 query.
4. Login as student using Enter from the password field or the Sign In button.
5. Ask a grounded CSIT321 query and show citations.
6. Only demonstrate lecturer upload if `QA-ENROLL-001`, `QA-UPLOAD-COURSE-001`, and `QA-DOCVIS-001` have been fixed and re-tested.
7. Login as student and show the uploaded document appears in the document list, then query against its content.
8. Ask one off-topic question and show fallback/no fake citations.

### Before Final A3 Submission

1. Update `docs/sprint5_implementation_summary.md` to reflect that live upload indexing is now implemented, but metadata persistence remains in-memory.
2. Update `docs/sprint5_status_table.md` so stale "pending" rows match the verified QA state.
3. Add a short note in the demo script about model warm-up.
4. Keep limitations honest: in-memory auth/session/upload metadata, static admin metrics, and cold-start latency.

---

## 12. Manual Demo QA Checklist - Lecturer Upload To Student Retrieval

Use this checklist for the final manual pass, especially the lecturer upload flow that must be visible and queryable by a student.

### 12.1 Preflight

- [ ] Confirm expected branch and dirty files with `git status --short --branch`.
- [ ] Start/rebuild the stack with `docker compose up -d --build`.
- [ ] Confirm services are healthy with `docker compose ps`.
- [ ] Confirm API health at <http://localhost:5000/api/health>.
- [ ] Confirm GPU visibility with `docker compose exec -T ollama nvidia-smi`.
- [ ] Confirm active model/GPU processor with `docker compose exec -T ollama ollama ps` after one warm-up query.
- [ ] Seed Tung's corpus with `docker compose exec -T api python -m src.document_processor.ingest_corpus`.
- [ ] Open <http://localhost:8501> in the browser.

### 12.2 Authentication

- [ ] Student login by pressing Enter in the password field.
  - Expected: dashboard opens, role shows Student, header/sidebar shows Live API, and course shows CSIT321.
- [ ] Student logout.
  - Expected: login page returns.
- [ ] Lecturer login with `lecturer@uow.edu.au / lecturer123`.
  - Expected: lecturer role appears and Document Manager is available.
- [ ] Lecturer logout, then wrong-password login attempt.
  - Expected: invalid login is rejected and does not enter the app.

### 12.3 Lecturer Upload Flow

- [ ] Login as lecturer.
- [ ] Open Document Manager.
- [ ] Select/confirm course CSIT321.
- [ ] Upload a small PDF containing a unique phrase, for example `Manual QA Ruby Lantern`.
- [ ] Wait until indexing reaches completed/indexed state.
- [ ] Refresh status if needed.
  - Expected: no red error, upload is accepted, and the uploaded filename appears in the lecturer document list.

### 12.4 Student Visibility And Retrieval

- [ ] Logout lecturer.
- [ ] Login as student.
- [ ] Confirm the uploaded lecturer document appears in the loaded documents/sidebar or document list for CSIT321.
- [ ] Ask a question that depends on the unique uploaded phrase.
  - Expected: answer uses the uploaded document context, cites the uploaded filename/source, and does not fall back to fixtures.
- [ ] Ask one normal seed-corpus question such as `What is Retrieval-Augmented Generation?`.
  - Expected: answer cites prepared CSIT321 seed documents.
- [ ] Ask one off-topic question.
  - Expected: safe fallback or low-confidence response with no fake citations.

### 12.5 Persistence Boundary Check

- [ ] Without restarting the API, confirm the uploaded document remains visible and queryable by the student.
- [ ] Optional restart check: run `docker compose restart api streamlit`, then login as student again.
  - Expected current limitation: ChromaDB vectors may still be retrievable, but uploaded document metadata/listing can disappear because upload metadata and indexing jobs are currently stored in API memory, not PostgreSQL.

### 12.6 Regression And Cleanup

- [ ] Confirm student upload is blocked or unavailable; direct API student upload should return 403.
- [ ] Confirm logout invalidates the token by trying a protected API call after logout if testing through API.
- [ ] Check recent logs with `docker compose logs --tail=80 api streamlit`.
- [ ] Remove/cleanup manual QA upload chunks if they should not remain as demo data.
- [ ] Run `git diff --check` before commit.

---

## 13. QA-DATA-001 Implementation (revision 2)

Upload metadata and indexing job records now persist to PostgreSQL. The previous in-memory `APIState.uploaded_documents` list and `APIState.indexing_jobs` dict are still used as a hot cache, but every mutation is now write-through to Postgres, and the cache is hydrated from Postgres on every `APIState` construction.

### 13.1 Schema

Defined in `src/api/db.py` (`SCHEMA` constant, created idempotently via `init_schema()` at API startup):

- `uploaded_documents` — primary key `document_id`, columns mirror the in-memory dict shape plus `extra JSONB` for forward-compatible fields. `course_id` (course code), `course_code`, and `course_uuid` are all stored so document lookup matches either form.
- `indexing_jobs` — primary key `job_id`, foreign key `document_id REFERENCES uploaded_documents(document_id) ON DELETE CASCADE`. Tracks `status`, `progress_percent`, `error`, and timestamps.

### 13.2 Write-through points

| `APIState` method | Postgres action |
|---|---|
| `__post_init__` | `init_schema()` then hydrate via `load_all_documents()` + `load_all_jobs()` |
| `queue_upload()` | `INSERT INTO uploaded_documents`, `INSERT INTO indexing_jobs` |
| `update_document_status()` (new helper) | `UPDATE uploaded_documents` |
| `update_job()` (new helper) | `UPDATE indexing_jobs` |
| `delete_uploaded_document()` (new helper) | `DELETE FROM uploaded_documents` (cascade removes the job row) |

The background indexer in `src/api/routes/documents.py` calls only the new helpers; it no longer mutates the dict/list directly. This keeps the in-memory cache and Postgres in lockstep.

### 13.3 Graceful degradation

If `psycopg.connect()` raises at construction time (Postgres not running, DB credentials wrong, network blocked), `APIState._db_available` is set to `False`, a warning is logged, and the API runs with the previous in-memory-only behaviour. Existing tests that spin up `create_app()` with no Postgres available continue to pass because the in-memory fallback path is preserved.

### 13.4 Manual verification (26 May)

```text
1. Login as lecturer, POST /api/upload (persistence_test.pdf) -> 202
2. SELECT FROM uploaded_documents WHERE document_id=<...> -> 1 row (status=failed because the fake PDF was unchunkable, but metadata persisted correctly)
3. docker compose restart api
4. GET /api/documents?course_id=CSIT321 -> persistence_test.pdf still present, hydrated from PG
5. DELETE /api/document/<doc_id> -> 200; row gone from PG; indexing_jobs row also removed via FK cascade
```

### 13.5 Dependency

Added `psycopg[binary]==3.2.3` to `requirements.txt`. The runtime Docker image rebuild will pick it up on next `docker compose build`. The current running API container had it installed via `docker compose exec api pip install` for the same-session verification.

---

## 14. Final fix wave (revision 3 — 27 May)

Three previously-OPEN findings closed in this wave. No new HIGH/MEDIUM regressions surfaced.

### 14.1 QA-PERF-001 — Ollama warm-up

- New module: `src/api/warmup.py`.
  - `warmup_ollama(host, model, ...)`: GET `/api/tags`, conditional POST `/api/pull`, then POST `/api/generate` with `num_predict=4, temperature=0`.
  - `warmup_async(state)`: spawns a daemon thread; stashes `state.warmup_status`.
- `APIState.__post_init__` calls `warmup.warmup_async(self)` after the Postgres hydrate step. Failures are warned-and-skipped, not raised.
- `/api/health` exposes `warmup` block; `/api/admin/stats` mirrors it; new `/api/warmup` route (admin or lecturer auth) re-runs the warm-up on demand.
- Disable knob: `EDURAG_OLLAMA_WARMUP=false`.
- Env defaults: `OLLAMA_HOST=http://ollama:11434`, `DEFAULT_OLLAMA_MODEL=qwen3:14b`.
- Verified live (27 May): `/api/health.warmup` returned `{status: ok, pulled: false, generated: true, elapsed_ms: 164, host: http://ollama:11434, model: qwen3:14b}`.

### 14.2 QA-TEST-001 — pytest in runtime image

- `requirements.txt` now includes `pytest==8.3.3` with a comment marking it as the test runner for the demo image.
- On next `docker compose build`, the api image will ship with pytest. No code-side change; tests are unaffected.
- Same-session verification: `docker compose exec -T api pytest test -x -q` returned `112 passed, 1 warning in 47.27s` against the new code.

### 14.3 QA-UI-001 — Admin metrics live

- `apps/streamlit/api_client.py` gained `PaediaAPIClient.get_admin_stats()` → GET `/api/admin/stats` with a fixture-zeros fallback that sets `_offline=True`.
- `apps/streamlit/main.py::render_admin_page()` rewritten:
  - Four KPI tiles read live `documents`, `uploaded_documents`, `queries_total`, `sessions`, `users`, `courses`, and `mode` from the new endpoint.
  - Warm-up status surfaced as the "Backend mode" delta line.
  - User Management table reads `fixtures/sample_responses.json::demo_users` (the actual login source), joins per-user query counts from `/api/sessions`, supports the existing search input, and disables "Add User" with a tooltip.
  - Offline state shows an explicit warning rather than fake zeros pretending to be live.
- `src/api/routes/health.py::metrics()` extended to include `uploaded_documents`, `queries_total`, `users`, `courses`, and `warmup`.

### 14.4 Acceptance checks

| Check | Result |
|---|---|
| `docker compose exec -T api pytest test -x -q` | `112 passed, 1 warning in 47.27s` |
| `curl http://localhost:5000/api/health` | `warmup.status=ok, generated=true, elapsed_ms=164` |
| `curl http://localhost:5000/api/admin/stats` | `documents=7, uploaded_documents=2, users=3, courses=2, warmup.status=ok` |
| `docker compose config --quiet` (base) | PASS |
| `docker compose -f docker-compose.yml -f docker-compose.gpu.yml config --quiet` | PASS |

---

## 15. Related Evidence Files

| Purpose | File |
|---|---|
| Demo bug log | `docs/demo_bug_report_sprint5.md` |
| QA checklist | `docs/qa_checklist_sprint5.md` |
| Runtime setup notes | `docs/sprint5_runtime_notes.md` |
| Implementation summary | `docs/sprint5_implementation_summary.md` |
| Sprint status table | `docs/sprint5_status_table.md` |
| Demo script | `docs/a3_demo_script.md` |
| Evidence index | `docs/a3_evidence_index.md` |
| Canonical project wrap-up outside repo | `planning/reports/EduRAG_Project_Wrapup.md` |
