# T11/T12 — UI Polish for Tech Expo

Went through the live Streamlit UI end-to-end (login, chat, document manager,
session history) against the real Docker stack (not fixtures) to find rough
edges that would show during a live demo, then fixed the ones that actually
mattered.

## What was tested

Logged in as a lecturer, navigated all four pages, and ran a real query
("What is RAG?") through the full pipeline (ChromaDB retrieval + Ollama
generation) to see what a marker would actually see during a live demo.

## Issues found and fixed

### 1. The UI looked frozen during generation (real bug)

Asking a question left the "Welcome to Paedia" empty-state screen and
suggestion chips on screen, with the user's own question never shown, while a
single static "🧠 Generating response..." line sat there for however long
Ollama took — up to ~200s on CPU-only hardware per the T09/T25 benchmarks. To
anyone watching, this looks indistinguishable from a hung app.

Root cause (`apps/streamlit/main.py`): the chat page appended the user's
message and called the (blocking) generation function in the same script run
that rendered the empty-state block, so the empty state had already been
drawn before the question was even recorded.

Fix: split submission into two reruns. `_submit_query()` appends the user's
message and sets a `pending_send` flag, then reruns immediately — so the
question renders as a chat bubble right away. Generation happens on the next
rerun, with a clearer status message ("can take up to a couple of minutes on
CPU-only hardware") so it doesn't read as broken. Applied consistently to the
chat input and both suggestion-chip flows (welcome screen + follow-up chips),
which previously had no loading indicator at all.

### 2. Frontend query timeout was shorter than the backend's (real bug)

`apps/streamlit/api_client.py` defaulted `PAEDIA_QUERY_TIMEOUT` to 180s, but
`src/document_processor/rag_pipeline.py`'s own Ollama call timeout was raised
to 240s in T25. On slow hardware the Streamlit client gave up and showed a
generic timeout error *before* the backend's own graceful-fallback logic ever
got a chance to run. Confirmed live: a real query hit `Read timed out
(read timeout=180)` in the streamlit container logs.

Fix: bumped the default to 260s, comfortably above the backend's 240s ceiling.

### 3. Console warnings on every load (cosmetic)

`.streamlit/config.toml` had no `[theme.sidebar]` section, so the frontend
logged `Invalid color passed for widgetBackgroundColor/widgetBorderColor/
skeletonBackgroundColor in theme.sidebar: ""` on every page load. Added an
explicit `[theme.sidebar]` block matching the existing navy sidebar CSS.
Confirmed the warnings are gone and the sidebar looks identical.

## Verification

- Re-ran the full pytest suite after all changes: **118 passed**, no
  regressions.
- Re-tested the live query end-to-end after the fix: user's question now
  appears immediately as a chat bubble, the generating indicator is visible
  next to it, and the completed answer renders with citations, confidence
  bar, and model badge — all within the new timeout budget.
- Re-verified sidebar navigation (Q&A Chat / Session History / Document
  Manager) still works after the state changes.
- Screenshots of the before/after chat behaviour and all four pages
  (welcome state, live in-flight query, completed answer, Document Manager,
  Session History) were captured during this verification pass.

## Files changed

- `apps/streamlit/main.py` — deferred-generation fix (`_submit_query` /
  `pending_send`), reused previously-unused `pending_send`/`query_state`
  session-state keys that had been added but never wired up.
- `apps/streamlit/api_client.py` — `query_timeout` default 180s → 260s.
- `.streamlit/config.toml` — added `[theme.sidebar]`.
