# T12 — Automated permission checks across every endpoint

**Task:** T12 (Sprint 10)
**Owner:** Tung Phuong Anh Huynh
**Checked by:** Andre
**Sprint:** 10
**Status:** Rewritten after Taylor's review of PR #134 (CI was red). All 30
cases pass against a real Postgres, both locally (Section 2) and in CI on
PR #136 (Section 4).

**Definition of Done** (from the sprint plan)
> The suite fails if either defect is reintroduced, and every new endpoint
> joins it in the same change that adds it.

---

## 0. What changed since the first version

The version merged in PR #134 signed up real users through
`/api/auth/signup` and logged in through `/api/auth/login`. Taylor's review
found five problems with that approach, all fixed here by switching to the
isolated-Postgres-schema pattern already used by
`test_student_self_enrolment_postgres.py` and
`test_token_transactions_postgres.py` — every persona's user/course/
membership/token row is inserted directly by SQL into a throwaway schema,
and only route *behaviour* is exercised through the real Flask app:

| # | Problem in the merged version | Fix |
|---|-------------------------------|-----|
| 1 | Logged the admin in with hardcoded `"admin123"`; the real demo password has come from `PAEDIA_DEMO_ADMIN_PASSWORD` since #127 | No login call at all — a token row is inserted directly via `db.insert_token_pair`, same as the sibling Postgres tests already do |
| 2 | Read `user["user_id"]` from the signup response; the API returns `user["id"]` | N/A — user ids come straight from the `INSERT ... RETURNING id` that creates them |
| 3 | Fixed username per persona (`t12own`, `t12oth`, ...) collided on a second run against a persistent database | Each test gets its own randomly-named schema, dropped at teardown — nothing persists between runs |
| 4 | Assumed `CSIT321`/`T12-OUTSIDE` were safe, unused course codes | Course codes (`T12TGT`/`T12OTH`) live only inside the throwaway schema; nothing else in the database can collide with them |
| 5 | The one identifier-form check hit `/api/courses/<code>/members` (which has never accepted anything but a course code) and accepted **either** 200 or 404 — so it could not actually catch a regression on the real surface | `TestCourseIdentifierForms` now hits `/api/documents` (the actual T6/T7 regression surface) and asserts one strict status per persona, in both identifier forms |

**Coverage:** `/api/courses/<code>/settings`, `/api/courses/<code>/members`,
`/api/documents` (unscoped list — the T7 surface), `/api/document/<id>`,
`/api/admin/stats`, and the identifier-form check on `/api/documents` (the
T6 surface). Same "not yet covered" list as before, unchanged by this fix:
`/api/upload`, `/api/document/<id>/file`, `/api/indexing-jobs/<id>`,
`/api/sessions*`, `/api/query`, `/api/admin/audit-logs`, `/api/warmup`,
`/api/settings` (global scope), `/api/auth/*`.

---

## 1. Run environment (this pass)

| Field | Value |
|-------|-------|
| Date | 27 Sept 2026 |
| Platform | linux (sandboxed verification run — CI itself runs on `ubuntu-latest`, see `.github/workflows/ci.yml`) |
| Python | 3.12.3 (CI pins 3.11; both run this file the same way — nothing here is version-sensitive) |
| Postgres | local `postgres:16`-equivalent instance, disposable `edurag_test` database and role |
| Test command | `python -m pytest test/test_sprint10_t12_permission_matrix.py -v` |

**Running it locally — never against the live Postgres.** Do not use
`docker compose up -d postgres`: on the GPU host that is the live database,
and this suite creates and drops schemas in whatever it points at. Use a
throwaway container on a different port:

```powershell
docker run --rm -d --name edurag-t12-pg -p 55432:5432 `
  -e POSTGRES_USER=edurag_test -e POSTGRES_PASSWORD=t12_disposable `
  -e POSTGRES_DB=edurag_test postgres:16
$env:PAEDIA_TEST_POSTGRES_HOST = "127.0.0.1"
$env:POSTGRES_PORT = "55432"
$env:POSTGRES_USER = "edurag_test"
$env:POSTGRES_PASSWORD = "t12_disposable"
$env:POSTGRES_DB = "edurag_test"
python -m pytest test/test_sprint10_t12_permission_matrix.py -v
docker stop edurag-t12-pg
```

---

## 2. Result — with Postgres available

```
============================= test session starts ==============================
collected 30 items

TestCourseSettings::test_only_the_owner_or_admin_can_write[none] PASSED
TestCourseSettings::test_only_the_owner_or_admin_can_write[student_in] PASSED
TestCourseSettings::test_only_the_owner_or_admin_can_write[student_out] PASSED
TestCourseSettings::test_only_the_owner_or_admin_can_write[lecturer_owner] PASSED
TestCourseSettings::test_only_the_owner_or_admin_can_write[lecturer_other] PASSED
TestCourseSettings::test_only_the_owner_or_admin_can_write[admin] PASSED
TestCourseMembers::test_roster_visible_only_to_manager[none] PASSED
TestCourseMembers::test_roster_visible_only_to_manager[student_in] PASSED
TestCourseMembers::test_roster_visible_only_to_manager[student_out] PASSED
TestCourseMembers::test_roster_visible_only_to_manager[lecturer_owner] PASSED
TestCourseMembers::test_roster_visible_only_to_manager[lecturer_other] PASSED
TestCourseMembers::test_roster_visible_only_to_manager[admin] PASSED
TestDocumentList::test_unqualified_list_never_shows_a_foreign_course[student_in] PASSED
TestDocumentList::test_unqualified_list_never_shows_a_foreign_course[student_out] PASSED
TestDocumentList::test_unqualified_list_never_shows_a_foreign_course[lecturer_owner] PASSED
TestDocumentList::test_unqualified_list_never_shows_a_foreign_course[admin] PASSED
TestDocumentList::test_none_is_401_not_an_empty_200 PASSED
TestDocumentMetadata::test_document_scoped_to_course_membership[none] PASSED
TestDocumentMetadata::test_document_scoped_to_course_membership[student_in] PASSED
TestDocumentMetadata::test_document_scoped_to_course_membership[student_out] PASSED
TestDocumentMetadata::test_document_scoped_to_course_membership[lecturer_owner] PASSED
TestDocumentMetadata::test_document_scoped_to_course_membership[lecturer_other] PASSED
TestDocumentMetadata::test_document_scoped_to_course_membership[admin] PASSED
TestAdminOnlyRoutes::test_non_admin_refused[none] PASSED
TestAdminOnlyRoutes::test_non_admin_refused[student_in] PASSED
TestAdminOnlyRoutes::test_non_admin_refused[lecturer_owner] PASSED
TestAdminOnlyRoutes::test_non_admin_refused[lecturer_other] PASSED
TestAdminOnlyRoutes::test_admin_allowed PASSED
TestCourseIdentifierForms::test_enrolled_student_reaches_documents_by_code_and_uuid_identically PASSED
TestCourseIdentifierForms::test_unenrolled_student_refused_identically_by_both_forms PASSED

============================= 30 passed in 56.75s ==============================
```

## 3. Result — without Postgres available (the state the main `pytest -q` step runs in)

```
============================= 30 skipped in 3.98s ==============================
```
Confirms this file cannot reproduce PR #134's `signup_unavailable` failure
mode in the main test step: it now opts out cleanly instead of trying (and
failing) to reach a database that step deliberately doesn't provide. Every
other file's pass/fail count is unaffected — this file only adds skips to
that step, no new failures.

---

## 4. CI wiring

Added to the existing Postgres-opt-in step in `.github/workflows/ci.yml`
("Verify token transactions, course joining and demo account seeding on
isolated PostgreSQL schemas"), alongside the three files that already use
this pattern:

```
python -m pytest test/test_token_transactions_postgres.py test/test_student_self_enrolment_postgres.py test/test_demo_accounts_postgres.py test/test_sprint10_t12_permission_matrix.py -q
```

**CI result:** PR #136's `CI / Python tests and fixture validation` job —
which contains this Postgres step — passed, along with the Docker Compose
validation and Demo stack smoke test checks. (An earlier run of that job failed
on the Sprint 5 integration gate, not on this test: the gate's conflict-marker
check used `startswith("=======")` and misread pytest's own `=====` banner
lines inside this doc's code blocks. Fixed in
`scripts/sprint5_integration_gate.py` by matching git's exact marker format.)

---

## 5. Result

**Overall Result:** PASS (30/30, against real Postgres; clean skip without it)

**Endpoints with verified persona coverage this sprint:** 5 routes
(`/api/courses/<code>/settings`, `/api/courses/<code>/members`,
`/api/documents`, `/api/document/<id>`, `/api/admin/stats`), plus the
identifier-form check on `/api/documents`.

**Endpoints still needing coverage:** `/api/upload`,
`/api/document/<id>/file`, `/api/indexing-jobs/<id>`, `/api/sessions*`,
`/api/query`, `/api/admin/audit-logs`, `/api/warmup`, `/api/settings`
(global scope), `/api/auth/*`. The `world` fixture in the test file is
reusable for all of them — each is a new test function using the same
inserted personas, not a new setup approach.

---

## 6. Sign-off

- [x] This file is a finalised file with a fully running test
- [x] Run against a real local Postgres (Section 2) and confirmed to skip
      cleanly without one (Section 3)
- [x] Wired into `.github/workflows/ci.yml`'s Postgres step (Section 4)
- [ ] Still to be confirmed once more against CI's own Postgres service
      (this doc's Section 2 was run locally, not inside GitHub Actions —
      push and check the Actions run before marking this fully closed)