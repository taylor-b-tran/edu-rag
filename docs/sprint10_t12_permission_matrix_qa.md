# T12 — Automated permission checks across every endpoint

**Task:** T12 (Sprint 10)
**Owner:** Tung Phuong Anh Huynh
**Checked by:** Andre
**Sprint:** 10
**Noted:** This is the draft file that haven't running test yet

**Definition of Done** (from the sprint plan)
> The suite fails if either defect is reintroduced, and every new endpoint
> joins it in the same change that adds it.

**Branch Tested**

```
feature/tung-sprint10
```

---

## 0. Why this task exists

Both access-control defects found this sprint (T6 — course identifier
resolution, T7 — document list scoping) existed because the previous tests
only asserted that a permission check was *present* (some 401/403
somewhere), never that it returned the *right* body to the *wrong* kind of
user. `test/test_sprint10_t12_permission_matrix.py` checks response bodies,
not just status codes, across a persona matrix: unauthenticated, enrolled
student, unenrolled student, owning lecturer, non-owning lecturer, admin.

**Coverage in this pass:** `/api/courses`, `/api/courses/<code>/members`,
`/api/courses/<code>/settings`, `/api/documents`, `/api/document/<id>`,
`/api/admin/stats`, plus a re-assertion of the T6 (course id/UUID) fix.

**Not yet covered — flagged, not silently dropped:** `/api/upload`,
`/api/document/<id>/file`, `/api/indexing-jobs/<id>`, `/api/sessions*`,
`/api/query`, `/api/admin/audit-logs`, `/api/warmup`, `/api/settings`
(global scope), `/api/auth/*`. The persona fixtures in the new test file are
reusable for all of them — each is a ~5-line addition to the file, not a new
approach.

---

## 1. Run Environment

| Field | Value |
|-------|-------|
| Date | <PASTE: date you ran this> |
| Operating System | Windows 11 |
| Platform | win32 |
| Python Version | <PASTE: python --version output> |
| Pytest Version | <PASTE: pytest --version output> |
| Postgres | <PASTE: running via docker compose up -d postgres? local install? — this suite needs a real DB, every persona is a real signup> |
| Test Command | `python -m pytest test/test_sprint10_t12_permission_matrix.py -v` |

---

## 2. Preconditions

| ID | Verification | Result |
|----|--------------|--------|
| RQ-01 | `feature/tung-sprint10` checked out, branched from `develop` | <PASS/FAIL> |
| RQ-02 | `docker compose up -d postgres chromadb` running (this suite signs up real users and needs a live DB) | <PASS/FAIL> |
| RQ-03 | `pip install -r requirements-dev.txt` up to date | <PASS/FAIL> |
| RQ-04 | `test/test_sprint10_t12_permission_matrix.py` present on this branch | <PASS/FAIL> |

---

## 3. New file — permission matrix

```
python -m pytest test/test_sprint10_t12_permission_matrix.py -v
```

<PASTE THE FULL TERMINAL OUTPUT HERE, INCLUDING THE FINAL SUMMARY LINE>

```
<paste here>
```

### If anything failed

For each failing test, note here whether it's:
- **a real defect** — the endpoint really does leak data or refuse the
  wrong caller. Fix the route, not the test.
- **a wrong assumption in the test** — e.g. `TestCourseIdentifierForms`
  asserts `_require_course_manager` still takes code-only for
  `/api/courses/<c>/members`; if T6's work was extended to that route too,
  this assertion needs updating, not the route.

| Test | Result | Real defect or test assumption? | Action |
|------|--------|----------------------------------|--------|
| <paste failing test name> | FAIL | <your analysis> | <fix route / fix test / defer> |

---

## 4. Full suite regression check

Run the whole suite to confirm this file didn't destabilise anything else
(new signups, new courses created per test run):

```
python -m pytest
```

<PASTE FULL SUMMARY LINE, e.g. "148 passed, 1 skipped, 2 warnings in 118.4s">

```
<paste here>
```

---

## 5. Result

**Overall Result:** <PASS / FAIL — do not mark PASS if any test above is a
real defect rather than a test-assumption issue>

**Endpoints with verified persona coverage this sprint:** <count>/36
**Endpoints still needing coverage (see Section 0):** <list, so whoever
picks this up next doesn't have to re-derive it>

---

## 6. Sign-off

- [] This file is a finalised file with a fully running test
- [x] This file committed to `feature/tung-sprint10` and pushed