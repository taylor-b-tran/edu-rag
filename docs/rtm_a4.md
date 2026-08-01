# Requirements Traceability Matrix — A4

Project 37 | Group 19 — Aletheia's Zetetes | CSIT321
Status as of: 26 Jul 2026 (Sprint 5 baseline; update before A4 submission with any Sprint 6 changes)

> **Source note:** this supersedes the earlier draft in this file. The functional requirement list (FR-001–FR-033) and user-story references (US-Sx/US-Lx/US-Ax) come from `Traceability Matrix.docx` (team draft); light corrections were applied to 3 rows where Sprint 5 evidence had moved past the original status (see "Corrections" below). Non-functional requirements (NFR-001–008) are new — the original draft had none. A polished copy lives at `docs/rtm_a4.docx`.

> **Status legend:** `Implemented` = live and QA-verified · `Partial` = interface/some path works, gap documented · `Planned` = designed but not built.

---

## 1. Functional Requirements

| FR ID | Requirement | Priority | Origin | Source User Story | Status | Evidence |
|---|---|---|---|---|---|---|
| FR-001 | User Authentication | Must | A2 Base | US-A1, US-S1, US-L1 | Implemented | JWT authentication, login system |
| FR-002 | Role-Based Access Control | Must | A2 Base | US-A1, US-S1, US-L1 | Implemented | Student/Lecturer/Admin role permissions |
| FR-003 | Document Upload (PDF) | Must | A2 Base | US-L1 | Implemented | Document upload interface |
| FR-004 | Text Extraction | Must | A2 Base | US-L1 | Implemented | PDF text extraction pipeline |
| FR-005 | Document Chunking | Must | A2 Base | US-L1, US-L4 | Implemented | Chunking pipeline |
| FR-006 | Embedding Generation | Must | A2 Base | US-L1 | Implemented | SentenceTransformer embeddings |
| FR-007 | Vector Indexing | Must | A2 Base | US-L1, US-S5 | Implemented | ChromaDB vector storage |
| FR-008 | Semantic Search | Must | A2 Base | US-S1, US-S5 | Implemented | ChromaDB retrieval |
| FR-009 | Natural Language Query | Must | A2 Base | US-S1 | Implemented | Student chat interface |
| FR-010 | LLM-Grounded Answers | Must | A2 Base | US-S1, US-S2 | Implemented | Ollama response generation |
| FR-011 | Source Citation Display | Must | A2 Base | US-S2 | Implemented | Citation display in responses |
| FR-012 | Async Indexing with Status | Must | A2 Additional | US-L1, US-L4 | **Implemented** | Live chunk→embed→ChromaDB indexing (Sprint 5); was fixture-backed at A3, now real for both seeded corpus and lecturer uploads — *corrected, see below* |
| FR-013 | Multi-Course Support | Must | A2 Additional | US-S5, US-A2 | Implemented | Course-specific retrieval |
| FR-014 | Single-Turn Q&A | Must | A2 Base | US-S1 | Implemented | Student Q&A interface |
| FR-015 | Structured Logging | Must | A2 Additional | US-A6 | Partial | Backend logging support |
| FR-016 | Graceful Fallback — No Course Material Found | Must | A2 Additional | US-S7 | Implemented | Unsupported-answer handling |
| FR-017 | Secrets Management | Must | A2 Additional | Security Foundation | Implemented | Environment variables (.env) |
| FR-018 | Password Hashing | Must | A2 Additional | US-A1 | Implemented | bcrypt password hashing; PostgreSQL user authentication |
| FR-019 | Document Upload (PPTX) | Should | A2 Additional | US-L1 | Implemented | PPTX upload support |
| FR-020 | Document Upload (DOCX) | Should | A2 Additional | US-L1 | Implemented | DOCX upload support |
| FR-021 | Multi-Turn Conversations | Should | A2 Additional | US-S3 | Implemented | Chat history and conversation context |
| FR-022 | Saved Conversation Sessions | Should | A2 Additional | US-S4, US-S8 | Implemented | Conversation history feature |
| FR-023 | Admin Usage Dashboard | Should | A2 Additional | US-A5 | Partial | Live KPI tiles via `/api/admin/stats` (Sprint 5 rev 3); user provisioning ("Add User") intentionally disabled — *corrected, see below* |
| FR-024 | Audit Log Review | Should | A2 Additional | US-A6 | Partial | Logging and audit functionality |
| FR-025 | Rate Limiting | Should | A2 Additional | Platform Protection | Planned | Planned for production deployment |
| FR-026 | Document Management | Should | A2 Additional | US-L1, US-L3 | Implemented | Lecturer document management interface |
| FR-027 | Confidence Scoring | Should | A2 Additional | US-S6 | Implemented | Confidence indicator displayed with responses |
| FR-028 | Retrieval Accuracy Benchmarks | Should | Added Sprint 5 | US-L6, US-A5 | **Partial** | Fixture-mode 31-query benchmark (6 PASS/6 PARTIAL/19 FAIL) + live 5-query manual QA with citations; no formal Precision@5/Recall@10 computed against the live ChromaDB backend yet — *corrected, see below* |
| FR-029 | Export Conversation to PDF | Could | A2 Additional | US-S8 | Planned | Future enhancement |
| FR-030 | Topic Summarisation | Could | Added Sprint 6 | US-S8 | Planned | Sprint 6 feature |
| FR-031 | Query Suggestions | Could | Added Sprint 6 | US-S3 | Planned | Suggested follow-up questions |
| FR-032 | Dark Mode | Could | Added Sprint 6 | UI Enhancement | Planned | UI enhancement |
| FR-033 | Usage Analytics Export | Could | A2 Additional | US-A5 | Planned | CSV export functionality |

### Corrections applied to the team draft

| FR ID | Draft said | Corrected to | Why |
|---|---|---|---|
| FR-012 | Partial — "indexing fixture-backed" | Implemented — live indexing | Sprint 5 (S5-T17/T18) wired real chunk→embed→ChromaDB for both seeded corpus and uploads; the "fixture-backed" note was accurate at A3 but is stale now |
| FR-023 | Partial — "Admin dashboard interface" (vague) | Partial — precise evidence | Sprint 5 rev 3 made KPI tiles live (`/api/admin/stats`); kept status Partial because "Add User" is still explicitly stubbed, but evidence text now says why |
| FR-028 | Implemented — "Precision@5 and Recall@10 benchmarking" | Partial | No formal precision/recall was computed against the *live* backend — only fixture-mode benchmark + ad hoc live QA. Claiming "Implemented" here would overclaim vs. what's actually measured |

---

## 2. Non-Functional Requirements

*(Not present in the team draft — added here.)*

| NFR ID | Requirement | Priority | Origin | Category | Status | Evidence |
|---|---|---|---|---|---|---|
| NFR-001 | System response latency | Should | A2 Base | Performance | Partial | Warm queries observed 2.55–4.17s; cold-start ~45s mitigated by warm-up (Sprint 5 rev 3, `elapsed_ms=164` post warm-up) |
| NFR-002 | Data isolation across courses | Must | A2 Base | Security Foundation | Implemented | ChromaDB `course_id` metadata filter; A3 report Fig. 6 cross-course retrieval test |
| NFR-003 | Accessibility (WCAG AA contrast) | Should | A2 Additional | Usability | Implemented | S5-T09, merged PR #36 |
| NFR-004 | Deployment portability (GPU-optional) | Must | A2 Base | Platform Protection | Partial | GPU moved to compose overlay (QA-DEPLOY-001 resolved); not yet verified via a clean-machine dry run — Sprint 6 T25/T26/T31 |
| NFR-005 | Automated regression test coverage | Should | A2 Additional | Maintainability | Implemented | 112 tests passing, Sprint 5 QA revision 3 |
| NFR-006 | Storage capacity planning | Could | A2 Base | Scalability | Planned | Design-stage estimate only (~8.5–10GB for 10 courses/50 docs/500 pages); not measured against real load |
| NFR-007 | Session/auth token expiry & invalidation | Must | A2 Base | Security Foundation | Implemented | Logout invalidates JWT; verified 401 on subsequent request |
| NFR-008 | Model warm-up (cold-start mitigation) | Could | Added Sprint 5 | Performance | Implemented | `src/api/warmup.py`; verified live `status=ok, elapsed_ms=164` |

---

## 3. Deprioritised / Out of Scope

| Item | Status |
|---|---|
| Expand Q&A into a full learning assistant | Demoted to Low priority by Prof. Jun Yan (27 May sponsor review); explicitly cut from Sprint 6 scope. Report as "planned next iteration," not removed. |
| Live LMS integration, native mobile apps, multi-language UI, automated grading | Explicit exclusion carried over unchanged from A2 |

---

## To finish before A4 (owner: Andre + Thanh, per Sprint 6 T03/T04)

1. Verify FR-015/FR-024 (Structured Logging, Audit Log Review — both "Partial") against current code — no strong evidence found either way, status kept as-is from the team draft rather than guessed.
2. Add any Sprint 6 additions (model fine-tuning T07, vector DB optimisation T09) as new FR/NFR rows once merged, using the same Origin convention ("Added Sprint 6").
3. `docs/rtm_a4.docx` is the polished copy for the report appendix; keep this `.md` in sync if either is edited further.
