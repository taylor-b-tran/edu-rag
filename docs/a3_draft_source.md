# Assessment 3 Draft Source

Project: EduRAG / Paedia
Group: Group 19, CSIT321 Project 37
Draft status: Sprint 4 first draft
Prepared for: Task 23 - A3 document first draft
Date: 12 May 2026

## 1. Design Methodology

Paedia is being developed through an iterative, evidence-driven design process.
The team began with a modular architecture proposal in Assessment 2, then used
Sprint 3 and Sprint 4 to turn the design into a working prototype path. The
implementation approach is deliberately incremental: first validate the RAG
pipeline and system interfaces in a controlled environment, then connect the
Streamlit interface to a Flask API, and finally replace fixture responses with
seeded live retrieval for the final demonstration.

The design process follows three practical principles.

First, user roles shape the interface and API. Students need a low-friction
question-answer flow with citations, lecturers need upload and indexing status
feedback, and admins need visibility into usage, failures, and audit events.
This role separation appears in the Flask API, the Streamlit navigation model,
and the PostgreSQL schema through users, course memberships, documents,
sessions, messages, and audit logs.

Second, answers must be grounded in course material rather than treated as
general AI output. The RAG configuration keeps course isolation as a core
constraint: retrieved chunks must be filtered by `course_id`, unsupported
questions should return a clear fallback, and source references must be visible
to the student. The current Sprint 4 API still uses fixture-backed responses,
so the Sprint 5 plan separates fixture-mode evidence from live ChromaDB
retrieval evidence.

Third, the team keeps documentation aligned with implementation. Sprint 4
closed several design-code gaps by adding the Flask API wrapper, updating API
validation notes, regenerating 31-query benchmark evidence, and recording
demo-readiness risks. This draft treats those artifacts as the source of truth
instead of relying on older conceptual diagrams.

## 2. Requirements Covered by the Prototype

The Sprint 4 prototype covers the core demonstration path for Assessment 3.
The implemented Flask API exposes authentication, course-scoped querying,
document upload, indexing job status, document listing, session history, health
checks, and admin compatibility routes. The Streamlit UI can communicate with
that API through `apps/streamlit/api_client.py`, while retaining a fixture mode
for safe demos when the backend is unavailable.

The main functional requirements currently represented are:

- Student login and protected API access through bearer-token style
  authentication.
- Course-scoped query submission through `POST /api/query`.
- Source-reference display in the API response and Streamlit answer flow.
- Fallback labelling for off-topic or unsupported questions.
- Lecturer document upload through `POST /api/upload`.
- Indexing job polling through `/api/indexing-jobs/{job_id}`.
- Session list and session detail routes for conversation history.
- Admin statistics and audit-log compatibility routes.

The key non-functional requirements are also visible in the prototype evidence:

- Course isolation: users are checked against enrolled courses before query
  execution.
- Reliability: fixture fallback and labelled fallback responses prevent the UI
  from failing silently during demos.
- Maintainability: Flask routes are separated into modules under
  `src/api/routes/`.
- Testability: the API and document-processing paths are covered by the pytest
  suite, and the 31-query benchmark corpus is stored as repeatable evidence.
- Deployability: Docker Compose provides the local infrastructure baseline,
  and Sprint 5 begins with GitHub Actions validation for Python tests and
  Docker demo readiness.

The prototype is not yet a production deployment. The current query route is
fixture-backed, not a live ChromaDB plus Ollama generation path. Assessment 3
should state this boundary clearly and show the Sprint 5 plan for moving from
fixture-mode integration to seeded live retrieval.

## 3. Interface Section Draft

The Paedia interface is designed around a student-first question-answer flow.
After login, the student selects or inherits a course context, enters a
natural-language question, and receives an answer with source references and a
confidence/fallback indicator. The visual style uses the locked Paedia design
system so that chat messages, source chips, upload status badges, and navigation
states remain consistent across the prototype.

The lecturer view focuses on document operations. A lecturer can upload
supported files, see whether a document is queued or indexed, and confirm that
course materials are available for retrieval. This keeps document ingestion
visible instead of hiding processing failures behind the chat interface.

The admin and monitoring view supports the project requirement for auditability.
It provides summary metrics and audit-log style events so that the team can
discuss usage monitoring, failures, and responsible AI controls during the
presentation.

The Assessment 3 interface evidence should include six annotated screenshots:

1. Login and role selection.
2. Student chat with a grounded answer and visible source references.
3. Student fallback response for an off-topic question.
4. Lecturer document upload and indexing status.
5. Session history or saved conversation view.
6. Admin/monitoring dashboard.

As of this draft, the screenshot folder is still pending. The screenshots
should be captured from the connected Streamlit and Flask path where possible,
and any fixture-backed screen must be labelled honestly in the caption.

## 4. Evidence to Reference

The final Assessment 3 document should reference:

- `src/api/app.py` and `src/api/routes/` for the Flask API wrapper.
- `apps/streamlit/main.py` and `apps/streamlit/api_client.py` for UI/API
  integration.
- `docs/api/api_spec.yaml` and `docs/api/api_spec_validation.md` for API
  contract evidence.
- `docs/rag_config.md` and `docs/rag_config_benchmark_31q.json` for benchmark
  evidence.
- `docs/risk_register.md` for Sprint 4 and Sprint 5 risks.
- `docs/sprint_5_kickoff.md` for CI/CD and Docker demo-readiness planning.

## 5. Draft Boundary

This is a first draft, not the final Assessment 3 submission document. The
final version still needs live screenshots, final demo results, and the video
recording reference after the team completes the Sprint 5 demo rehearsal.
