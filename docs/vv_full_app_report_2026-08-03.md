# Full-App V&V Report — 3 Aug 2026

Scope: full application, not just the recent Sprint 6 changes — backend data
pipeline, RBAC/role UI, and regression safety.

## 1. Backend upload -> storage -> processing pipeline: VERIFIED END-TO-END

Ran a real upload against the live stack (not fixtures, not mocks):

1. `POST /api/upload` with a real 8.7MB PDF (`materials/book_embNLP_draft.pdf`) as
   lecturer — 202 queued, file written to `/workspace/data/uploads/`.
2. Background thread: parsed the PDF, chunked it, batch-encoded embeddings
   (T09 path), upserted into ChromaDB. **48.5s total** for 466 chunks.
3. Postgres (`uploaded_documents`, `indexing_jobs`) correctly transitioned
   `queued -> processing -> indexed`, chunk count (466) recorded.
4. Real query ("What is an embedding in NLP?") against the newly-indexed
   course retrieved the correct chunks (pages 2/15/16/80/120 of the uploaded
   PDF) and generated a grounded, cited answer — confirms retrieval and
   generation are both live, not fixture fallback.
5. `DELETE /api/document/<id>` correctly removed the Postgres row, the
   ChromaDB chunks, and the file from disk — verified all three directly,
   zero orphaned data left behind.

**Conclusion: the upload/storage/processing pipeline is fully wired and
working correctly**, including the failure path (see below) and cleanup path.

## 2. The 7 "unused" Postgres tables — confirmed, with two corrections

Re-verified the Sprint 6 finding (`docs/architecture/erd_reconciliation_sprint5.md`)
still holds, with a direct check of the live database:

```
\dt  ->  only uploaded_documents and indexing_jobs actually exist.
```

The other 7 tables from `db/migrations/001_initial_schema.sql`
(`users`, `courses`, `course_memberships`, `conversation_sessions`,
`conversation_messages`, `refresh_tokens`, `audit_logs`) were **never even
applied** to this database — not just unused, physically absent.

Two refinements to the earlier finding:
- **`refresh_tokens`**: there IS a working `/api/auth/refresh` endpoint — it's
  just backed by an in-memory dict (`APIState.refresh_tokens`), not the
  Postgres table. So refresh works functionally, just doesn't survive an API
  restart. Earlier note that "no refresh flow exists" was too strong.
- **`audit_logs`**: `/api/admin/audit-logs` and `/api/logs` exist as routes,
  but both are hardcoded stubs returning `{"logs": [], ...}` unconditionally.
  Confirmed not wired to anything — this part of the earlier finding holds.

This is a pre-existing Sprint 4/5 gap, not a Sprint 6 regression. No code
change made here — reporting only, per your call on scope.

## 3. UI role testing

### Lecturer (already covered under T11)
Document Manager, Session History, Q&A Chat all working — see
`docs/t11_t12_ui_polish.md`.

### Student — 1 real bug found and fixed
`My Uploads` rendered a fully functional upload dropzone identical to the
lecturer's, even though students are documented as read-only
(`docs/ui/ui_state.md` §3.1) and the backend correctly rejects student
uploads with 403. Confirmed live: student token -> `/api/upload` ->
`403 "Lecturer or admin role required."` The frontend handled the failure
gracefully (clear error message, no crash), but showing an upload control
that always fails is confusing and inconsistent with the read-only design.

**Fix:** `render_uploads_page()` now just shows the caption "Read-only — ask
your lecturer to add course materials." and the document table — no
uploader. Matches actual backend behaviour and the original design intent.

### Admin — 1 real bug found and fixed
The user-management table's per-row **Edit** and **Del** buttons were fully
clickable with no handler behind them at all — clicking silently did nothing
(not even a rerun visibly changes anything), which is worse than the
adjacent "Add User" button, which is correctly `disabled=True` with a
tooltip explaining it's not wired yet.

**Fix:** `Edit`/`Del` now `disabled=True` with the same "not yet wired"
tooltip pattern as `Add User`, for consistency.

Everything else on the Admin Dashboard (live stats card, backend mode,
Ollama warm-up status) is correctly live-wired to `/api/admin/stats` — not a
fixture, confirmed via the "Live from /api/admin/stats" caption and cross-
checked against real document/session counts.

## 4. Regression testing

- Full pytest suite re-run after all fixes (T09-T12 + the two RBAC/admin UI
  fixes above): **118 passed**, no regressions.
- Manually re-verified nav (Q&A Chat / Session History / Document
  Manager / Admin Dashboard) still works for all three roles after the
  state and page-rendering changes.

## 5. Known issue not fixed (flagging only)

`test/test_api.py::test_upload_queues_document_when_lecturer_authenticated`
writes a real file and triggers the real background indexing thread against
the **same shared Postgres database** the demo stack uses — it doesn't wait
for indexing to finish or clean up afterward. Found 6 leftover "demo.pdf"
rows (all correctly marked `failed`, since the test file isn't a real PDF —
this is fitz correctly rejecting fake content, not a pipeline bug). These
never surface in the running app's UI (the API container only hydrates its
in-memory document list once at startup) but do clutter the database if
anyone inspects it directly. Cleaned up the existing rows manually; didn't
change the test itself since it's out of scope for this pass and the test's
actual behaviour under test is correct.

## Files changed in this V&V pass

- `apps/streamlit/main.py` — `render_uploads_page()` simplified to read-only
  for students; admin `Edit`/`Del` buttons disabled with tooltips.
