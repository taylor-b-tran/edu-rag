# Sprint 5 CI / Test Validation Report

**Task:** S5-T06  
**Owner:** Tung Phuong Anh Huynh  
**Date validated:** 18 May 2026  
**Branch:** `develop` (commit: see GitHub Actions run link below)  
**Sprint:** 5 (14 May – 28 May 2026)

> **Purpose:** Record the pass/fail status of every current automated test and CI check.
> This document is evidence for S5-AC-01 (CI gate) and feeds into the A3 evidence pack (S5-T14).
> Update the Status column each time CI is re-run on a new commit.

---

## 1. CI Workflow Summary

| Workflow | Trigger | Last run result | GitHub Actions URL |
|----------|---------|-----------------|--------------------|
| `CI` (`.github/workflows/ci.yml`) | PR / push to `develop` or `main` | ⬜ Pending first S5 run | _paste link after first run_ |
| `Docker Demo` (`.github/workflows/docker-demo.yml`) | Manual / PR | ⬜ Pending first S5 run | _paste link after first run_ |

**How to get the link:** GitHub repo → Actions tab → click the run → copy the URL from your browser address bar.

---

## 2. CI Job Breakdown

### 2a. Job: `python-test` — Python tests and fixture validation

| Step | Description | Status | Notes |
|------|-------------|--------|-------|
| Checkout | `actions/checkout@v4` | ⬜ | |
| Setup Python 3.11 | `actions/setup-python@v5` | ⬜ | |
| Install dependencies | `pip install -r requirements-dev.txt` | ⬜ | |
| **Compile runtime modules** | `py_compile` on api, streamlit, chunker | ⬜ | See §4 for individual files |
| **Validate JSON artifacts** | `fixtures/sample_responses.json`, `tests/test_queries.json`, benchmark JSONs | ⬜ | See §5 |
| **Run pytest** | Full pytest suite | ⬜ | See §3 for per-test results |

### 2b. Job: `docker-compose-validate`

| Step | Description | Status | Notes |
|------|-------------|--------|-------|
| Checkout | `actions/checkout@v4` | ⬜ | |
| Docker version | `docker --version` and `docker compose version` | ⬜ | |
| Validate base Compose | `docker compose -f docker-compose.yml config` | ⬜ | |
| Validate GPU overlay | `docker compose -f docker-compose.yml -f docker-compose.gpu.yml config` | ⬜ | |
| Sprint 5 service contract | Checks postgres, chromadb, ollama, api, streamlit all present; api depends on chromadb + ollama | ⬜ | |

---

## 3. Pytest Results — Per-Test Table

Run with: `python -m pytest -q --tb=short` from repo root.

> **Status key:** ✅ PASS · ❌ FAIL · ⚠️ SKIP · 🔄 XFAIL (expected failure)

### File: `test/test_api.py`

| Test ID | Test Function | Status | Failure reason / Notes |
|---------|---------------|--------|------------------------|
| API-01 | `test_health_reports_core_routes` | ✅ PASS | `/api/health` returns 200, routes present |
| API-02 | `test_login_returns_tokens_with_correct_password` | ✅ PASS | student login returns `dev_access_` token |
| API-03 | `test_login_rejects_wrong_password` | ✅ PASS | 401 on bad password |
| API-04 | `test_login_rejects_unknown_email` | ✅ PASS | 401 on unknown user |
| API-05 | `test_login_rejects_missing_fields` | ✅ PASS | 400 on missing email/password |
| API-06 | `test_query_returns_fixture_answer_when_authenticated` | ✅ PASS | Fixture returns answer + session_id |
| API-07 | `test_query_returns_401_without_token` | ✅ PASS | Unauthenticated query rejected |
| API-08 | `test_query_returns_403_for_unenrolled_course` | ✅ PASS | lecturer blocked from CSIT321 |
| API-09 | `test_upload_queues_document_when_lecturer_authenticated` | ✅ PASS | 202 + indexing_job queued |
| API-10 | `test_upload_returns_401_without_token` | ✅ PASS | 401 without token |
| API-11 | `test_upload_returns_403_for_student_role` | ✅ PASS | 403 for student |
| API-12 | `test_documents_returns_401_without_token` | ✅ PASS | 401 without token |
| API-13 | `test_documents_returns_list_when_authenticated` | ✅ PASS | Returns `documents` list |
| API-14 | `test_sessions_returns_collection_after_query` | ✅ PASS | Session recorded after query |

### File: `test/test_chunker.py`

| Test ID | Test Function | Status | Failure reason / Notes |
|---------|---------------|--------|------------------------|
| CHK-01 | `TestEmptyAndWhitespace::test_empty_string_returns_empty_list` | ✅ PASS | `chunk_text("")` → `[]` |
| CHK-02 | _(additional chunker tests — fill in after CI run)_ | ⬜ | |

> **Note:** Update this table by pasting the `pytest -v` output into the Notes column after each CI run.
> The command to get verbose per-test output: `python -m pytest -v --tb=short 2>&1 | tee docs/ci_pytest_raw_sprint5.txt`

---

## 4. Compile Check Results

| Module | Command | Status | Notes |
|--------|---------|--------|-------|
| `src/api/app.py` | `python -m py_compile src/api/app.py` | ⬜ | |
| `apps/integration/backend/api.py` | `python -m py_compile apps/integration/backend/api.py` | ⬜ | |
| `apps/streamlit/main.py` | `python -m py_compile apps/streamlit/main.py` | ⬜ | |
| `src/document_processor/chunker.py` | `python -m py_compile src/document_processor/chunker.py` | ⬜ | |

---

## 5. JSON Artifact Validation

| File | Valid JSON | Notes |
|------|------------|-------|
| `fixtures/sample_responses.json` | ⬜ | |
| `tests/test_queries.json` | ⬜ | |
| `docs/rag_config_benchmark_2026-04-22.json` | ⬜ | |
| `docs/rag_config_benchmark_31q.json` | ⬜ | |

---

## 6. Known Broken / Skipped Tests

> List any tests that are currently failing or skipped, with the reason and owner.

| Test | Status | Reason | Owner | ETA to fix |
|------|--------|--------|-------|-----------|
| _(none known at Sprint 5 start)_ | — | — | — | — |

> If a new failure is found during Sprint 5, add it here and also log it in `docs/demo_bug_report_sprint5.md`.

---

## 7. Sprint 5 Test Coverage Gaps

The following scenarios are **not yet covered** by automated tests. These represent known testing debt for Sprint 5 or future sprints.

| Gap | Reason not tested | Risk | Recommended action |
|-----|-------------------|------|-------------------|
| ChromaDB retrieval path (`backend_mode = "chromadb"`) | Live ChromaDB requires a running container — not available in CI without `docker-in-docker` | High — core Sprint 5 feature untested in CI | Add a mock ChromaDB client or use `pytest-mock` to stub the retriever |
| Ollama generation path | Ollama requires GPU/CPU model — not in CI runner | High | Stub `ollama.chat()` call in tests; validate prompt construction separately |
| Rate limiting at exactly 10 req/min boundary | Requires 10 sequential requests in unit tests | Low | Add a dedicated rate-limit test with mocked `time.time()` |
| Session continuity across two separate login calls | Not tested — multi-client scenario | Medium | Add integration test with two test clients sharing a session_id |
| File size limit enforcement (> 100 MB upload) | Test client makes in-memory upload; large size not simulated | Low | Add a test that sends a `Content-Length` header > max and checks 413 |

---

## 8. Validation Evidence (paste here after CI run)

```
# Paste the GitHub Actions "Run pytest" step log output here after the first S5 CI run.
# Example format:
#
# collected 14 items
#
# test/test_api.py ..............                          [100%]
#
# 14 passed in 2.31s
```

---

## 9. Update Log

| Date | Author | Change |
|------|--------|--------|
| 18 May 2026 | Tung Phuong Anh Huynh | Initial document created (Sprint 5 kickoff state) |

---

*Owner: Tung Phuong Anh Huynh — CSIT321 Project 37, Group 19*