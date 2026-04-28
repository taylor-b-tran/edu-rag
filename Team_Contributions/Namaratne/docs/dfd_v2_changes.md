# DFD Level 1 v2 Changes Summary

Owner: Kahavidanage Namaratne  
Sprint: Sprint 3  
Artifact: `diagrams/dfd_level1_v2.png`

## Purpose

The DFD Level 1 v2 extends the Sprint 2 data-flow model with the error paths and runtime stores discovered during Sprint 3 PoC work. It keeps the RAG pipeline as the centre of the system while making upload failure, indexing failure, retrieval fallback, and LLM provider failure explicit.

## Updated Processes

| Process | Responsibility |
|---|---|
| P1 Web Application / API | Authenticates users, validates requests, routes uploads and queries, polls indexing jobs, and returns answers or status messages. |
| P2 Document Processor | Validates files, extracts PDF text with PyMuPDF, chunks text with the LangChain splitter, and manages async indexing work. |
| P3 Vector Retrieval | Embeds user queries, filters vectors by `course_id`, retrieves top-k chunks, and applies fallback threshold rules. |
| P4 LLM Response Generator | Builds grounded prompts, calls the selected local LLM, and returns answers with source citations. |
| P5 Logging and Monitoring | Records upload events, parsing failures, indexing failures, query/response events, fallback events, and rate-limit events. |

## Updated Data Stores

| Store | Purpose |
|---|---|
| D1 Raw Document Store | Stores uploaded course materials as files. |
| D2 ChromaDB | Stores chunk embeddings and vector metadata for retrieval. |
| D3 PostgreSQL | Stores users, courses, documents, indexing jobs, sessions, messages, refresh tokens, and audit logs. |

## Added Error Paths

| Error Path | Handling |
|---|---|
| Invalid file upload | API rejects the file, marks the document as rejected if a record exists, logs the validation failure, and returns a 400 response. |
| PyMuPDF extraction failure | Indexing job is marked failed with `error_message`; lecturer sees failure through polling; audit log stores the event. |
| ChromaDB indexing failure | Job retry count increases; system retries until the configured limit; final failure is logged and visible through job status. |
| Retrieval returns no relevant chunks | System returns the approved labelled fallback instead of generating an unsupported course answer. |
| LLM provider unavailable | Retrieval evidence is preserved for debugging, but the user receives a safe service-unavailable response. |
| Cross-course retrieval leakage risk | Retrieval must filter by `course_id`; any missing or mismatched filter is treated as a security/audit event. |

## Inclusion Note

For the consolidated Sprint 3 report, this diagram should be placed near the architecture/data-flow section. It supports the Assessment 2 design by showing that Sprint 3 implementation now considers operational failure paths, not only the happy path.
