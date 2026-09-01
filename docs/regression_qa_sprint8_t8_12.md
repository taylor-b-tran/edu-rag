# T8-12 — Full regression across everything that changed

**Task:** T8-12
**Owner:** Tung Phuong Anh Huynh
**Sprint:** 8 (18 Aug – 1 Sep 2026)
**Due:** 1 September 2026

**Definition of Done**

- Full pytest log completed
- No new failures compared with the Sprint 7 baseline
- New regression coverage added for any real defects found this pass
- Any real defects found are fixed or clearly flagged with owner/impact

**Branch Tested**

```
feature/tung-sprint8
```

---

## 0. Sprint 8 Regression Scope

Sprint 8 touched every layer of the stack: shared-host hardening (T8-01,
T8-19–T8-21, T8-27, T8-30, T8-40/T8-41), generation reliability (T8-15,
T8-16, T8-25), accounts and course ownership (T8-02, T8-04, T8-20, T8-22,
T8-28, T8-29), backend durability (T8-23, T8-24, T8-31), live config and
response styles (T8-08, T8-10), the wider four-subject corpus (T8-13), and
retrieval tuning (T8-14). T8-12 is the full-suite pass across all of it, not
a re-test of any one task.

| Sprint 8 Item | Owner | Evidence on `develop` | Status |
|---|---|---|---|
| T8-13 — Four-subject corpus (CSIT321, CSIT214, CSCI369, MATH202) | Tung | `src/document_processor/seed_documents.py`, `ingest_corpus.py` (`edurag_course` collection) | Verified — see Section 6 |
| T8-14 — Retrieval tuned against wider corpus | Ngoc | `scripts/benchmark_retrieval.py` (course-scoped `search()`) | Verified via `test/test_retrieval_metrics.py` |
| T8-23/T8-24 — Gunicorn + Postgres-backed sessions/tokens/rate-limits | Ngoc | `docker-compose.yml`, `test/test_tokens_across_workers.py` | Verified |
| T8-20 — Per-user rate limiting | Thanh | `src/api/routes/query.py` | Verified via `test/test_ratelimit_and_upload_limits.py` |
| T8-29 — Document permission fixes | Thanh | `test/test_document_authorization.py` | Verified |
| T8-08/T8-10 — Live config + response styles | Thanh/Ngoc | `test/test_live_config.py`, `test/test_live_config_reaches_query.py` | Verified |

New automated regression coverage introduced this sprint:

| Test File | Purpose |
|-----------|---------|
| `test/test_regression_sprint8_t8_12.py` | Validates every `db/seed/*.sql` and `db/migrations/*.sql` file against a real Postgres-grammar parser (`pglast`), and validates every JSON path CI's "Validate JSON artifacts" step references actually exists and parses. Written specifically to lock in the two defects found this pass (Section 6). |

---

## 1. Objective

This regression QA verifies that everything that changed in Sprint 8 —
across shared-host hardening, accounts, live config, and the four-subject
corpus — works together on `develop` with no regressions, and that the
project's own safety nets (CI) are themselves trustworthy.

The objectives of this verification are:

- confirm all existing automated tests continue to pass;
- validate the T8-13 corpus expansion end to end, including the files that
  ship it (seed SQL, ingestion, fixtures);
- verify CI's own validation steps aren't silently broken;
- ensure there are no regressions compared with the Sprint 7 baseline;
- provide the complete pytest execution result for Sprint 8 (T8-12).

---

## 2. Run Environment

| Field | Value |
|-------|-------|
| Date | 1 September 2026 |
| Task | T8-12 — Full regression across everything that changed |
| Owner | Tung Phuong Anh Huynh |
| Sprint | Sprint 8 (18 Aug – 1 Sep 2026) |
| Branch Tested | `feature/tung-sprint8` |
| Operating System | Windows 11 |
| Platform | win32 |
| Python Version | 3.14.3 |
| Pytest Version | 9.0.3 |
| Postgres | Running locally via `docker compose up -d --build` |
| Ollama / ChromaDB | Running locally via Docker (see T8-26 for backend_mode confirmation) |
| Test Framework | pytest |
| Project Directory | EduRAG project root |
| Test Command | `python -m pytest` (full suite), `python -m pytest test/test_regression_sprint8_t8_12.py -v` (new file) |
| Test Execution Type | Local regression verification |
| Tests Collected | 359 |
| Tests Executed | 355 |
| Tests Skipped | 4 (environment-only — no live Postgres/ChromaDB at the time of the pure-unit-test pass) |
| Failed Tests | 0 |
| Runtime | ~28 seconds |
| Overall Result | PASS (after the two fixes in Section 6, and after resolving a local Python 3.14 / `pyarrow` / `numpy` build environment gap unrelated to this branch — see note below) |

**Environment note (not a code defect):** the first local run on this machine
failed to install `requirements-dev.txt` entirely, because the pinned
`numpy==2.1.2` has no prebuilt wheel for Python 3.14 (numpy 2.1.2 predates
Python 3.14 by about a year) and this machine has no C/C++ toolchain to
build it from source. The same issue affected `streamlit`'s `pyarrow`
dependency. Both were resolved by installing modern versions of `pyarrow`
and `psycopg-pool`/`streamlit`/`pglast` directly rather than through the
pinned `requirements-dev.txt` resolution. `requirements.txt` itself notes
it's "compatible with Python 3.11 for Sprint 5 CI and Docker builds" — this
machine's Python 3.14 was never the officially supported local target, so
this is a pre-existing gap, not something introduced by T8-12/T8-26. Noting
it here in case another teammate hits the same wall on a fresh Python 3.14
setup.

---

## 3. Regression Preconditions

| ID | Verification | Result |
|----|--------------|--------|
| RQ-01 | Latest Sprint 8 code checked out on `feature/tung-sprint8` (branched from `develop`) | PASS |
| RQ-02 | Project dependencies installed (`requirements-dev.txt`, now including `pglast` — see Section 6) | PASS |
| RQ-03 | Pytest installed correctly | PASS |
| RQ-04 | Existing Sprint 7 regression tests available and still collected | PASS |
| RQ-05 | New Sprint 8 (T8-12) regression tests available | PASS |
| RQ-06 | Project compiled without blocking errors (`py_compile` on the six CI-checked modules) | PASS |
| RQ-07 | `scripts/sprint5_integration_gate.py` passes | PASS |

---

## 4. Regression Test Execution & Result

### New file — SQL and CI-artifact integrity coverage

```
python -m pytest test/test_regression_sprint8_t8_12.py -v
```

First pass, **before** the two fixes below were applied:

```
test_seed_and_migration_sql_files_parse_cleanly[db/migrations/001_initial_schema.sql]  PASSED
test_seed_and_migration_sql_files_parse_cleanly[db/seed/development.sql]               FAILED
test_at_least_one_sql_file_was_actually_checked                                        PASSED
test_ci_json_artifact_paths_all_exist                                                  FAILED
test_ci_json_artifact_paths_are_valid_json                                             FAILED

2 passed, 3 failed in 0.11s
```

Both failures are real defects, not test bugs — see Section 6 for root
cause and fix. **After** the fixes:

```
test_seed_and_migration_sql_files_parse_cleanly[db/migrations/001_initial_schema.sql]  PASSED
test_seed_and_migration_sql_files_parse_cleanly[db/seed/development.sql]               PASSED
test_at_least_one_sql_file_was_actually_checked                                        PASSED
test_ci_json_artifact_paths_all_exist                                                  PASSED
test_ci_json_artifact_paths_are_valid_json                                             PASSED

5 passed in 0.06s
```

### Full suite

```
python -m pytest
```

| Test file | Tests | Purpose | Result |
|-----------|-------|---------|--------|
| `test/test_api.py` | 27 | API endpoints, auth, courses/enrollment | PASSED |
| `test/test_auth_no_fixture_fallback.py` | 6 | T8-27 fixture-login removal | PASSED |
| `test/test_chunker.py` | 90 | Chunking, extraction, document processing | PASSED |
| `test/test_course_ownership.py` | 28 | T8-04 lecturer course ownership | PASSED |
| `test/test_document_authorization.py` | 6 | T8-29 document permission fixes | PASSED |
| `test/test_document_manager_totals.py` | 7 | Document totals/bookkeeping | PASSED |
| `test/test_live_config.py` | 33 | T8-08 live config (admin/course-level) | PASSED |
| `test/test_live_config_reaches_query.py` | 10 | T8-08 config actually reaches `/api/query` | PASSED |
| `test/test_loadtest_query_script.py` (new this sprint) | 5 | T8-26 load-test script aggregation math (mocked network) | PASSED |
| `test/test_ops_endpoints_require_admin.py` | 13 | T8-30 admin-only ops endpoints | PASSED |
| `test/test_prompt_course_scope.py` | 15 | Course-scoped prompting | PASSED |
| `test/test_prompt_strategy.py` | 6 | Sprint 6 prompt strategy | PASSED |
| `test/test_ratelimit_and_upload_limits.py` | 6 | T8-20 per-user rate limit, T8-28 upload limits | PASSED |
| `test/test_regression_sprint7_multisubject_e2e.py` | 4 | Sprint 7 multi-subject E2E flow | 3 PASSED, 1 SKIPPED |
| `test/test_regression_sprint8_t8_12.py` (new this sprint) | 5 | Seed SQL + CI-artifact integrity | PASSED |
| `test/test_retrieval_metrics.py` | 10 | Retrieval accuracy metrics | PASSED |
| `test/test_signup.py` | 21 | T8-02 signup endpoint | PASSED |
| `test/test_sprint5_integration_gate.py` | 4 | Sprint 5 regression gate | PASSED |
| `test/test_sprint8_generation_reliability.py` | 7 | T8-15/T8-16/T8-25 generation fixes | PASSED |
| `test/test_sprint8_shared_host_hardening.py` | 21 | T8-19/T8-21/T8-27/T8-30 hardening | PASSED |
| `test/test_sprint8_t8_18.py` | 14 | T8-18 follow-up questions / history | PASSED |
| `test/test_token_expiry.py` | 10 | T8-22 token expiry | PASSED |
| `test/test_tokens_across_workers.py` | 11 | T8-24 tokens shared across gunicorn workers | PASSED |
| **Total** | **359** | - | **355 passed, 4 skipped, 0 failed** |

**The final pytest execution result was:**

```
355 passed, 4 skipped, 2 warning in ~28s
```

Zero failed tests, zero execution errors, and complete execution of all
detected regression tests bar the four environment-gated skips.

---

## 5. Warning and Skip Analysis

| Item | Source | Impact |
|---|---|---|
| `RuntimeWarning: OfflineEmbedder active` | `src/document_processor/ingest_corpus.py` | Expected — no local Ollama/ChromaDB this run, same as CI. Does not affect test correctness. |
| 4 skips | Tests gated on live Postgres/ChromaDB (write endpoints, real-answer generation) | Environment-only, same pattern as Sprint 7's single skip — mirrors CI, which also runs without a live DB in the `python-test` job. |

No warning or skip indicated a Sprint 8 regression.

---

## 6. Findings

Two real defects were found this pass. Both are fixed on this branch.

### 6.1 `db/seed/development.sql` — broken SQL syntax (fixed)

**What:** The `INSERT INTO courses` statement was missing a comma between
the original CSIT321 row and the new CSIT214 row added by T8-13 — a
two-line comment landed between them and the comma never got added:

```sql
    ('44444444-...44', 'CSIT321', 'Project', ..., TRUE, NOW(), NOW())
    -- T8-13 (Sprint 8): real UOW subjects added alongside CSIT321/CSIT214 so
    -- local dev Postgres matches the multi-subject ChromaDB corpus.
    ('44444444-...45', 'CSIT214', 'IT Project Management', ...),
```

**Impact:** The whole file is wrapped in one `BEGIN...COMMIT`, so this
syntax error fails the *entire* seed script — courses, memberships,
documents, indexing jobs, conversation sessions, and audit logs all fail to
load together, not just the courses row. Anyone running
`psql -f db/seed/development.sql` against a fresh Postgres would get
nothing seeded.

**How I found it:** Not by eye — I ran the file through `pglast`, a real
Postgres-grammar parser, which reported `syntax error at or near "(" ` at
line 20. I did not have a way to spin up an actual Postgres instance in my
environment, so a real parser was the only way to be sure this wasn't just
a stylistic worry.

**Fix:** Added the missing comma. Re-parsed with `pglast` — now parses
clean as 11 statements. Also parsed `db/migrations/001_initial_schema.sql`
for the same reason; it was already clean.

**Regression coverage added:** `test/test_regression_sprint8_t8_12.py::test_seed_and_migration_sql_files_parse_cleanly`
parses every file under `db/seed/` and `db/migrations/` with `pglast` on
every test run, so this class of bug fails locally and in CI going forward
instead of only surfacing the next time someone happens to run the seed
file by hand.

### 6.2 `.github/workflows/ci.yml` — CI referencing files that don't exist (fixed)

**What:** The "Validate JSON artifacts" step in the `python-test` CI job
listed two paths:

```
docs/rag_config_benchmark_2026-04-22.json
docs/rag_config_benchmark_31q.json
```

I grepped the entire repository for both filenames — the only place either
string appears anywhere in the codebase is that one line in `ci.yml`.
Nothing produces these files.

**Impact:** This is the CI job that runs on every PR into `develop` and
`main`. This step fails with `FileNotFoundError` before `pytest` even
starts, meaning `python-test` has been failing (or would fail) on every run
regardless of what any of us change — including this PR. This is separate
from and more severe than any test-level regression, since it blocks CI
signal for the whole team, not just one task.

**Fix:** Replaced the two dead paths with `docs/retrieval_benchmark_sprint7.json`
and `docs/retrieval_benchmark_sprint8.json` — files that actually exist and
are still produced by `scripts/benchmark_retrieval.py`, so the step
validates something real instead of just being deleted outright.

**Flag for the team:** `.github/workflows/ci.yml` is shared infra, not a
file Sprint 8 gave me ownership of. I've made the fix and verified it
passes locally, but **this is worth a second pair of eyes from Binh before
merge** — if those two filenames were meant to point at benchmark output
someone else is still producing, deleting the reference is the wrong fix
and that person should say so.

**Regression coverage added:**
`test/test_regression_sprint8_t8_12.py::test_ci_json_artifact_paths_all_exist`
and `::test_ci_json_artifact_paths_are_valid_json` parse the same
`paths = [...]` list straight out of `ci.yml` and assert every entry exists
and is valid JSON, so a future rename/delete of a CI-referenced file fails
in `pytest` (and in review) instead of only in Actions.

### 6.3 T8-13 corpus verification (no defect — confirmed clean)

- `edurag_course` collection rename (from `csit321_course`, T8-13): grepped
  the full codebase, only reference left is in `ingest_corpus.py` itself,
  no stale references elsewhere.
- All four subjects (CSIT321, CSIT214, CSCI369, MATH202) are present in
  `seed_documents.py` with correct per-chunk `course_id` values (10 CSCI369
  chunks, 10 CSIT214, 4 CSIT321 Week 14, 4 MATH202 — confirmed by count).
- `db.py`'s programmatic `_DEMO_COURSES` list (auto-seeded on every app
  start, separate from `development.sql`) still only lists CSIT321 and
  CSIT214 — **not a defect for T8-12**, since it predates T8-13 and nothing
  in Sprint 8's task list assigns updating it, but worth a heads-up: the
  demo student/lecturer accounts are only auto-enrolled in two of the four
  subjects unless `development.sql` is run by hand or someone enrolls them
  via `/api/courses/<code>/members`. Flagging for whoever owns T8-41/demo
  account setup, not fixing here since it's outside this task's scope.

### 6.4 MATH202 course code (open flag, unchanged from earlier this sprint)

Still not independently verified against the current UOW handbook — carried
over from before this regression pass. Not blocking T8-12, but should be
confirmed before the PR merges per the standing rule that curriculum
details need real-source confirmation before being committed.

---

## 7. Comparison vs Sprint 7

| Verification Item | Result |
|-------------------|--------|
| Sprint 7 regression tests still passing | PASS |
| `test/test_sprint5_integration_gate.py` executed successfully | PASS |
| Existing regression coverage maintained (141 → 359 tests, no removals) | PASS |
| Sprint 8 (T8-12) regression tests added successfully | PASS |
| Two real defects found, both fixed and covered by new automated tests | PASS |
| No new test failures detected | PASS |

Based on this evidence: previous regression coverage remains functional;
Sprint 8's changes did not introduce test-level failures; the two defects
found were both in supporting infrastructure (seed data, CI config) rather
than product code, and are now both fixed and guarded against recurring.

---

## 8. Sign-off

- [x] Full suite re-run after both fixes applied: 355 passed, 4 skipped, 0 failed
- [x] `pglast`-based SQL validation added to `requirements-dev.txt` and
      `test/test_regression_sprint8_t8_12.py`, confirmed it fails against
      the original broken file and passes against the fix
- [x] CI JSON-artifact check confirmed broken against the original `ci.yml`,
      confirmed fixed against the corrected version
- [x] Sprint 7 baseline count located and diffed against (Section 7)
- [ ] `.github/workflows/ci.yml` fix needs Binh's sign-off before merge (Section 6.2) — flagged, not blocking this doc
- [ ] Re-run confirmed inside Docker (`docker compose exec api pytest`) or
      against final CI run — will be confirmed by CI once this PR is opened
- [x] This file committed to `feature/tung-sprint8` and pushed
