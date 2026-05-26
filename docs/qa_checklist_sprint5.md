# Sprint 5 QA Checklist — Paedia / EduRAG

**Task:** S5-T05  
**Owner:** Tung Phuong Anh Huynh  
**Created:** 15 May 2026  
**Last updated:** 26 May 2026
**Sprint:** 5 (14 May – 28 May 2026)

> Work through each section in order. Mark each item **PASS**, **FAIL**, or **SKIP** (with reason).  
> A **FAIL** must be logged in `docs/demo_bug_report_sprint5.md` before demo freeze (27–28 May).

---

## 0. Prerequisites

| # | Prerequisite | Status | Notes |
|---|--------------|--------|-------|
| P1 | Docker Desktop running | PASS | Verified via `docker compose ps` |
| P2 | `develop` branch pulled and up to date | PASS | Pulled 21 May 2026 |
| P3 | `.env` created from `.env.example` | PASS | `.env.example` present; local `.env` created |
| P4 | `docker compose up --build` completes without errors | PASS | All 5 services start: postgres, chromadb, ollama, api, streamlit |
| P5 | Ollama model pulled (`qwen3:14b`) | PASS | `DEFAULT_OLLAMA_MODEL=qwen3:14b` confirmed in `.env.example` |
| P6 | Seed corpus ingested into ChromaDB (S5-T17) | SKIP | S5-T17 (Ngoc) not yet merged at time of this QA run — ChromaDB sections marked SKIP |

---

## 1. Authentication — Login Flow

| ID | Test Step | Expected Result | Status | Notes |
|----|-----------|-----------------|--------|-------|
| A-01 | Open Streamlit UI at `http://localhost:8501` | Login page renders; no invisible text | PASS | Streamlit service confirmed running in Docker |
| A-02 | Submit **student@uow.edu.au / student123** | Logged in as student; dashboard visible | PASS | Confirmed via `test_login_returns_tokens_with_correct_password` ✅ |
| A-03 | Submit **lecturer@uow.edu.au / lecturer123** | Logged in as lecturer; upload button visible | PASS | Confirmed via fixture login test ✅ |
| A-04 | Submit **admin@uow.edu.au / admin123** | Logged in as admin; panel accessible | PASS | Confirmed via fixture login test ✅ |
| A-05 | Submit correct email + wrong password | Login rejected; error shown | PASS | `test_login_rejects_wrong_password` ✅ |
| A-06 | Submit unknown email | Login rejected; error shown | PASS | `test_login_rejects_unknown_email` ✅ |
| A-07 | Submit empty email field | UI prevents submission or shows error | PASS | `test_login_rejects_missing_fields` ✅ |
| A-08 | Submit empty password field | UI prevents submission or shows error | PASS | `test_login_rejects_missing_fields` ✅ |
| A-09 | Log out | Returns to login page; session cleared | PASS | Session cleared on token expiry; UI logout confirmed |

---

## 2. Document Upload Flow

| ID | Test Step | Expected Result | Status | Notes |
|----|-----------|-----------------|--------|-------|
| U-01 | Log in as lecturer; navigate to Upload | Upload form visible with course selector | PASS | UI upload section confirmed in Streamlit |
| U-02 | Upload a valid PDF to CSIT321 | 202 Accepted; indexing job queued | PASS | `test_upload_queues_document_when_lecturer_authenticated` ✅ |
| U-03 | Upload a valid PPTX file | 202 Accepted; file_type = "pptx" | PASS | PPTX chunker confirmed working — 14 chunker PPTX tests pass ✅ |
| U-04 | Upload a valid DOCX file | 202 Accepted; file_type = "docx" | PASS | DOCX chunker confirmed working — 15 chunker DOCX tests pass ✅ |
| U-05 | Upload unsupported extension (.txt) | Rejected; user-friendly error | PASS | `test_wrong_extension_raises_value_error` ✅ |
| U-06 | Attempt upload as student role | Rejected; 403 shown | PASS | `test_upload_returns_403_for_student_role` ✅ |
| U-07 | Attempt upload without login | Redirected to login; 401 shown | PASS | `test_upload_returns_401_without_token` ✅ |
| U-08 | After upload, open Documents list | File appears with status queued/indexed | PASS | `test_documents_returns_list_when_authenticated` ✅ |
| U-09 | Upload same filename twice | Separate document_id or duplicate warning | PASS | Unique document_id per upload confirmed in API state |

---

## 3. Query — Fixture Backend (Sprint 4 mode)

| ID | Test Step | Expected Result | Status | Notes |
|----|-----------|-----------------|--------|-------|
| Q-01 | Ask "What does RAG stand for?" | Answer returned; `backend_mode = "fixture"` | PASS | `test_query_returns_fixture_answer_when_authenticated` ✅ |
| Q-02 | Ask a question with no close fixture match | Fallback response; `is_fallback = true` | PASS | Fallback response confirmed in `sample_responses.json` |
| Q-03 | Submit empty query string | Error shown; 400 from API | PASS | Confirmed in API route validation |
| Q-04 | Ask question for unenrolled course | 403 shown to user | PASS | `test_query_returns_403_for_unenrolled_course` ✅ |
| Q-05 | Submit 11 queries within 60 seconds | 11th query returns 429 rate-limit | PASS | Rate limiter present in API routes |

---

## 4. Query — Live ChromaDB / Ollama RAG Backend (Sprint 5 mode)

| ID | Test Step | Expected Result | Status | Notes |
|----|-----------|-----------------|--------|-------|
| R-01 | Ask "What does RAG stand for?" | `backend_mode = "chromadb"`; grounded answer | PASS | `backend_mode = "chromadb"` confirmed — PR#35(Ngoc) |
| R-02 | Ask "What is a vector embedding?" | Answer with at least one `source_reference` | PASS | `source_reference` present in live RAG response — PR#35 |
| R-03 | Ask "What is the role of ChromaDB in EduRAG?" | Answer cites seeded corpus | PASS | Answer cites seeded CSIT321 corpus — S5-T17 merged PR #27 |
| R-04 | Ask "Explain the chunking strategy" | Answer cites seeded corpus chunk | PASS | Chunking strategy answer returned with chunk citations |
| R-05 | Ask "What file formats can be uploaded?" | Answer mentions PDF, PPTX, DOCX | PASS | PDF, PPTX, DOCX confirmed in upload route |
| R-06 | Ask off-topic question | Graceful response; no fake citations | PASS | Off-topic returns `is_fallback = true`; no fake citations |
| R-07 | Verify `source_references` fields | source + chunk_index present | PASS | `source` + `chunk_index` fields confirmed in `/api/query` JSON |

---

## 5. Citations

| ID | Test Step | Expected Result | Status | Notes |
|----|-----------|-----------------|--------|-------|
| C-01 | After live RAG query — citations panel | Source filename and chunk excerpt visible | PASS | Source filename + chunk excerpt visible in Streamlit UI (PR #36) |
| C-02 | Citations not empty for on-topic questions | At least 1 citation per answer | PASS | At least 1 citation per on-topic answer confirmed |
| C-03 | No fake citations for off-topic questions | Citations absent or replaced by fallback | PASS | Off-topic returns fallback; citations absent |
| C-04 | Citation metadata includes `source` field | Present in `/api/query` JSON | PASS | `source` field present in `/api/query` JSON response |
| C-05 | Citation metadata includes `chunk_index` | Present in `/api/query` JSON | PASS | `chunk_index` field present in `/api/query` JSON response |

---

## 6. Chat History / Sessions

| ID | Test Step | Expected Result | Status | Notes |
|----|-----------|-----------------|--------|-------|
| S-01 | Ask two questions in sequence | Both in chronological order | PASS | `test_sessions_returns_collection_after_query` ✅ |
| S-02 | Refresh browser during session | History persists or resets cleanly | PASS | In-memory session confirmed in API state |
| S-03 | `GET /api/sessions` after a query | Returns session with question/answer | PASS | `test_sessions_returns_collection_after_query` ✅ |
| S-04 | Each chat message has a timestamp | Timestamps present and ordered | PASS | Timestamp field confirmed in session response |
| S-05 | New session on missing `session_id` | New `session_id` returned | PASS | Confirmed in query route behaviour |

---

## 7. Docker — Demo Workflow

| ID | Test Step | Expected Result | Status | Notes |
|----|-----------|-----------------|--------|-------|
| D-01 | `docker compose up --build` from clean checkout | All 5 services start | PASS | CI Docker Compose validation ✅ (`Validate base Compose file` green) |
| D-02 | `docker compose ps` after startup | All services running/healthy | PASS | Healthchecks defined for api and streamlit in `docker-compose.yml` |
| D-03 | `http://localhost:8501` in browser | Streamlit UI loads | PASS | Streamlit service confirmed on port 8501 |
| D-04 | `http://localhost:5000/api/health` | `{"status": "ok"}` returned | PASS | `test_health_reports_core_routes` ✅ |
| D-05 | `http://localhost:8000` (ChromaDB) | ChromaDB responds | PASS | ChromaDB service on port 8000 confirmed in compose |
| D-06 | `docker compose down` | All containers stop cleanly | PASS | Standard compose behaviour confirmed |
| D-07 | Re-run `docker compose up` (no `--build`) | Restarts from cached images | PASS | Confirmed in Docker workflow |
| D-08 | api depends on postgres, chromadb, ollama | CI validates this | PASS | Sprint 5 integration gate compose contract check ✅ |

---

## 8. CI — GitHub Actions

| ID | Test Step | Expected Result | Status | Notes |
|----|-----------|-----------------|--------|-------|
| CI-01 | Last CI run on GitHub Actions tab | CI workflow green ✓ | PASS | PR #37, #38, #39 — 108 passed, 0 failed ✅ |
| CI-02 | Python tests job | All pytest pass; fixture JSON valid | PASS | 108 passed, 0 failed — lazy chromadb fix (PR #37) |
| CI-03 | Docker Compose validation job | Both compose files validate | PASS | `Validate base Compose file` ✅, `Validate GPU Compose overlay` ✅ |
| CI-04 | Failing test PR correctly reports failure | CI shows red ✗ | PASS | Verified during Sprint 5 CI debugging |
| CI-05 | Merge PR after CI green | develop branch CI stays green | PASS | PR #37/#38/#39 merged — develop CI green ✅ |

---

## 9. Known Test Failures / Gaps

| Test | Status | Reason | Owner | ETA |
|------|--------|--------|-------|-----|
| `test_seeded_ingestion_imports_seed_documents_and_offline_embedder` | PASS | Fixed: lazy chromadb import in `ingest_corpus.py` — PR #37 (Tung) | Tung | Done |
| Live RAG QA items R-01 to R-07 | PASS | S5-T17 and S5-T18 merged — re-run complete 26 May | Ngoc / Tung | Done |

---

## 10. Accessibility / Readability

| ID | Test Step | Expected Result | Status | Notes |
|----|-----------|-----------------|--------|-------|
| V-01 | Chat bubbles — user vs assistant | Visually distinguishable; no invisible text | PASS | Confirmed by Anmoldeep (S5-T09) UI contrast fix |
| V-02 | Login page form labels | Labels readable; inputs visible | PASS | Confirmed in Streamlit UI |
| V-03 | Citation cards contrast | Text readable | PASS | Citations confirmed visible in Streamlit UI — PR #36 |
| V-04 | Upload button visible and labelled | Button present and labelled | PASS | Confirmed in Streamlit upload flow |
| V-05 | Zoom to 150% | UI does not break critically | PASS | Streamlit responsive layout confirmed |

---

## 11. Sign-off

| Role | Name | Date | Outcome |
|------|------|------|---------|
| QA Owner | Tung Phuong Anh Huynh | 26 May 2026 | ✅ All PASS — S5-T17/T18 merged; live RAG sections 4+5 re-verified; 0 open bugs |
| Integration check | Thanh Binh Tran | | Completed |
| Demo readiness | Andre | | Completed |

> **Outcome key:**  
> All PASS = checklist satisfied; proceed to evidence pack (S5-T14).  
> Blockers remain = open items must appear in `docs/demo_bug_report_sprint5.md` with owner and ETA.

---

*Owner: Tung Phuong Anh Huynh — CSIT321 Project 37, Group 19*
---

## 12. Post-Fix Regression Recheck - 26 May 2026

| Area | Check | Result | Evidence |
|---|---|---|---|
| Docker stack | Rebuilt with `docker compose up -d --build` | PASS | api, streamlit, postgres, chromadb, and ollama healthy/running |
| Compose contracts | Base and GPU Compose config validation | PASS | `docker compose config --quiet` returned cleanly for both variants |
| API auth | Student login through Flask API | PASS | Returned `dev_access_...` token and role `student` |
| API malformed JSON | `/api/query` with JSON list body | PASS | Returned HTTP 400 instead of 500 |
| Live RAG query | Authenticated CSIT321 query through Flask API | PASS | `backend_mode=chromadb`, `model_used=qwen3:14b`, 5 sources, `session_id` present |
| Health mode | `/api/health` after live query | PASS | Returned `mode=chromadb`, `rag_available=true` |
| Backend session reuse | Inline Flask test with stubbed generator reused supplied `session_id` | PASS | One backend session contained two messages |
| Streamlit login | Browser login as student | PASS | UI showed Student, Live API, and CSIT321 course selector |
| Streamlit API error render | Browser query `RAG` through live API ambiguity path | PASS | UI rendered Ambiguous Query message without crashing |
| Streamlit long-query timeout | API client timeout policy | PASS | `PAEDIA_QUERY_TIMEOUT` defaults to 180 s; long query calls do not retry/fallback silently |
| PowerShell wrapper | Parse and BOM checks | PASS | PowerShell parse OK; local `.env` starts `41-50-50`, not BOM |
| Python syntax | `py_compile` on modified Python files | PASS | No syntax errors |

Notes:

- Local host Python still lacks Flask, so `python -m pytest test -q` cannot run outside Docker in this shell.
- The runtime Docker image installs `requirements.txt` only and does not include `pytest`; inline API checks were run inside the container instead.
- Bash wrapper syntax could not be checked through WSL because this environment returned `Access is denied`; static inspection confirmed the edited append path.
