# Sprint 5 QA Checklist — Paedia / EduRAG

**Task:** S5-T05  
**Owner:** Tung Phuong Anh Huynh  
**Created:** 15 May 2026  
**Last updated:** 15 May 2026  
**Sprint:** 5 (14 May – 28 May 2026)  

> **How to use this checklist**  
> Work through each section in order. Mark each item **PASS**, **FAIL**, or **SKIP** (with a reason).  
> A **FAIL** must be logged in `docs/demo_bug_report_sprint5.md` before the demo freeze (27–28 May).  
> The checklist must be fully signed off before the A3 evidence pack is assembled (S5-T14).

---

## 0. Prerequisites

Before starting, confirm the following are available on your machine:

| # | Prerequisite | Status |
|---|--------------|--------|
| P1 | Docker Desktop running | ☐ |
| P2 | `develop` branch pulled and up to date | ☐ |
| P3 | `.env` created from `.env.example` | ☐ |
| P4 | `docker compose up --build` completes without errors | ☐ |
| P5 | Ollama model pulled (`ollama pull llama3.2` or configured model) | ☐ |
| P6 | Seed corpus ingested into ChromaDB (S5-T17 done) | ☐ |

---

## 1. Authentication — Login Flow

| ID | Test Step | Expected Result | Status | Notes |
|----|-----------|-----------------|--------|-------|
| A-01 | Open Streamlit UI at `http://localhost:8501` | Login page renders with UOW branding; no invisible text | ☐ | |
| A-02 | Submit **student@uow.edu.au / student123** | Logged in as student; dashboard visible | ☐ | |
| A-03 | Submit **lecturer@uow.edu.au / lecturer123** | Logged in as lecturer; upload button visible | ☐ | |
| A-04 | Submit **admin@uow.edu.au / admin123** | Logged in as admin; admin panel accessible | ☐ | |
| A-05 | Submit correct email + wrong password | Login rejected; error message shown | ☐ | |
| A-06 | Submit unknown email | Login rejected; error message shown | ☐ | |
| A-07 | Submit empty email field | UI prevents submission or shows validation error | ☐ | |
| A-08 | Submit empty password field | UI prevents submission or shows validation error | ☐ | |
| A-09 | Log out (if logout button exists) | Returns to login page; session cleared | ☐ | |

---

## 2. Document Upload Flow

| ID | Test Step | Expected Result | Status | Notes |
|----|-----------|-----------------|--------|-------|
| U-01 | Log in as **lecturer**; navigate to Upload | Upload form visible with course selector | ☐ | |
| U-02 | Upload a valid PDF (< 100 MB) to CSIT321 | 202 Accepted; indexing job appears as "queued" | ☐ | |
| U-03 | Upload a valid PPTX file | 202 Accepted; file_type = "pptx" in response | ☐ | |
| U-04 | Upload a valid DOCX file | 202 Accepted; file_type = "docx" in response | ☐ | |
| U-05 | Upload a file with an unsupported extension (.txt) | Rejected with a user-friendly error message | ☐ | |
| U-06 | Attempt upload as **student** role | Rejected; 403 error shown to user | ☐ | |
| U-07 | Attempt upload without being logged in | Redirected to login; 401 shown | ☐ | |
| U-08 | After upload, open Documents list | Uploaded file appears with status "queued" or "indexed" | ☐ | |
| U-09 | Upload same filename twice | Second upload accepted (separate document_id) or meaningful duplicate warning | ☐ | |

---

## 3. Query — Fixture Backend (Sprint 4 mode)

> These tests confirm the fixture path still works before live RAG is active.  
> Mark the entire section SKIP once ChromaDB/Ollama live RAG is confirmed working (S5-AC-03).

| ID | Test Step | Expected Result | Status | Notes |
|----|-----------|-----------------|--------|-------|
| Q-01 | Log in as student; ask "What does RAG stand for?" | Answer returned; `backend_mode = "fixture"` | ☐ | |
| Q-02 | Ask a question with no close fixture match | Fallback response returned; `is_fallback = true` | ☐ | |
| Q-03 | Submit empty query string | Error shown; 400 from API | ☐ | |
| Q-04 | Ask a question for a course the student is not enrolled in | 403 error shown to user | ☐ | |
| Q-05 | Submit 11 queries within 60 seconds from one IP | 11th query returns rate-limit message (429) | ☐ | |

---

## 4. Query — Live ChromaDB / Ollama RAG Backend (Sprint 5 mode)

> These tests apply only after S5-T17 and S5-T18 are marked Done.

| ID | Test Step | Expected Result | Status | Notes |
|----|-----------|-----------------|--------|-------|
| R-01 | Ask "What does RAG stand for?" | Answer grounded in seeded corpus; `backend_mode = "chromadb"` | ☐ | |
| R-02 | Ask "What is a vector embedding?" | Answer returned with at least one `source_reference` citing a real chunk | ☐ | |
| R-03 | Ask "What is the role of ChromaDB in EduRAG?" | Answer mentions ChromaDB metadata/scoping; citations present | ☐ | |
| R-04 | Ask "Explain the chunking strategy used in this project" | Answer cites document chunk from seeded corpus | ☐ | |
| R-05 | Ask "What file formats can be uploaded to EduRAG?" | Answer mentions PDF, PPTX, DOCX | ☐ | |
| R-06 | Ask a question that is completely off-topic (e.g. "What is the capital of France?") | Graceful response; no hallucinated CSIT321 citations | ☐ | |
| R-07 | Verify `source_references` fields contain filename, chunk_index, and page/slide info | Citations include at least `source` and `chunk_index` metadata keys | ☐ | |

---

## 5. Citations

| ID | Test Step | Expected Result | Status | Notes |
|----|-----------|-----------------|--------|-------|
| C-01 | After a live RAG query, inspect the citations panel in UI | Source filename and chunk excerpt visible | ☐ | |
| C-02 | Citations list is not empty for on-topic questions | At least 1 citation per answer | ☐ | |
| C-03 | Citations are absent or replaced by fallback text for off-topic questions | No fake citations appear | ☐ | |
| C-04 | Citation metadata includes `source` (filename) field | Present in `/api/query` JSON response | ☐ | |
| C-05 | Citation metadata includes `chunk_index` or `page` field | Present in `/api/query` JSON response | ☐ | |

---

## 6. Chat History / Sessions

| ID | Test Step | Expected Result | Status | Notes |
|----|-----------|-----------------|--------|-------|
| S-01 | Ask two questions in sequence | Both messages appear in chat in chronological order | ☐ | |
| S-02 | Refresh the browser page during a session | Session history either persists or resets cleanly (no crash) | ☐ | |
| S-03 | `GET /api/sessions` after a query | Returns a list with the session containing the question/answer | ☐ | |
| S-04 | Each chat message shows a timestamp | Timestamps are present and in correct order (oldest first) | ☐ | |
| S-05 | New session starts when `session_id` is not passed | A new `session_id` is returned in the query response | ☐ | |

---

## 7. Docker — Demo Workflow

| ID | Test Step | Expected Result | Status | Notes |
|----|-----------|-----------------|--------|-------|
| D-01 | `docker compose up --build` from a clean checkout | All 5 services start: postgres, chromadb, ollama, api, streamlit | ☐ | |
| D-02 | `docker compose ps` after startup | All services show status "running" (or "healthy" if health checks set) | ☐ | |
| D-03 | Access `http://localhost:8501` in browser | Streamlit UI loads without errors | ☐ | |
| D-04 | Access `http://localhost:5000/api/health` | `{"status": "ok"}` returned | ☐ | |
| D-05 | Access `http://localhost:8000` (ChromaDB) | ChromaDB responds (404 or API root is fine) | ☐ | |
| D-06 | `docker compose down` | All containers stop cleanly; no orphan processes | ☐ | |
| D-07 | Re-run `docker compose up` (no `--build`) | Services restart from cached images in < 60 seconds | ☐ | |
| D-08 | Check compose file: api depends on postgres, chromadb, ollama | CI validates this; confirm manually | ☐ | |

---

## 8. CI — GitHub Actions

| ID | Test Step | Expected Result | Status | Notes |
|----|-----------|-----------------|--------|-------|
| CI-01 | Open the last CI run on GitHub → Actions tab | `CI` workflow shows green ✓ | ☐ | |
| CI-02 | Check "Python tests and fixture validation" job | All pytest tests pass; fixture JSON valid | ☐ | |
| CI-03 | Check "Docker Compose validation" job | Both `docker-compose.yml` and `docker-compose.gpu.yml` validate | ☐ | |
| CI-04 | Create a test PR with a known failing test | CI correctly reports failure (red ✗) | ☐ | |
| CI-05 | Merge PR after CI green | Merge succeeds; develop branch CI stays green | ☐ | |

---

## 9. Accessibility / Readability (Streamlit UI)

| ID | Test Step | Expected Result | Status | Notes |
|----|-----------|-----------------|--------|-------|
| V-01 | Inspect chat bubbles — user vs assistant messages | Both are visually distinguishable; no invisible/white-on-white text | ☐ | |
| V-02 | Inspect form labels on login page | Labels readable; input fields visible | ☐ | |
| V-03 | Inspect citation cards | Text contrast sufficient; not obscured by background | ☐ | |
| V-04 | Inspect upload button | Button is visible and labelled correctly | ☐ | |
| V-05 | Zoom browser to 150% | UI does not break or overlap critically | ☐ | |

---

## 10. Sign-off

| Role | Name | Date | Outcome |
|------|------|------|---------|
| QA Owner | Tung Phuong Anh Huynh | | ☐ All PASS / ☐ Blockers remain |
| Integration check | Thanh Binh Tran | | |
| Demo readiness | Andre | | |

> **Outcome key:**  
> All PASS = checklist satisfied; proceed to evidence pack (S5-T14).  
> Blockers remain = open items must appear in `docs/demo_bug_report_sprint5.md` with owner and ETA.

---

*Owner: Tung Phuong Anh Huynh — CSIT321 Project 37, Group 19*