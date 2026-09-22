# Task 12 — Live Technical Walkthrough (3 minutes)

**Presenter:** Anmoldeep Singh (8443580)
**Revision:** `963e28a` (develop)
**Rule:** Show actual files at this revision. One test. No credentials on screen.

---

## Opening (0:00 – 0:20)

> "I'll trace a single student query from the Streamlit interface all the way
> through enrollment check, retrieval, answer generation, citation rendering,
> and session persistence — six stops in the pipeline."

**Show:** the running app — a student logged in, CSIT321 selected,
chat page visible.

---

## Stop 1 — Interface: user submits a query (0:20 – 0:50)

**File:** `apps/streamlit/main.py`, line 1156 — `_send_message()`

> "When the student types a question and hits Enter, Streamlit calls
> `_send_message()`. It appends the user message to `session_state.messages`,
> then calls `get_ai_response(text)`, which delegates to the API client."

**File:** `apps/streamlit/api_client.py`, line 314 — `query()`

> "The API client builds a JSON payload — `query`, `course_id`, `session_id`,
> and optionally `response_style` — and POSTs it to `/api/query` on the
> Flask backend."

---

## Stop 2 — Enrollment check (0:50 – 1:10)

**File:** `src/api/routes/query.py`, line 107 — `query()`

> "The Flask route first validates the JWT bearer token (line 114), then
> rate-limits at 10 req/min per user (line 119). At line 171 it calls
> `state.is_enrolled(user, course_id)` — if the student isn't enrolled in
> CSIT321, a 403 is returned immediately. No retrieval, no model call."

---

## Stop 3 — Retrieval (1:10 – 1:40)

**File:** `src/document_processor/rag_pipeline.py`, line 527 — `generate()`

> "Once enrolled, the route calls `state.get_generator().generate()`. The
> pipeline first resolves the query for retrieval — if there's conversation
> history it rewrites the question to be self-contained (line 538).
>
> Then it calls `self._retriever.search(search_query, course_id=course_id,
> top_k=top_k)` (line 539). This hits ChromaDB, which stores 384-dimensional
> vectors from `all-MiniLM-L6-v2` in a single collection called
> `edurag_course`, scoped by a `where={"course_id": {"$eq": course_id}}`
> metadata filter (line 270). Only chunks with similarity above the
> threshold are kept (line 541). If nothing passes the threshold, the
> response is marked as a fallback."

---

## Stop 4 — Answer generation (1:40 – 2:10)

> "The pipeline builds a prompt from the retrieved chunks plus conversation
> history (line 543), then calls Ollama — or OpenAI for the demo endpoint.
> The raw response goes through citation cleanup: invalid markers are
> stripped, and only sources the model actually cited are kept in the
> final list (lines 554-556). Citation markers are renumbered to match
> the de-duplicated source list (line 562)."

---

## Stop 5 — Citation rendering + XSS protection (2:10 – 2:35)

**File:** `apps/streamlit/main.py`, line 1387

> "Back in the frontend, the answer text is escaped with `_html.escape()`
> before any HTML is added — this prevents injection from document content
> or model output. Bold and code formatting is re-applied with regex after
> escaping (lines 1388-1389).
>
> Source references are rendered as numbered chips (lines 1403-1422). Each
> filename, page number, section, and collection name is individually
> escaped with `_html.escape()` before insertion into the HTML template."

---

## Stop 6 — Session save (2:35 – 2:50)

**File:** `src/api/routes/query.py`, line 246

> "Before the response is returned, `state.record_session_message()` persists
> the question-answer pair with the session ID. If this is the first message,
> a new session is created; the session ID comes back in the response so the
> client can send follow-ups to the same conversation."

**File:** `apps/streamlit/main.py`, line 1174

> "The client stores the `backend_session_id` in `session_state` so the next
> question in this chat goes to the same server-side session."

---

## Test demo (2:50 – 3:00)

**Run:** `python -m pytest test/test_xss_escaping.py -v --tb=short`

> "This test suite injects `<img src=x onerror=alert(1)>` into every
> value that reaches `unsafe_allow_html` and verifies the escaped form
> appears — 16 tests, all green."

---

## Summary slide (if time)

| Stop | File | Key line |
|------|------|----------|
| 1. Interface | `main.py` | `_send_message()` L1156 |
| 2. Auth + enrol | `query.py` | `is_enrolled()` L171 |
| 3. Retrieval | `rag_pipeline.py` | `_retriever.search()` L539 |
| 4. Generation | `rag_pipeline.py` | `_call_ollama()` L544 |
| 5. Citations + XSS | `main.py` | `_html.escape()` L1387 |
| 6. Session save | `query.py` | `record_session_message()` L246 |
