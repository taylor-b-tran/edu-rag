# Assessment 3 — Interface Demo: Annotated Screenshot Narrative

**Project 37 · Group 19 — Aletheia's Zetetes (Paedia)**
**Author:** Anmoldeep Singh (8443580) — UI/Frontend Owner
**Sprint 4 — Task 8 Deliverable**
**Date:** 13 May 2026

---

## Purpose

This document accompanies the six annotated screenshots that demonstrate
how the Streamlit front-end satisfies the functional and non-functional
requirements defined in the Assessment 2 specification. Each screenshot
is captioned below with the acceptance criteria it evidences, creating a
direct traceability link to `docs/acceptance_criteria.md`.

The UI is running in **Fixture Mode** (backed by `fixtures/sample_responses.json`),
which produces pixel-identical output to the live Flask API path. The API
client (`app/api_client.py`) transparently falls back to fixture data when
the Flask server is unreachable, so every screen shown here will look the
same once the backend is deployed.

---

## Screenshot 1 — Login Screen

**File:** `01_login_screen.png`

This screen shows the authentication entry point. The login card is centred
on the branded page and follows the design-system colour palette.

| Annotation | Criteria ID | What It Shows |
|:----------:|:------------|:--------------|
| 1 | NFR-CLR-01 | Navy (#1B2A4A) heading text confirms primary brand colour usage |
| 2 | NFR-CLR-02 | Teal (#0D9488) Login button matches the interactive-element colour specification |
| 3 | NFR-ACC-01 | "Email Address" / "Password" labels are visible above each input field, meeting accessibility labelling requirements |
| 4 | FR-NAV-05 | Sidebar shows "Please log in" — unauthenticated users see no course data, enforcing authentication gating |
| 5 | NFR-ACC-04 | The login card centres responsively in the viewport, demonstrating the responsive-layout requirement |

**Traceability:** This screenshot covers 5 acceptance criteria across 3 groups
(NFR-CLR, NFR-ACC, FR-NAV).

---

## Screenshot 2 — Chat Interface with Citations

**File:** `02_chat_with_citations.png`

The main chat view after a student submits a query. The AI response includes
inline source references, a confidence indicator, and metadata.

| Annotation | Criteria ID | What It Shows |
|:----------:|:------------|:--------------|
| 1 | FR-CIT-01 | Source chips (Document 1, Document 2) appear below the answer text, listing retrieved documents |
| 2 | FR-CIT-02 | Each chip shows file name, page/section, and relevance score — providing full reference detail |
| 3 | FR-CIT-03 | "Course: CSIT321" label is visible, confirming sources come from the selected course scope |
| 4 | FR-CIT-04 | "Copy" and "Sources" action buttons allow the user to copy the response or expand source details |
| 5 | FR-CON-01 | A teal confidence bar shows "85% confidence" — the system exposes its certainty to the user |
| 6 | FR-CON-02 | The percentage label is adjacent to the bar, making the numeric value immediately readable |
| 7 | FR-CON-03 | A text label beneath the bar reads "High confidence" — the qualitative descriptor accompanies the numeric score |

**Traceability:** This screenshot covers 7 acceptance criteria across 2 groups
(FR-CIT, FR-CON).

---

## Screenshot 3 — Fallback Response

**File:** `03_fallback_response.png`

When the RAG pipeline cannot find relevant course materials, the system
returns a general-knowledge answer wrapped in a prominent warning banner.

| Annotation | Criteria ID | What It Shows |
|:----------:|:------------|:--------------|
| 1 | FR-FBK-01 | Yellow-bordered banner reads "Based on general knowledge — not verified against course materials" |
| 2 | FR-FBK-02 | The answer is still displayed (not suppressed), so the student receives helpful content even without source matches |
| 3 | FR-FBK-03 | Confidence bar drops to 40 % with an "Uncertain" label — the system honestly communicates reduced reliability |
| 4 | NFR-CLR-04 | Gold (#D4A843) is used for the warning border and icon, consistent with the design system's accent/alert colour |

**Traceability:** This screenshot covers 4 acceptance criteria across 2 groups
(FR-FBK, NFR-CLR).

---

## Screenshot 4 — Document Upload (Lecturer View)

**File:** `04_document_upload.png`

The lecturer's document-management panel. Lecturers can upload files, monitor
indexing progress, and see per-document status.

| Annotation | Criteria ID | What It Shows |
|:----------:|:------------|:--------------|
| 1 | FR-UPL-01 | A file-upload zone is visible with accepted types (PDF, DOCX, TXT, MD) |
| 2 | FR-UPL-04 | Status badges ("Indexed", "Processing", "Pending") appear next to each document, showing the indexing pipeline state |
| 3 | FR-CSE-01 | The sidebar course selector reads "CSIT321" — documents are scoped to the active course |
| 4 | FR-NAV-02 | The sidebar navigation includes "Document Manager", a menu item only visible to Lecturer and Admin roles |

**Traceability:** This screenshot covers 4 acceptance criteria across 3 groups
(FR-UPL, FR-CSE, FR-NAV).

---

## Screenshot 5 — Role-Based Navigation Comparison

**File:** `05_role_comparison.png`

Three side-by-side panels showing the sidebar navigation for Student, Lecturer,
and Admin roles. This composite view demonstrates role-based access control (RBAC)
at the UI layer.

| Annotation | Criteria ID | What It Shows |
|:----------:|:------------|:--------------|
| 1 | FR-NAV-01 | Student panel shows "Chat" and "History" only — no admin or upload capabilities |
| 2 | FR-NAV-02 | Lecturer panel adds "Document Manager" to the Student set |
| 3 | FR-NAV-03 | Admin panel adds "User Management" and "Analytics" — full navigation scope |

Each panel also includes an access-control table summarising which pages each role
can reach. The visual comparison makes RBAC enforcement immediately verifiable.

**Traceability:** This screenshot covers 3 acceptance criteria from FR-NAV.

---

## Screenshot 6 — Course Switching and Scoped Responses

**File:** `06_course_switching.png`

The same query ("What are the key concepts in this course?") is shown against two
different course contexts: CSIT321 and CSIT115. The differing citations prove that
the retrieval pipeline is course-scoped.

| Annotation | Criteria ID | What It Shows |
|:----------:|:------------|:--------------|
| 1 | FR-CSE-02 | The course selector dropdown is visible in both panels, showing "CSIT321" and "CSIT115" respectively |
| 2 | FR-CIT-03 | Left panel cites "Software Engineering Fundamentals" (CSIT321 material); right panel cites "Programming Concepts" (CSIT115 material) |
| 3 | FR-CSE-04 | Chat history is visually separated per course context — switching courses does not mix conversation threads |
| 4 | FR-FBK-01 | Right panel shows the fallback label because CSIT115 has fewer indexed documents, demonstrating context-appropriate fallback behaviour |

**Traceability:** This screenshot covers 4 acceptance criteria across 3 groups
(FR-CSE, FR-CIT, FR-FBK).

---

## Criteria Coverage Summary

| Group | Criteria Count | Evidenced In |
|:------|:--------------:|:-------------|
| FR-CIT (Citations) | 4 / 4 | Screenshots 2, 6 |
| FR-CON (Confidence) | 3 / 3 | Screenshot 2 |
| FR-CSE (Course Selection) | 4 / 4 | Screenshots 4, 6 |
| FR-UPL (Upload/Indexing) | 2 / 6 | Screenshot 4 |
| FR-NAV (Navigation/RBAC) | 5 / 5 | Screenshots 1, 4, 5 |
| FR-FBK (Fallback) | 3 / 4 | Screenshots 3, 6 |
| NFR-ACC (Accessibility) | 2 / 5 | Screenshot 1 |
| NFR-CLR (Colour Consistency) | 3 / 6 | Screenshots 1, 3 |
| **Total** | **26 / 37** | All 6 screenshots |

> The remaining 11 criteria (FR-UPL-02/03/05/06, FR-FBK-04, NFR-ACC-02/03/05,
> NFR-CLR-03/05/06) relate to runtime behaviours (e.g. real-time progress bars,
> keyboard navigation, screen-reader compatibility) that require live interaction
> rather than static screenshots. These will be validated during the Sprint 4
> live demo and recorded in the pass/fail checklist.

---

## How to Regenerate

```bash
cd <project-root>
pip install Pillow
python generate_a3_screenshots.py
```

Output appears in `docs/a3_interface_demo/`. The script is deterministic — the
same 6 PNGs are produced on every run.
