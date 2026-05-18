# Sprint 4 Risk Register

Project: EduRAG / Paedia, CSIT321 Project 37, Group 19
Sprint: Sprint 4
Status date: 12 May 2026
Source task: Task 20 - Sprint 4 risk register update

## Current Risk Status

| ID | Risk | Impact | Likelihood | Mitigation | Owner | Status |
|---|---|---|---|---|---|---|
| R1 | Flask API implementation slips past the Sprint 4 integration chain | Blocks Streamlit wiring, 31-query testing, sequence diagram validation, and API-spec validation | High | The Flask wrapper has now landed under `src/api/` and is covered by `test/test_api.py`; keep API changes PR-gated in Sprint 5 | Binh | Closed for Sprint 4 |
| R2 | ERD documentation diverges from the live PostgreSQL schema | Architecture evidence becomes misleading for A2/A3 | Medium | Keep `db/migrations/001_initial_schema.sql` as the source of truth; preserve the reconciled ERD under `docs/architecture/diagrams/erd_v2.png` | Namaratne | Closed with follow-up |
| R3 | Streamlit frontend cannot integrate with the Flask API | Prototype demo path becomes unavailable for A3 evidence | Medium | Keep fixture fallback mode while validating live API calls through `apps/streamlit/api_client.py` and `apps/integration/start.sh` | Anmoldeep | Mitigated |
| R4 | Fixture-mode benchmark is mistaken for live RAG quality | Team overclaims demo readiness and hides retrieval gaps | High | Separate fixture benchmark from live ChromaDB benchmark; Sprint 5 must rerun the 31-query corpus against seeded live retrieval | Binh / Tung | Active |
| R5 | ChromaDB retrieval returns irrelevant or weak context | Reduced groundedness and citation quality in the demo | Medium | Seed a controlled CSIT321 corpus and track retrieval relevance, citation accuracy, fallback correctness, and latency in Sprint 5 | Binh / Ngoc | Active |
| R6 | LLM provider timeout or unavailable model breaks the demo | Query flow fails during rehearsal or recording | Medium | Keep Ollama as the default local provider, avoid full model pull in CI, and preserve safe fallback/error messaging | Binh | Monitoring |
| R7 | PPTX/DOCX parsing exposes unsupported layouts | Corpus expansion evidence becomes unreliable | Medium | Restrict Sprint 4 evidence to standard layouts and carry complex layout cases into Sprint 5 parser hardening | Ngoc | Monitoring |
| R8 | OpenAPI specification drifts from Flask routes | API documentation becomes invalid or misleading | Medium | Revalidate `docs/api/api_spec.yaml` after route changes; keep `docs/api/api_spec_validation.md` as the handoff note | Tai | Mitigated |
| R9 | A3 screenshots or recording are captured too late | Final presentation evidence is weak or inconsistent | Medium | Create a clean demo script, capture screenshots immediately after the integrated path is stable, and keep pending evidence visible | Anmoldeep / Tai | Active |
| R10 | Sprint 4 recording or sponsor-review evidence is claimed without a real source | Documentation loses credibility | High | Do not fabricate links or meeting notes; mark Task 4 and Task 17 as evidence-blocked until a real URL or meeting record exists | Binh / Tung | Active |
| R11 | GitHub Actions or Docker demo workflow is missing before Sprint 5 | Demo readiness depends on local-only manual checks | Medium | Add CI and Docker demo-readiness workflows, then require them on Sprint 5 PRs | Binh | Mitigated |
| R12 | Raw private course materials or secrets are committed | Privacy and repository hygiene risk | High | Keep `data/samples/` ignored, validate fixtures, and never commit real API keys or Moodle-only materials | All | Active |

## Carry-Forward Risks for Sprint 5

The highest-priority Sprint 5 risks are R4, R5, R9, R10, and R12. They affect
demo credibility more than basic API stability. The team should treat live RAG
benchmarking, screenshot capture, and honest evidence boundaries as the first
Sprint 5 planning checks.
