# Sprint 4 Summary

Project: EduRAG / Paedia, CSIT321 Project 37, Group 19
Sprint dates: 29 April 2026 to 13 May 2026
Prepared: 12 May 2026
Source task: Task 24 - Sprint 4 summary document

Latest re-check: 13 May 2026, after the Streamlit UI readability fixes,
Sprint 4 demo recording link, and local test pass.

## 1. Sprint Goal Review

Sprint 4 aimed to submit Assessment 2, close remaining Sprint 3 gaps, create
the first connected Streamlit-to-Flask prototype path, and prepare enough
interface/design evidence for Assessment 3 planning.

The sprint materially advanced the prototype: the Flask API wrapper now exists,
the Streamlit client can call it, the document-processing tests are passing, the
31-query benchmark corpus has been executed in fixture mode, and Sprint 5 now
has a CI/CD and Docker demo-readiness plan.

The sprint is not fully closed yet because some evidence deliverables depend on
real external artifacts: the Sprint 4 sponsor-review note and live interface
screenshot pack are still not present in the repository. The demo recording
link is now filed in the Sprint 3 internal demo evidence document. The latest
local demo check confirms that Flask and Streamlit run together, but the backend
health endpoint still reports fixture mode, so the team must not claim a full
live ChromaDB/Ollama RAG path for Sprint 4.

## 2. Completed or Locally Completed Deliverables

| Task | Deliverable | Status | Evidence |
|---:|---|---|---|
| 1 | A2 Appendix G / final proofread | Complete | `docs/reports/Assessment_2_Group19.docx`, `docs/reports/Assessment_2_Group19.pdf` |
| 2 | Flask API wrapper | Complete | `src/api/app.py`, `src/api/routes/`, `test/test_api.py` |
| 3 | 31-query benchmark rerun | Locally complete | `docs/rag_config.md`, `docs/rag_config_benchmark_31q.json` |
| 4 | PoC recording link | Filed, access check pending | `docs/meetings/sprint3_internal_demo.md` |
| 5 | Sprint 5 plan outline | Locally complete | `docs/sprint_5_kickoff.md`, `.github/workflows/ci.yml`, `.github/workflows/docker-demo.yml` |
| 6 | Streamlit to Flask API wiring | Complete after UI re-check | `apps/streamlit/api_client.py`, `apps/streamlit/main.py`, `apps/integration/start.sh`; latest fixes address low-contrast buttons, raw HTML response cards, default live API attempts, and role normalisation |
| 7 | Branding and design system | Complete | `docs/ui/design_system.md`, `docs/ui/assets/paedia_logo_mark.png` |
| 10 | Embedder module and benchmark | Complete | `src/vector_retriever/embedder.py`, `docs/embedding_benchmarks.md` |
| 11 | PPTX/DOCX chunker extension | Complete | `src/document_processor/chunker.py`, passing pytest suite |
| 12 | Parser evaluation update | Complete | `docs/parser_evaluation.md` |
| 13 | Sprint 3 sponsor-review document | Complete | `docs/meetings/sprint3_sponsor_review.docx` |
| 15 | 31-query API test evidence | Complete | `docs/test_results_sprint4.md` |
| 16 | Sample corpus expansion manifest | Complete with raw-file boundary | `data/sample_manifest.md` |
| 18 | ERD v2 schema reconciliation | Complete after review | `docs/architecture/diagrams/erd_v2.png`, `docs/architecture/erd_v2.png`, `docs/architecture/erd_v2_changes.md` |
| 19 | Flask API query sequence diagram | Complete after review | `docs/architecture/seq_api_query.png`, `docs/architecture/seq_api_query.md` |
| 20 | Sprint 4 risk register update | Complete after review | `docs/risk_register.md` |
| 22 | API spec validation | Complete | `docs/api/api_spec.yaml`, `docs/api/api_spec_validation.md` |
| 23 | A3 first draft | Locally complete | `docs/a3_draft.docx`, `docs/a3_draft_source.md` |
| 24 | Sprint 4 summary | Locally complete | `docs/sprint4_summary.md` |
| 25-30 | A2 enrichment tasks | Complete in submitted A2 report | `docs/reports/Assessment_2_Group19.docx` |

## 3. Open Evidence Gaps

| Task | Expected output | Current state | Required action |
|---:|---|---|---|
| 8 | `docs/a3_interface_demo/` with six annotated PNGs and `narrative.md` | Folder is not present | Capture screenshots from the corrected Streamlit/Flask path and label fixture-backed screens honestly |
| 17 | `docs/meetings/sprint4_sponsor_review.docx` | File is not present | Add the actual sponsor-review note after the meeting or from a real meeting source |
| 21 | Moodle submission receipt | Local repo has final report files, but no receipt artifact | Keep evidence external unless the team wants to store a redacted receipt note |

Task 4 is no longer a content gap because the Google Drive recording link is
filed. It still needs a simple non-owner access check before final A3 evidence
freeze.

Task 9, the React scaffold, remains a stretch task and is not required for A3.

## 3.1 Current Re-check Result

Re-check commands run on 12 May 2026:

- `python -m py_compile apps/streamlit/main.py apps/streamlit/api_client.py src/api/app.py apps/integration/backend/api.py src/document_processor/chunker.py`
- `python -m pytest -q`
- JSON parse checks for `fixtures/sample_responses.json`, `tests/test_queries.json`, and `docs/rag_config_benchmark_31q.json`
- Local health checks for `http://localhost:5000/api/health` and `http://localhost:8501`

Results:

- Python compile passed.
- Full pytest suite passed: 104 tests.
- JSON artifacts parsed successfully.
- Flask and Streamlit were both reachable locally.
- Backend mode remains `fixture`, so live retrieval/generation evidence is still a Sprint 5 blocker.
- Multiple Sprint 4 deliverables are currently local-only/uncommitted and must be committed or PR'd before they count as repository-level completion.

## 4. Quality Review of Local Member Outputs

### `C:\studyAssets\CSIT321 - Project\andre`

The folder contains useful intent but should not be merged directly as-is.

Strengths:

- It identifies the right task area: ERD reconciliation, query sequence diagram,
  and risk register.
- The sequence diagram is visually readable.
- The risk register covers several real Sprint 4 risks.

Issues:

- `erd_v2_changes.md` is generic and does not give a concrete table/column
  reconciliation against `001_initial_schema.sql`.
- The ERD image uses simplified integer keys and omits implemented schema areas
  such as `refresh_tokens`.
- The sequence diagram shows a target live RAG flow, but the implemented Sprint
  4 `/api/query` route is still fixture-backed.
- `risk_register.md` keeps several risks as active even after the related work
  landed, and it is not stored at the Sprint plan path `docs/risk_register.md`.
- The Markdown has encoding artifacts in the heading text.

Action taken:

- Kept the existing repository ERD as canonical because it aligns better with
  the SQL schema.
- Added a truthful Sprint 4 sequence diagram for the implemented Flask route.
- Rebuilt the Sprint 4 risk register in the expected repository path.

### `C:\studyAssets\CSIT321 - Project\tai_huynh`

The folder contains one DOCX summary. It is not reliable enough to be the
canonical Sprint 4 summary.

Strengths:

- It attempts to cover task status, metrics, decisions, problems, and Sprint 5
  preview.
- It correctly notes that the React scaffold is a stretch/deferred item.

Issues:

- It claims Task 4, Task 8, Task 17, and Task 23 are done, but the matching
  repository evidence is absent or was only created during this cleanup pass.
- It reports a 31-query benchmark pass rate of `29/31 (94%)`, which conflicts
  with the regenerated benchmark result: 6 PASS, 6 PARTIAL, 19 FAIL.
- It describes ChromaDB/embedder precision issues, but the current benchmark was
  fixture-mode and should not be interpreted as live retrieval precision.
- It says Task 3 had only two query dips, which is inconsistent with
  `docs/rag_config_benchmark_31q.json`.
- Artifact-tool rendering failed on the DOCX table structure, so it is not a
  clean publishable document by the usual visual QA path.

Action taken:

- Created this canonical Markdown summary with corrected task status and honest
  evidence boundaries.
- Created a clean A3 first draft in `docs/a3_draft.docx` and verified it by
  rendering it to page images.

## 5. Sprint 5 Handoff

The team should enter Sprint 5 with three priorities:

1. Capture missing evidence: PoC recording link, sponsor-review note, and six
   A3 interface screenshots.
2. Replace fixture-backed query evidence with seeded live ChromaDB retrieval and
   rerun the 31-query benchmark.
3. Use the new GitHub Actions and Docker demo-readiness workflows as the
   baseline quality gate for all Sprint 5 PRs.

## 6. Professor Brief

Use this short version when speaking with the professor.

What Sprint 4 achieved:

- Submitted Assessment 2 and preserved the final report artifacts in the
  repository.
- Recovered the local repository into a clean baseline on top of `develop`.
- Added a Flask API wrapper with authentication, query, upload, document,
  session, health, and admin compatibility routes.
- Wired the Streamlit prototype to the Flask API and fixed the most visible UI
  readability issues found during the first recording pass.
- Reran the 31-query benchmark in fixture mode and documented the real result:
  6 PASS, 6 PARTIAL, 19 FAIL.
- Filed the Sprint 4 demo recording link in
  `docs/meetings/sprint3_internal_demo.md`.
- Prepared CI and Docker demo-readiness workflows for Sprint 5.
- Prepared Sprint 5 planning around live RAG, demo packaging, evidence capture,
  and GitHub quality gates.

What to show:

- The Streamlit login and chat flow, using the corrected high-contrast UI.
- Flask `/api/health`, making clear that the current backend mode is `fixture`.
- A successful query and fallback query from the connected prototype.
- The demo recording link and the Sprint 4 evidence note in
  `docs/meetings/sprint3_internal_demo.md`.
- The benchmark file and summary result in `docs/rag_config_benchmark_31q.json`
  and `docs/rag_config.md`.
- The Sprint 5 plan, especially the move from fixture-backed answers to seeded
  live ChromaDB/Ollama RAG.
- The new CI and Docker workflow files as the team's quality gate for the next
  sprint.

Be transparent about these remaining items:

- Task 8 screenshot pack still needs to be captured from the corrected UI.
- Task 17 sponsor-review note should be written after the actual professor
  meeting.
- Live ChromaDB/Ollama answer generation is Sprint 5 work, not a completed
  Sprint 4 claim.
