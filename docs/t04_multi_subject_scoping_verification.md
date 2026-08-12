# T04 — Upload/Ingest Scoping Verification

**Task:** Confirm the upload/ingest path scopes correctly to the selected course, for courses created through the new T03 admin API (not just the two fixture courses).
**Done by:** Thanh Binh Tran
**Result:** No code changes needed — the T02 course-code design already made this work. Verified live end to end against the running stack.

## Why this wasn't a given

Course-scoped retrieval (`src/document_processor/rag_pipeline.py`) filters ChromaDB by a `course_id` string tag. Enrollment checks (`APIState.is_enrolled`) and course resolution (`APIState.resolve_course`) originally only knew about the two courses hardcoded in `fixtures/sample_responses.json`. T03 lets an admin create courses that exist **only** in Postgres. The open question was whether upload, indexing, and query would still scope correctly to a course that has no fixture entry at all.

They do, because of a decision made back in T02: `get_enrolled_course_codes()` returns course **codes**, not Postgres UUIDs, and `is_enrolled()` checks the user's enrolled-course list directly before ever consulting the fixture list. So a Postgres-only course code just flows through unchanged.

## Verification steps (live, against the running Docker stack)

1. As admin, created two courses that exist only in Postgres — `CSIT498` and `CSIT499` — via the T03 API. Enrolled the demo lecturer in both, and the demo student in `CSIT499` only (left unenrolled in `CSIT498` to test the negative case).
2. Lecturer (fresh login, so the JWT picks up the new memberships) uploaded a distinct `.docx` to each course. Both indexed successfully; ChromaDB chunks were tagged `course_id: CSIT498` / `CSIT499` as expected.
3. Student (not enrolled in `CSIT498`) queried it → **403 "Not enrolled in this course."**
4. Lecturer (enrolled) queried `CSIT498` → correct grounded answer, citing `csit498_doc.docx`.
5. Student (enrolled) queried `CSIT499` → correct grounded answer, citing `csit499_doc.docx`.
6. Isolation check: student asked the `CSIT498`-specific question while scoped to `CSIT499` → no fabricated answer, `is_fallback: true`, no sources — confirms retrieval doesn't leak across courses even when both are Postgres-only.

## Side note

This also closes the fixture-inconsistency gap flagged in the T22/T28 zip verification (`docs/t22_t28_zip_verification.md`) — login `enrolled_courses` used to return UUIDs while retrieval matched on codes. T02's fix (codes, not UUIDs) is what step 3-6 above rely on.

## Cleanup

Deleted the two test courses, their uploaded documents, and ChromaDB chunks after verification — live Postgres/ChromaDB are back to the CSIT321/CSIT214 baseline.

## Result

Upload/ingest scoping is correct for any course, fixture or Postgres-backed. No blockers for T05 (subject-selector UI) or T06 (regression test).
