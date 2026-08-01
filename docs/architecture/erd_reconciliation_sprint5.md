# ERD Reconciliation — Sprint 5 (as-designed vs. as-implemented)

Project: EduRAG / Paedia
Verified against code: 26 Jul 2026 (Sprint 6 T05 — architecture drift review)
Diagram artifact: `docs/architecture/diagrams/erd_reconciliation_sprint5.svg`

## Finding

`docs/architecture/erd_v2.png` (and `erd_v2_changes.md`, last reconciled at Sprint 4) documents the **formal migration schema** in `db/migrations/001_initial_schema.sql` — 9 UUID-keyed, foreign-key-constrained PostgreSQL tables. The System Design Document (`system_design_document_v2_source.md`, §11) states as fact: *"PostgreSQL stores users, roles, courses, memberships, documents, indexing jobs, sessions, messages, refresh tokens, and audit logs."*

**This is no longer accurate for the running Sprint 5 system.** Checking the actual runtime code:

- `src/api/state.py` reads users from `self.fixtures.get("demo_users", [])` — **fixture-backed**, not the `users` table.
- There is no code anywhere in `src/api/` that queries `courses`, `course_memberships`, `conversation_sessions`, `conversation_messages`, `refresh_tokens`, or `audit_logs`. These 6 tables are defined in the migration file but **appear to be unused dead schema** at runtime.
- The only real, live Postgres usage is `src/api/db.py`, added in Sprint 5 for QA-DATA-001 (upload/indexing persistence). It defines its **own schema**, independent of the migration file:
  - `uploaded_documents` (TEXT primary key `document_id`, loosely-typed `course_id`/`course_code`/`course_uuid`, no foreign keys) — **not the same table** as the migration's `documents` (UUID PK, FK to `courses.id`, `stored_path`, `mime_type`, `sha256_checksum`).
  - `indexing_jobs` (TEXT PK `job_id`, FK to `uploaded_documents`, columns `status`/`error`) — **similar in purpose but different in shape** from the migration's `indexing_jobs` (UUID PK, `job_status`/`error_message`/`attempt_count`, FK to both `documents` and `courses`).

In short: **2 of the 9 designed tables have a real (but redesigned) runtime equivalent; the other 7 exist only in the migration file and are not queried by any current code path.**

## As-Designed vs. As-Implemented

| Table (as designed, migration) | Real at runtime? | Actual persistence |
|---|---|---|
| `users` | No | Fixture (`fixtures/sample_responses.json::demo_users`) |
| `courses` | No | Fixture / hardcoded course list |
| `course_memberships` | No | Fixture (`enrolled_courses` on the fixture user record) |
| `documents` | **Redesigned** | `uploaded_documents` (`src/api/db.py`) — different schema, same purpose |
| `indexing_jobs` | **Redesigned** | `indexing_jobs` (`src/api/db.py`) — different columns, same purpose |
| `conversation_sessions` | No | In-memory (`APIState.record_session_message()`) |
| `conversation_messages` | No | In-memory, part of the same session dict |
| `refresh_tokens` | No | Not implemented — no refresh-token flow found in the API routes |
| `audit_logs` | No | Not implemented — no audit-log writes found |

## Why this matters for A4

The A4 Requirements Traceability Matrix (`docs/rtm_a4.md`) already marks several related items honestly (NFR-002 course isolation via ChromaDB metadata rather than the relational schema; FR-024 audit log review as "Partial"). This reconciliation makes the underlying reason explicit: **the formal relational design was never fully wired up — only the upload/indexing slice was, and via a simpler, purpose-built schema rather than the originally designed one.**

This is not a Sprint 6 regression — it has been true since at least Sprint 4/5. It was simply never reflected back into the ERD or System Design Document. Flagging and correcting it now is itself a legitimate piece of Sprint 6/A4 "actual work," separate from the still-pending T07 (model fine-tuning) and T09 (vector DB optimisation) technical tasks.

## Recommendation (not yet actioned — flag for team decision)

Pick one before the report is finalised:
1. **Update the ERD** to show only the 2 real tables (`uploaded_documents`, `indexing_jobs`) as implemented, and mark the other 7 as "designed, not yet wired" — most honest, smallest change.
2. **Actually wire up** `users`/`courses`/`conversation_sessions` to Postgres in a later sprint, making the original ERD accurate again — larger effort, out of scope for the current 2-week A4 window.

Either is defensible for A4 as long as the report doesn't repeat the unqualified claim in System Design Document §11.
