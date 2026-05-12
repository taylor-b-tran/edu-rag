# Flask API Query Sequence

Project: EduRAG / Paedia
Sprint: Sprint 4
Source task: Task 19 - Flask API query sequence diagram
Diagram artifact: `docs/architecture/seq_api_query.png`

## Scope

This sequence diagram documents the implemented Sprint 4 Flask query route, not
the future live ChromaDB/Ollama retrieval path. The current route is useful for
Streamlit integration and API testing, but it still uses fixture-backed matching
through `APIState.query_fixture()`.

## Implemented Sprint 4 Flow

1. Streamlit sends `POST /api/query` with `query`, `course_id`, and optional
   `session_id`.
2. Flask applies the per-IP rate-limit check in `src/api/routes/query.py`.
3. Flask validates the bearer token through the in-memory `APIState`.
4. Flask checks that the user is enrolled in the requested course.
5. `APIState.query_fixture()` fuzzy-matches the question against
   `fixtures/sample_responses.json`.
6. `APIState.record_session_message()` stores the exchange in in-memory session
   state.
7. Flask returns a JSON response with `answer`, `source_references`,
   `fallback_used`, `confidence`, `session_id`, `backend_mode`, and
   `latency_ms`.

## Sprint 5 Gap

The target demo path should replace fixture matching with course-scoped ChromaDB
retrieval and live generation. Until that lands, diagrams that show PostgreSQL,
ChromaDB, and Ollama in the `/api/query` runtime path must be labelled as target
architecture rather than current Sprint 4 implementation.
