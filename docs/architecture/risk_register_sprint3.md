# Risk Register - Sprint 3 Update

Owner: Kahavidanage Namaratne  
Sprint: Sprint 3  
Status: Ready for consolidated report inclusion

## Updated Risk Register

| ID | Risk | Likelihood | Impact | Status | Mitigation |
|---|---|---|---|---|---|
| R1 | Team skill gaps in RAG and LLM technologies | Low | Medium | Closed | Sprint 3 PoC demonstrated the core RAG path. Keep knowledge sharing through notebook walkthroughs and handoff notes. |
| R2 | Scope creep from extra product features | Medium | Medium | Ongoing | Prioritise the RAG pipeline, source citations, course isolation, and upload/query flows before optional UI polish. |
| R3 | High external API cost from hosted LLM usage | Medium | Medium | Ongoing | Use Ollama/local models during development and reserve paid API usage for controlled demo or fallback scenarios. |
| R4 | Hallucinated or inaccurate LLM responses | High | High | Ongoing | Use RAG grounding, source citations, similarity thresholds, fallback labels, and manual evaluation against labelled test queries. |
| R5 | Poor PDF/PPTX/DOCX parsing quality | High | High | New | Use PyMuPDF as the preferred PDF parser, compare PPTX/DOCX extraction separately, and preserve page/slide boundaries for citations. |
| R6 | Indexing job failure or incomplete processing | Medium | High | New | Track `indexing_jobs.job_status`, `attempt_count`, `progress_percent`, and `error_message`; expose status polling to lecturers. |
| R7 | ChromaDB and PostgreSQL metadata inconsistency | Medium | High | New | Store `course_id` and `document_id` in ChromaDB metadata, enforce document/course constraints in PostgreSQL, and log indexing results. |
| R8 | LLM provider unavailable or too slow | Medium | High | New | Provide safe service-unavailable messaging, keep retrieval evidence, and support configurable local model fallback. |
| R9 | Retrieval returns no relevant chunks | Medium | Medium | New | Apply the documented similarity threshold and return a labelled fallback rather than unsupported course-grounded answers. |
| R10 | Excessive queries or rate limiting gaps | Low | Medium | New | Add rate-limit middleware in the API layer and log rate-limit events for admin review. |
| R11 | Cross-course data leakage | Low | High | New | Require `course_id` filtering in vector retrieval and enforce RBAC checks before returning documents, sessions, or citations. |
| R12 | Large document storage and scaling pressure | Medium | Medium | New | Estimate storage early, monitor raw document and vector-store growth, and optimise chunking defaults before larger pilots. |

## Report-Ready Summary

Sprint 3 reduced the earlier team-skill risk by proving the RAG pipeline locally, but it also surfaced more concrete implementation risks. The highest priority risks are now parsing quality, hallucination control, indexing reliability, and cross-course data isolation. These are manageable if Sprint 4 keeps the current focus on grounded answers, course-scoped retrieval, job status tracking, and parser validation.
