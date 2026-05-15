# Sprint 4 Kickoff Agenda

## 1. Meeting Details

- Meeting type: Sprint 4 kickoff and supervisor-alignment session
- Project: EduRAG / Paedia, CSIT321 Project 37
- Participants: Group 19 team members and Prof. Jun Yan
- Recommended duration: 45 to 60 minutes

## 2. Sprint 4 Objective

The objective of Sprint 4 is to move from Sprint 3 design consolidation into an integrated working prototype. This includes stabilising the RAG workflow, connecting the UI and API layers, validating retrieval quality with a broader test set, and confirming what evidence must be shown in the final demo.

## 3. Agenda

| Time | Topic | Purpose |
|---|---|---|
| 0-5 min | Sprint 3 recap | Confirm what was completed across RAG PoC, API specification, privacy, ethics, and design updates. |
| 5-15 min | Architecture confirmation | Confirm whether the current RAG pipeline and modular system direction are acceptable for Sprint 4 implementation. |
| 15-25 min | Implementation priorities | Agree which workstreams must be completed first: upload/indexing, query flow, UI integration, testing, or monitoring. |
| 25-35 min | Validation expectations | Clarify what evidence is required in the Sprint 4 demo and what counts as sufficient proof of functionality. |
| 35-45 min | Risk and blocker review | Review technical, privacy, ethics, and time-risk issues that could delay integration. |
| 45-60 min | Task ownership and deadlines | Assign owners, confirm acceptance criteria, and set internal milestones. |

## 4. Decisions Needed

- Is the current RAG architecture acceptable for Sprint 4 implementation?
- Should Streamlit remain the main demo UI, or should FastAPI/React begin as a stretch direction only?
- Are `/api/metrics` and `/api/logs` required route names, or are `/api/admin/stats` and `/api/admin/audit-logs` acceptable as long as mapping is documented?
- What privacy retention standard is expected for a student prototype storing sessions, uploads, and audit events?
- What evidence must be shown in the Sprint 4 demo: notebook, Streamlit UI, API calls, or all three?
- Are source citations and fallback labels sufficient as the minimum ethical control set at this stage?

## 5. Questions For Prof. Jun Yan

- Is the current RAG architecture acceptable for Sprint 4 implementation?
- Should the team keep Streamlit as the main demonstration UI for Sprint 4, or start a FastAPI/React migration only as a stretch path?
- Are `/api/metrics` and `/api/logs` required route names for assessment alignment, or are the explicit admin route names acceptable?
- What level of privacy retention detail is expected for a student prototype?
- Does the supervisor want the Sprint 4 evidence to include notebook output, UI walkthrough, direct API evidence, or a combination?
- Are visible source citations and fallback labels enough for the current ethics expectation, or is further moderation evidence required?

## 6. Proposed Sprint 4 Workstreams

| Workstream | Scope | Suggested owner |
|---|---|---|
| Query pipeline integration | Connect retrieval, prompt strategy, and answer formatting into the main prototype flow. | Binh |
| Document ingestion and indexing | Finalise upload handling, parser reliability, indexing jobs, and status polling. | Ngoc / backend contributors |
| UI integration | Connect authentication, chat, document management, and fallback/citation display. | Anmoldeep |
| API alignment and documentation | Keep routes, auth, validation notes, and monitoring endpoints aligned with assessment expectations. | Tai |
| Data model and operational controls | Validate ERD/DFD updates, audit logging, and storage assumptions. | Namaratne |
| Test assets and evaluation | Run the broader query set, record outcomes, and identify regression cases. | Tung |

## 7. Risks And Blockers

- Retrieval quality may still be overestimated because the larger labelled query set was not fully used in the early benchmark pass.
- Parser quality for PPTX and DOCX may still lag behind the PDF-first PoC path.
- The current backend implementation maturity may not yet match the documentation completeness.
- Cross-course leakage must remain a non-negotiable check in retrieval and API access control.
- Privacy retention and audit access rules still need supervisor-confirmed boundaries.
- Time may be split between polishing the demo path and beginning stretch architecture work too early.

## 8. Acceptance Criteria For Sprint 4

- A user can authenticate and access the correct role-scoped interface.
- A lecturer can upload a supported course document and observe indexing progress or outcome.
- A student can submit a course-scoped query and receive an answer with visible sources where grounding is available.
- Off-topic or weak-retrieval cases return a clearly labelled fallback response instead of an unsupported course-grounded answer.
- Retrieval remains scoped by `course_id`.
- The team can demonstrate the integrated prototype through at least one agreed evidence path.
- Outstanding privacy, ethics, and risk items are documented honestly rather than hidden.

## 9. Pre-Meeting Checklist

- Review the latest Sprint 3 deliverables and confirm the package file set.
- Bring one example notebook-based query result and one example UI or API flow if available.
- Prepare a short list of unresolved technical blockers.
- Confirm which route naming, UI, and deployment decisions still require supervisor input.
- Bring the current test query set and known risk items for discussion.
