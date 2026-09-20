# Task 13 — Dynamic Content Rendering Audit

**File:** `apps/streamlit/main.py` (rev `963e28a`)
**Auditor:** Anmoldeep Singh (8443580) · Group 19 Aletheia's Zetetes
**Date:** 2026-09-20

## Method

Every call to `st.markdown(..., unsafe_allow_html=True)` was identified
(30 occurrences). For each, the content inserted was classified by origin:

| Origin | Risk | Count |
|--------|------|-------|
| Fixed text / CSS / layout | None | 14 |
| Client-generated (timestamps, counts, computed values) | None | 3 |
| API data — already escaped before insertion | Safe | 6 |
| API data — **now escaped** by this audit | **Fixed** | 7 |

---

## Findings — sites that were unescaped (now fixed)

Each "untrusted" value originates from the Flask API, which returns
data stored in PostgreSQL or produced by the LLM. A lecturer or
document author who controls these values could inject HTML/JS into
another user's browser session via Streamlit's `unsafe_allow_html`.

All findings below have been fixed by wrapping the value in
`_html.escape()` (Python's `html.escape`).

### Finding 1 — Session title in sidebar (line 1049)

```python
# BEFORE
title = s["title"][:30] + ("..." if len(s["title"]) > 30 else "")
# AFTER
title = _html.escape(s["title"][:30] + ("..." if len(s["title"]) > 30 else ""))
```
**Source:** `session["title"]` — derived from the first user message, stored
in and returned from the API. A crafted message like
`<img src=x onerror=alert(1)>` would render as HTML.
Also escaped: `s.get('created_at', '')` on line 1054.

### Finding 2 — Document name in sidebar (line 1078)

```python
# BEFORE
doc_name = doc.get("original_filename") or doc.get("filename") or doc.get("name") or "Unknown"
# AFTER
doc_name = _html.escape(doc.get("original_filename") or ...)
```
**Source:** `original_filename` — the name the lecturer gave the uploaded
file. A file named `<script>alert(1)</script>.pdf` would inject.

### Finding 3 — User initials in sidebar (line 1114)

```python
# BEFORE
initials = "".join(w[0] for w in st.session_state.user.get("name", "U").split()[:2])
# AFTER
initials = _html.escape("".join(...))
```
**Source:** `user["name"]` from the API. At most 2 characters after the
split, but those characters could be `<` and `>`. Low practical risk
but should still be escaped for correctness.

### Finding 4 — Session history cards (lines 1556-1560)

```python
# BEFORE
title = session.get("title", "Untitled")
course = session.get("course_id", "CSIT214")
created = session.get("created_at", "—")
preview = session.get("preview", ...)
# AFTER — all four escaped
title = _html.escape(session.get("title", "Untitled"))
course = _html.escape(session.get("course_id", "CSIT214"))
created = _html.escape(session.get("created_at", "—"))
preview = _html.escape(session.get("preview", ...))
```
**Source:** `title` (user message), `course` (course_id from API),
`preview` (message content). `title` and `preview` carry user/LLM
content — same risk as Finding 1.

### Finding 5 — Document table rows (line 1860)

```python
# BEFORE — doc_type inserted raw into <span>
cols[1].markdown(f"<span ...>{doc_type}</span>", unsafe_allow_html=True)
# AFTER — escaped after MIME-type processing, before insertion
doc_type = _html.escape(doc_type)
```
**Source:** `doc_type` derived from `original_filename` extension or
`file_type` field. `doc_name` on line 1870 uses `st.markdown` *without*
`unsafe_allow_html`, so Streamlit strips HTML there — no issue.

### Finding 6 — Upload progress (line 1759)

```python
# BEFORE
f'<strong>{filename}</strong> ({file_size / 1024:.1f} KB)<br>'
# AFTER
f'<strong>{_html.escape(filename)}</strong> ({file_size / 1024:.1f} KB)<br>'
```
**Source:** `filename` is `uploaded_file.name` — chosen by the user
uploading. `msg` comes from a fixed `stages` dict (safe).

### Finding 7 — Course cards (lines 2368-2370, 2442-2444)

```python
# BEFORE — in both enrolled-courses and available-courses blocks
f"...{code}</span><br/>"
f"...{course.get('name', '')}</span><br/>"
f"...{course.get('description', '') or 'No description.'}</span>"
# AFTER — all three escaped in both blocks
f"...{_html.escape(code)}</span><br/>"
f"...{_html.escape(course.get('name', ''))}</span><br/>"
f"...{_html.escape(course.get('description', '') or 'No description.')}</span>"
```
**Source:** `code`, `name`, `description` all come from the courses API.
An admin creates courses; the name and description are free-text.

---

## Sites that ARE properly escaped (pre-existing, confirmed safe)

| Line | Content | Escaped by |
|------|---------|------------|
| 809 | `model_used` (LLM model name) | `_html.escape()` in `get_model_badge()` |
| 1356 | User message content | `_html.escape()` |
| 1367 | Error message | `_html.escape()` |
| 1387 | AI answer text | `_html.escape()` + `\n→<br>` |
| 1407-1414 | Source filenames, pages, sections, collections | `_html.escape()` each |
| 1875 | `status_note` in document table | `_html.escape()` |

These are the highest-risk values (LLM output, user messages,
document metadata) and they were all correctly escaped before this audit.

---

## Sites that are fixed text / layout only (no risk)

Line 386 (CSS block), 943, 945, 1325, 1340, 1474, 1484, 1505,
1642, 1664, 1850, 1851, 2135, 2228, 2575.

---

## Summary

**7 genuine findings** where API-sourced data reached `unsafe_allow_html`
without `_html.escape()`. All 7 have been fixed. The highest-risk values
(user messages, LLM answers, source citations) were already escaped
before this audit. The fixed sites involve session titles, document
filenames, course metadata, and user initials — lower risk because they
require a lecturer or admin account to exploit, but they should still
be escaped for defence-in-depth.

**Total `_html.escape()` calls after fix:** 26 (10 pre-existing + 16 new).
