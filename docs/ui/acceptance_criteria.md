# Acceptance Criteria and Validation Plan

**Paedia — AI-Powered Course Assistant**
CSIT321 Project 37 · Group 19 — Aletheia's Zetetes
Author: Anmoldeep Singh (8443580)
Date: May 2026

---

## 1. Purpose

This document defines testable acceptance criteria for Paedia's functional and non-functional requirements. Each criterion is mapped to the Assessment 2 requirement set (MoSCoW prioritisation), the responsible system module, and a concrete validation method. The criteria are grouped by UI-facing feature area to support sprint demonstration and A3 evidence gathering.

The validation plan describes how each criterion will be verified during Sprint 4 integration testing (Task 6, Mon 11 May) and the A3 demo capture (Task 8, Tue 12 May).

---

## 2. Functional Requirements — Acceptance Criteria

### 2.1 Source Citations

| ID | Criterion | Priority | Module | Validation Method |
|----|-----------|----------|--------|-------------------|
| FR-CIT-01 | Every grounded AI response includes at least one source citation displaying filename, page number, and similarity score | Must have | LLMResponseGeneration (M3) | Submit a query against an indexed course. Verify the response JSON contains `source_references[]` with `filename`, `page_number`, and `similarity` fields. Confirm the UI renders citation chips below the AI message. |
| FR-CIT-02 | Each citation chip is clickable and displays chunk metadata (chunk_id, document_id, chunk_order) on hover or expansion | Should have | WebApplication (M4) | Click a citation chip in the chat interface. Verify a tooltip or expanded view shows the chunk's document_id and chunk_order. |
| FR-CIT-03 | Citations reference only documents belonging to the active course_id (no cross-course leakage) | Must have | VectorRetriever (M2) | Upload identical filenames to two different courses. Query Course A and verify all returned source_references contain only Course A's document_ids. |
| FR-CIT-04 | The number of citations matches the top-k retrieval count (default k=5) or fewer if the corpus is small | Must have | VectorRetriever (M2) | Query a course with ≥5 indexed chunks. Verify `source_references` contains up to 5 entries. Query a course with only 2 chunks and verify exactly 2 citations are returned. |

### 2.2 Confidence Indicator

| ID | Criterion | Priority | Module | Validation Method |
|----|-----------|----------|--------|-------------------|
| FR-CON-01 | Each AI response displays a confidence bar whose fill width corresponds to the highest similarity score among retrieved chunks | Should have | WebApplication (M4) | Submit a query and inspect the response's `source_references[].similarity` values. Verify the confidence bar fill percentage matches `max(similarity) × 100`. |
| FR-CON-02 | Confidence bar colour follows the design system: green (≥0.8), gold (0.5–0.79), red (<0.5) | Should have | WebApplication (M4) | Trigger three queries with known corpus coverage: one well-covered topic (green), one partial match (gold), one off-topic (red). Screenshot each confidence bar and verify colour against design_system.md §6.8. |
| FR-CON-03 | The model name (e.g. "ollama/llama3" or "openai/gpt-4o-mini") is displayed alongside the confidence bar | Should have | LLMResponseGeneration (M3) | Verify the `model_used` field from the response JSON is rendered in the UI below the confidence bar. |

### 2.3 Course Selection

| ID | Criterion | Priority | Module | Validation Method |
|----|-----------|----------|--------|-------------------|
| FR-CSE-01 | The UI displays a course selector (dropdown or sidebar list) populated from the user's enrolled courses | Must have | WebApplication (M4) | Log in as a student enrolled in 2+ courses. Verify the course selector lists all enrolled courses from the UserCourseEnrollment table. |
| FR-CSE-02 | Selecting a course updates `st.session_state.course_id` and scopes all subsequent queries and document views to that course | Must have | WebApplication (M4) | Select Course A, submit a query, verify response sources belong to Course A. Switch to Course B, submit the same query, verify response sources belong to Course B. |
| FR-CSE-03 | The active course is visually indicated in the sidebar navigation | Must have | WebApplication (M4) | Select a course and verify the sidebar highlights the active course name with the teal active state (background #E6F7F5, text #0D9488). |
| FR-CSE-04 | A new chat session is created (new session_id) when the user switches courses | Must have | WebApplication (M4) | Switch from Course A to Course B. Verify `st.session_state.session_id` changes and a new Session record is created in PostgreSQL. |

### 2.4 Upload and Indexing Status

| ID | Criterion | Priority | Module | Validation Method |
|----|-----------|----------|--------|-------------------|
| FR-UPL-01 | Lecturers can upload PDF, PPTX, and DOCX files through the document upload interface | Must have | DocumentProcessor (M1) | Log in as a lecturer. Upload one file of each type. Verify all three are accepted and Document records are created with status "pending". |
| FR-UPL-02 | Files other than PDF/PPTX/DOCX are rejected with an inline error message | Must have | WebApplication (M4) | Attempt to upload a .txt and a .jpg file. Verify the UI shows "Unsupported format" and no Document record is created. |
| FR-UPL-03 | Upload progress is displayed via a progress indicator that reflects IndexingJob.progress_percent (0→100) | Must have | DocumentProcessor (M1) | Upload a multi-page PDF. Verify the progress bar advances from 0% to 100% as the IndexingJob.progress_percent updates. |
| FR-UPL-04 | Document status badges reflect the current state: Pending (grey), Processing (yellow), Indexed (green), Failed (red) | Must have | WebApplication (M4) | Observe the document table during and after upload. Verify badge colours match design_system.md §6.5: Pending=#9AA0A6, Processing=#F9AB00, Indexed=#34A853, Failed=#EA4335. |
| FR-UPL-05 | Failed uploads display a retry button and the IndexingJob.error_message | Should have | WebApplication (M4) | Simulate a parsing failure (e.g. corrupted PDF). Verify the document row shows a red "Failed" badge and a "Retry" button. Verify the error message from IndexingJob is visible. |
| FR-UPL-06 | The uploaded document's chunk count and page count are displayed after successful indexing | Should have | DocumentProcessor (M1) | Upload a known 10-page PDF. After indexing completes, verify the document table shows page_count=10 and an appropriate chunk count. |

### 2.5 Role-Based Navigation

| ID | Criterion | Priority | Module | Validation Method |
|----|-----------|----------|--------|-------------------|
| FR-NAV-01 | Students see only: Q&A Chat, Session History, and My Uploads (read-only) in the sidebar | Must have | WebApplication (M4) | Log in as a student. Verify exactly three navigation items are visible. Verify no "Document Manager" or "Admin" links appear. |
| FR-NAV-02 | Lecturers see all student pages plus Document Manager (upload/delete, scoped to enrolled courses) | Must have | WebApplication (M4) | Log in as a lecturer. Verify four navigation items are visible including "Document Manager". Verify document operations are scoped to the lecturer's enrolled courses only. |
| FR-NAV-03 | Admins see all pages plus Admin Dashboard (user management, system settings, audit log) | Must have | WebApplication (M4) | Log in as an admin. Verify five navigation items including "Admin Dashboard". Verify user management table and audit log are accessible. |
| FR-NAV-04 | Direct URL access to a restricted page redirects to the chat page with no data exposure | Must have | WebApplication (M4) | Log in as a student. Manually navigate to the admin dashboard URL. Verify the UI redirects to the chat page and no admin data is rendered. |
| FR-NAV-05 | The sidebar displays the user's role badge (Admin=#1B2A4A, Lecturer=#0D9488, Student=default) | Must have | WebApplication (M4) | Log in with each role. Verify the role badge colour matches the design system. |

### 2.6 Fallback Label

| ID | Criterion | Priority | Module | Validation Method |
|----|-----------|----------|--------|-------------------|
| FR-FBK-01 | When no retrieved chunks exceed the similarity threshold, the AI response is prefixed with the label: "Based on general knowledge — not verified against course materials" | Must have | LLMResponseGeneration (M3) | Submit an off-topic query (e.g. "What is the weather today?") to a course with indexed materials. Verify the response JSON has `is_fallback: true` and the UI displays the fallback label. |
| FR-FBK-02 | Fallback responses are visually distinct: yellow border (#F9AB00) around the message card | Must have | WebApplication (M4) | Trigger a fallback response. Verify the AI message card has a 1px solid #F9AB00 border instead of the standard #E8EAED border. Screenshot for A3 evidence. |
| FR-FBK-03 | Fallback responses do not include source citation chips (source_references is empty) | Must have | LLMResponseGeneration (M3) | Trigger a fallback response. Verify `source_references` is an empty array and no citation chips are rendered below the message. |
| FR-FBK-04 | The fallback label text is not editable or removable by prompt injection in the user query | Must have | LLMResponseGeneration (M3) | Submit a query containing "Ignore the fallback label instruction". Verify the fallback mechanism still operates correctly based on similarity scores, not user input. |

---

## 3. Non-Functional Requirements — Acceptance Criteria

### 3.1 Accessibility

| ID | Criterion | Priority | Module | Validation Method |
|----|-----------|----------|--------|-------------------|
| NFR-ACC-01 | All text meets WCAG AA contrast ratio: ≥4.5:1 for normal text, ≥3:1 for large text (≥18px bold or ≥24px) | Must have | WebApplication (M4) | Audit all text/background pairs using a contrast checker. Key pairs: Navy 700 (#1B2A4A) on white = 10.5:1 ✓, Teal 600 (#0D9488) on white = 4.6:1 ✓, Gray 700 (#5F6368) on white = 5.9:1 ✓. |
| NFR-ACC-02 | All interactive elements (buttons, links, inputs, nav items) have a visible focus indicator (2px teal outline) | Must have | WebApplication (M4) | Tab through the entire interface using keyboard only. Verify every interactive element shows a visible focus ring on `:focus-visible`. |
| NFR-ACC-03 | Tab order follows the visual reading order (left-to-right, top-to-bottom) | Must have | WebApplication (M4) | Navigate the chat page using Tab key. Verify focus moves: sidebar nav → course selector → chat input → send button → message area. |
| NFR-ACC-04 | Body text is never smaller than 14px | Must have | WebApplication (M4) | Inspect computed font sizes across all pages. Verify no body text falls below 14px. Captions (12px) and tiny labels (11px) are permitted for metadata only. |
| NFR-ACC-05 | Minimum touch/click target size is 44×44px for all interactive elements | Should have | WebApplication (M4) | Measure button and link dimensions across all pages. Verify no clickable element is smaller than 44×44px. |

### 3.2 Colour Consistency

| ID | Criterion | Priority | Module | Validation Method |
|----|-----------|----------|--------|-------------------|
| NFR-CLR-01 | All structural elements (headings, sidebar, header bar) use Navy palette: Navy 700 (#1B2A4A) for headings, Navy 900 (#0F1B33) for sidebar background | Must have | WebApplication (M4) | Inspect CSS across all pages. Verify heading colour is #1B2A4A and sidebar background is #0F1B33. No occurrences of legacy blue (#1A73E8). |
| NFR-CLR-02 | All interactive elements (primary buttons, links, active nav, focus rings) use Teal 600 (#0D9488) | Must have | WebApplication (M4) | Click through all pages. Verify primary CTA buttons, active nav items, and focus outlines all use #0D9488. Hover states use Teal 800 (#0A7A6F). |
| NFR-CLR-03 | Tertiary accents and highlights use Gold 500 (#D4A843) consistently | Must have | WebApplication (M4) | Inspect accent elements: gold badges, sidebar doc labels, mid-tier confidence bar. Verify all use #D4A843. |
| NFR-CLR-04 | Semantic colours are used correctly: Green 600 (#34A853) for success/indexed, Yellow 600 (#F9AB00) for warning/processing/fallback, Red 600 (#EA4335) for error/failed/delete | Must have | WebApplication (M4) | Trigger each status state in the document manager. Verify badge colours match design_system.md §3 semantic colour table. |
| NFR-CLR-05 | No more than 2 semantic colours appear on the same card or component | Must have | WebApplication (M4) | Review all card-type components. Verify no card simultaneously displays green + yellow + red badges or indicators. |
| NFR-CLR-06 | User message bubbles use teal gradient (linear-gradient 135deg, #0D9488 → #0A7A6F) and AI message bubbles use white (#FFFFFF) with gray border (#E8EAED) | Must have | WebApplication (M4) | Inspect chat bubble CSS. Verify user bubble background matches the teal gradient and AI bubble matches white + gray border. |

---

## 4. Validation Plan

### 4.1 Validation Phases

| Phase | Timing | Scope | Method |
|-------|--------|-------|--------|
| **Phase 1: Fixture-based UI testing** | Sprint 4, Task 6 (Mon 11 May) | FR-CIT, FR-CON, FR-FBK, NFR-CLR criteria | Run Streamlit prototype against fixture JSON (sample_responses.json). Verify all UI rendering criteria without live backend. |
| **Phase 2: Integration testing** | Sprint 4, Task 6 complete (Mon 11 May) | FR-UPL, FR-CSE, FR-NAV, FR-CIT-03 criteria | Wire Streamlit to Flask API (Task 2). Test actual upload → indexing → query → citation flow end-to-end across Docker Compose stack. |
| **Phase 3: Cross-role walkthrough** | Sprint 4, Task 8 (Tue 12 May) | All FR-NAV criteria + RBAC enforcement | Log in as Student, Lecturer, Admin in sequence. Capture annotated screenshots for A3 evidence showing each role's navigation scope. |
| **Phase 4: Accessibility audit** | Sprint 4, Task 8 (Tue 12 May) | All NFR-ACC criteria | Keyboard-only navigation test, contrast ratio audit, font size inspection. Results documented in A3 narrative. |
| **Phase 5: Visual consistency check** | Sprint 4, Task 7 (completed) | All NFR-CLR criteria | Grep codebase for legacy colour codes. Verify wireframes, Streamlit CSS, and design_system.md are aligned. |

### 4.2 Test Data Requirements

| Data | Source | Purpose |
|------|--------|---------|
| Demo users (3 roles) | fixtures/sample_responses.json → `demo_users[]` | Test RBAC and role-based navigation |
| Demo courses (2 courses) | fixtures/sample_responses.json → `courses[]` | Test course selection and cross-course isolation |
| Demo documents (5 files) | fixtures/sample_responses.json → `documents[]` | Test upload status badges and document table |
| Grounded response | fixtures/sample_responses.json → `responses[0]` | Test citation rendering and confidence bar |
| Fallback response | fixtures/sample_responses.json → `fallback_response` | Test fallback label and yellow border |
| Chunk samples | fixtures/sample_responses.json → `chunks_sample[]` | Test citation chip metadata display |

### 4.3 Evidence Mapping for A3

Each acceptance criterion maps to A3 demo evidence:

| A3 Evidence Type | Criteria Covered | Capture Method |
|-----------------|-----------------|----------------|
| Screenshot: Login screen | NFR-CLR-01, NFR-CLR-02 | Wireframe 01_login_screen.png + live prototype |
| Screenshot: Chat with citations | FR-CIT-01, FR-CIT-02, FR-CON-01, FR-CON-02 | Live query with grounded response |
| Screenshot: Fallback response | FR-FBK-01, FR-FBK-02, FR-FBK-03 | Off-topic query triggering fallback |
| Screenshot: Document upload flow | FR-UPL-01, FR-UPL-03, FR-UPL-04 | Upload sequence: pending → processing → indexed |
| Screenshot: Role comparison (3 screens) | FR-NAV-01, FR-NAV-02, FR-NAV-03 | Side-by-side student/lecturer/admin sidebar views |
| Screenshot: Course switching | FR-CSE-01, FR-CSE-02, FR-CSE-03 | Two queries against different courses showing different citations |

### 4.3.1 Sprint 4 Demo UI Readability Re-check

Re-check date: 12 May 2026

The Streamlit demo recording exposed two UI regressions affecting A3 evidence capture:

- AI response cards rendered indented HTML as visible code blocks, hiding citation chips and confidence bars.
- Light panels inherited low-contrast text from Streamlit theme defaults, making some text difficult to read unless selected.

Corrective action: the Streamlit prototype now enforces the design-system text colours for the main content area, inputs, and select controls; AI response cards are rendered through a whitespace-normalising HTML helper so citation chips, fallback labels, and confidence bars display as visual UI elements rather than raw markup. The Streamlit client also attempts the live Flask API by default and falls back to fixtures only when needed.

Second-pass correction: Streamlit button labels are internally rendered as Markdown text, so the global page text rule could override button text and create dark-on-dark labels. Button, form-submit, sidebar navigation, and prompt buttons now have explicit foreground/background rules after the global text rules. Secondary buttons render as white with navy text; primary buttons render as teal with white text; sidebar buttons render as light text on dark navigation backgrounds.

### 4.4 Pass/Fail Summary Template

This template will be used during Sprint 4 integration testing to record results:

| ID | Criterion Summary | Pass/Fail | Notes | Screenshot Ref |
|----|-------------------|-----------|-------|---------------|
| FR-CIT-01 | Grounded response shows citations | | | |
| FR-CIT-02 | Citation chip shows chunk metadata | | | |
| FR-CIT-03 | No cross-course citation leakage | | | |
| FR-CIT-04 | Citation count ≤ top-k | | | |
| FR-CON-01 | Confidence bar matches similarity | | | |
| FR-CON-02 | Confidence bar colour correct | | | |
| FR-CON-03 | Model name displayed | | | |
| FR-CSE-01 | Course selector populated | | | |
| FR-CSE-02 | Query scoped to active course | | | |
| FR-CSE-03 | Active course visually indicated | | | |
| FR-CSE-04 | New session on course switch | | | |
| FR-UPL-01 | PDF/PPTX/DOCX upload accepted | | | |
| FR-UPL-02 | Invalid file types rejected | | | |
| FR-UPL-03 | Upload progress displayed | | | |
| FR-UPL-04 | Status badges correct colours | | | |
| FR-UPL-05 | Failed upload shows retry + error | | | |
| FR-UPL-06 | Chunk/page count after indexing | | | |
| FR-NAV-01 | Student sees 3 nav items only | | | |
| FR-NAV-02 | Lecturer sees 4 nav items | | | |
| FR-NAV-03 | Admin sees 5 nav items | | | |
| FR-NAV-04 | Restricted URL redirects safely | | | |
| FR-NAV-05 | Role badge colours correct | | | |
| FR-FBK-01 | Fallback label on ungrounded reply | | | |
| FR-FBK-02 | Yellow border on fallback message | | | |
| FR-FBK-03 | No citations on fallback reply | | | |
| FR-FBK-04 | Fallback resists prompt injection | | | |
| NFR-ACC-01 | WCAG AA contrast ratios met | | | |
| NFR-ACC-02 | Focus indicators visible | | | |
| NFR-ACC-03 | Tab order matches visual order | | | |
| NFR-ACC-04 | Body text ≥ 14px | | | |
| NFR-ACC-05 | Touch targets ≥ 44×44px | | | |
| NFR-CLR-01 | Navy for structural elements | | | |
| NFR-CLR-02 | Teal for interactive elements | | | |
| NFR-CLR-03 | Gold for tertiary accents | | | |
| NFR-CLR-04 | Semantic colours correct | | | |
| NFR-CLR-05 | Max 2 semantic colours per card | | | |
| NFR-CLR-06 | Chat bubble styling correct | | | |

---

## 5. Traceability Matrix

| Feature Area | FR/NFR IDs | A2 Requirement Layer | A2 Module(s) | Sprint 4 Task |
|-------------|-----------|---------------------|-------------|--------------|
| Source Citations | FR-CIT-01 to 04 | Base (Must have) | M2, M3, M4 | Task 6, 8 |
| Confidence Indicator | FR-CON-01 to 03 | Additional (Should have) | M3, M4 | Task 6, 8 |
| Course Selection | FR-CSE-01 to 04 | Base (Must have) | M4 | Task 6, 8 |
| Upload/Indexing | FR-UPL-01 to 06 | Base (Must have) | M1, M4 | Task 6, 8 |
| Role Navigation | FR-NAV-01 to 05 | Base (Must have) | M4 | Task 6, 8 |
| Fallback Label | FR-FBK-01 to 04 | Base (Must have) | M3, M4 | Task 6, 8 |
| Accessibility | NFR-ACC-01 to 05 | Base (Must have) | M4 | Task 7 (done), 8 |
| Colour Consistency | NFR-CLR-01 to 06 | Base (Must have) | M4 | Task 7 (done) |

---

## Sprint 5 UI Evidence Reference

Anmoldeep Singh provided the A3 interface evidence set under `docs/a3_interface_demo/`.
Treat these screenshots and the accompanying narrative as fixture-backed UI
traceability evidence. They support visual and interaction review, but live
ChromaDB/Ollama retrieval still needs separate Sprint 5 demo validation.
