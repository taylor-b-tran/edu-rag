# API Specification Validation Notes

Owner: Tai Huynh  
Sprint: Sprint 3  
Task: 26 - API specification draft  
Primary artifact: `api_spec.yaml`

## Scope Covered

This API specification focuses only on Task 26. It documents Module 4 Web Application endpoints using OpenAPI 3.0.3.

Covered endpoint groups:

- Authentication: login, logout, refresh
- Query: course-scoped RAG question endpoint
- Documents: upload, list, metadata, delete
- Indexing: upload status polling
- Sessions: list session history and retrieve/archive one session
- Admin: statistics and audit logs
- Health: local runtime health check

## Alignment With Sprint 2 Module 4

The Sprint 2 Module Interface document named these core endpoints:

- `POST /api/query`
- `POST /api/upload`
- `DELETE /api/document/{doc_id}`

The final Task 26 spec keeps those route names and adds supporting endpoints needed for Sprint 3 auth, async indexing, sessions, and admin monitoring.

## Quality Improvements Over Original Draft

| Area | Improvement |
|---|---|
| Route naming | Replaced `/ask` and `/documents` upload-only style with Module 4-aligned `/api/query`, `/api/upload`, and `/api/document/{doc_id}`. |
| Security | Added JWT bearer security and explicit unauthenticated public endpoints. |
| Role expectations | Endpoint descriptions identify Student, Lecturer, and Admin responsibilities. |
| Schemas | Added reusable request and response schemas for auth, query, upload, indexing jobs, sessions, admin stats, audit logs, health, and errors. |
| Error handling | Added reusable `400`, `401`, `403`, `404`, `422`, and `500` response definitions. |
| Async indexing | Added `GET /api/indexing-jobs/{job_id}` so upload can return `202 Accepted` while indexing continues. |
| RAG-specific response | Query responses now include `sources`, `fallback_used`, `confidence_label`, and `model_used`. |

## Local Validation Checklist

- YAML parses successfully with PyYAML.
- OpenAPI version is `3.0.3`.
- All internal `$ref` values resolve to local `components`.
- All operations include `operationId`.
- All protected endpoints inherit bearer auth.
- All main success responses include response schemas.

## Swagger Editor Handoff

The file is ready to paste into Swagger Editor for visual inspection. If Swagger Editor flags style warnings, they should be minor because the YAML uses valid OpenAPI 3.0.3 structure and local component references.
