# ERD v2 Changes Summary

Owner: Kahavidanage Namaratne  
Sprint: Sprint 3  
Artifact: `diagrams/erd_v2.png`

## Purpose

The ERD v2 was corrected to match the Sprint 3 PostgreSQL implementation rather than the earlier conceptual Sprint 2 model. The implemented schema lives in `db/migrations/001_initial_schema.sql`, so this version uses that file as the source of truth.

## Main Corrections

| Area | Original Issue | Corrected v2 Design |
|---|---|---|
| Role modeling | Role appeared as a separate entity. | Role is represented by `users.role` and `course_memberships.membership_role`, matching the SQL schema. |
| Course membership | Student and lecturer enrolment/ownership was not explicit enough. | Added `course_memberships` to represent user-course relationships and role within each course. |
| Conversation data | Query and Response appeared as separate entities. | Replaced them with `conversation_sessions` and `conversation_messages`, matching the implemented tables. |
| Refresh tokens | Authentication persistence was missing. | Added `refresh_tokens` because the Sprint 3 schema supports JWT refresh-token storage and revocation. |
| Audit logging | AuditLog existed but was not aligned to the implemented schema. | Updated audit logging to `audit_logs` with `event_type`, `event_level`, JSON payload, and optional user/course/session links. |
| Vector storage | Embedding/chunk storage risked looking relational. | ChromaDB is shown as an external vector store, linked by metadata such as `course_id`, `document_id`, `page_number`, and `chunk_index`. |
| Indexing jobs | Async ingestion was present but needed tighter schema alignment. | `indexing_jobs` now uses `job_status`, `progress_percent`, `attempt_count`, and `error_message` as implemented. |

## Final ERD Entities

The corrected ERD contains these PostgreSQL tables:

- `users`
- `courses`
- `course_memberships`
- `documents`
- `indexing_jobs`
- `conversation_sessions`
- `conversation_messages`
- `refresh_tokens`
- `audit_logs`

It also shows ChromaDB as an external vector store, not a PostgreSQL table.

## Key Relationships

| Relationship | Meaning |
|---|---|
| `users` -> `course_memberships` -> `courses` | A user can belong to multiple courses, with a course-specific role. |
| `courses` -> `documents` | Course materials are scoped to one course. |
| `documents` -> `indexing_jobs` | Uploaded documents create asynchronous processing jobs. |
| `documents` -> ChromaDB metadata | Extracted chunks and embeddings are stored in ChromaDB with document/course metadata. |
| `users` -> `conversation_sessions` -> `conversation_messages` | Student conversation history is stored as sessions and ordered messages. |
| `users` -> `refresh_tokens` | Login persistence and token revocation are stored relationally. |
| `audit_logs` -> optional user/course/session links | Operational events can be traced without blocking append-only logging. |

## Inclusion Note

For the Sprint 3 consolidated report, use the PNG diagram first, then summarise the correction as:

> The ERD v2 was updated to reflect the implemented Sprint 3 PostgreSQL schema and the hybrid storage model. PostgreSQL stores users, courses, memberships, documents, indexing jobs, conversations, refresh tokens, and audit logs, while ChromaDB stores chunk embeddings externally with metadata links back to course and document records.

## Sprint 4 Reconciliation Check

Sprint 4 Task 18 rechecked the ERD against `db/migrations/001_initial_schema.sql`
after the Flask API wrapper landed. The existing reconciled diagram remains the
correct baseline because it includes the implemented PostgreSQL tables,
UUID-style `id` keys, refresh-token storage, audit-log links, and ChromaDB as an
external vector store rather than a relational table.

The late local draft under `C:\studyAssets\CSIT321 - Project\andre` was reviewed
but should not replace the repository diagram. That draft simplifies keys to
generic `int`, omits `refresh_tokens`, uses older message/document field names,
and shows a target RAG sequence rather than the current fixture-backed Flask
route behaviour.

Current canonical artifacts:

- `docs/architecture/diagrams/erd_v2.png`
- `docs/architecture/erd_v2_changes.md`
- `docs/architecture/erd_v2.png` as a Sprint 4 plan-path compatibility copy
