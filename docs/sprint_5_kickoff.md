# Sprint 5 Kickoff - Demo Readiness and CI/CD

Project: EduRAG / Paedia, CSIT321 Project 37, Group 19
Prepared by: Thanh Binh Tran
Date: 11 May 2026
Latest update: 13 May 2026 after Thanh-owned Docker/CI demo-readiness branch validation
Sprint window: 14 May 2026 to 28 May 2026
Source task: Sprint 4 Task 5 - Sprint 5 plan outline
Shared tracker: https://docs.google.com/spreadsheets/d/13Y9YarTRwCqpFcu7riYiWvzZRK6QBciaeHPsMDXAOfI/edit

## 1. Sprint Goal

Sprint 5 moves Paedia from a connected Sprint 4 prototype into a demo-ready
system. The sprint should prove that the team can run, test, and demonstrate
the integrated Streamlit + Flask + PostgreSQL + ChromaDB + Ollama stack from a
repeatable GitHub and Docker workflow.

The key shift is from "works locally with fixtures" to "can be demonstrated
reliably from a clean branch, with CI evidence and a seeded RAG path".

## 2. Current Baseline

| Area | Current state as of 12 May 2026 |
|---|---|
| Branch baseline | Local `develop` is synced with `origin/develop`, with Sprint 4 handoff work still uncommitted locally |
| Sprint 4 API | Flask API exists under `src/api/` with auth, query, upload, documents, sessions, health, and admin compatibility routes |
| UI integration | Streamlit can call the Flask API through `apps/streamlit/api_client.py` and `apps/integration/start.sh`; latest fixes improve button contrast, response-card rendering, role normalisation, and live API default behaviour |
| RAG benchmark | 31-query fixture-mode API benchmark completed: 6 PASS, 6 PARTIAL, 19 FAIL |
| RAG config | Keep `chunk_size=1024`, `chunk_overlap=0`, `top_k=5`, threshold `0.65` until a live ChromaDB rerun proves a better setting |
| Docker | Compose stack now has explicit `api` and `streamlit` demo services plus `postgres`, `chromadb`, and `ollama`; the old `app` container is retained only as a `tools` profile |
| CI/CD | CI and Docker demo workflows exist on `develop`; Thanh's Sprint 5 branch adds a demo service contract check and Ollama service smoke test |
| Sprint 4 evidence | Task 4 recording link is filed in `docs/meetings/sprint3_internal_demo.md`; Task 8 screenshots and Task 17 sponsor-review note remain open |

### 2.1 Sprint 4 Handoff Status

Sprint 5 should start from the following honest handoff boundary:

- The connected Flask + Streamlit prototype is runnable and recordable.
- The Sprint 4 demo recording link has been filed, but its share access should still be checked from a non-owner account before final A3 evidence freeze.
- The current query path is still fixture-backed at the Flask backend layer.
- The UI readability bugs found during the first recording pass have been addressed locally and must be included in the first publication PR.
- `docs/a3_interface_demo/` is still missing and should be produced from the corrected UI rather than from the earlier low-contrast recording.
- Sprint 4 sponsor-review evidence is still pending the professor meeting.

## 3. In Scope

- Add GitHub Actions CI for Python tests, JSON validation, compile checks, and
  Docker Compose validation.
- Add a Docker demo readiness workflow that can be run manually before demo
  rehearsals.
- Keep `develop` protected through PR-only merges and evidence-backed review.
- Publish the Sprint 4 handoff artifacts from a clean PR before starting larger
  Sprint 5 feature work.
- Turn the fixture-backed query path into a seeded live demo path using the
  current Flask API contract.
- Rerun the 31-query benchmark against live retrieval once seeded ChromaDB data
  is available.
- Prepare A3 demo evidence: screenshots, benchmark table, Docker run notes,
  API/UI smoke test, and final limitations.

## 4. Out of Scope

- No React rewrite unless Streamlit blocks the final demo.
- No public cloud production deployment in Sprint 5 unless the team first
  approves hosting, secrets, cost, and privacy boundaries.
- No real student data or private course material in Git.
- No raw binary sample corpus files unless the team explicitly changes the
  current Git policy and documents licensing.
- No takeover of another member's deliverable without that member's review or
  a clearly recorded dependency handoff.
- No microservices split; the modular monolith remains the target for A3.

## 5. Sprint 5 Workstreams

| ID | Workstream | Primary owner | Outputs | Acceptance check |
|---|---|---|---|---|
| W1 | GitHub CI workflow | Thanh Binh Tran | `.github/workflows/ci.yml` | PRs run Python tests, compile checks, JSON validation, and Compose config validation |
| W2 | Docker demo readiness workflow | Thanh Binh Tran | `.github/workflows/docker-demo.yml` | Manual workflow validates Compose and smoke-tests core demo services |
| W3 | Demo stack packaging | Thanh Binh Tran + Tai Huynh | Docker run notes, app container decision, updated demo commands | A clean checkout can start the demo path without hand-editing commands |
| W4 | Live RAG seed path | Thanh Binh Tran + Ngoc Nguyen | Seeded corpus ingestion path, ChromaDB records, source citations | At least five CSIT321 queries return grounded answers with citations |
| W5 | API/UI demo flow | Tai Huynh + Anmoldeep Singh | Login, upload, query, citations, session history demo flow | Streamlit shows the same evidence returned by Flask API |
| W6 | Benchmark and test evidence | Tung Huynh + Thanh Binh Tran | Updated 31-query live benchmark, smoke-test results | Fixture benchmark is clearly separated from live retrieval evidence |
| W7 | A3 evidence pack | Whole team, led by Thanh Binh Tran | Demo script, screenshots, recording link, final limitations, recording checklist | Team can rehearse the final demo using one agreed script and a verified evidence folder |

## 6. CI/CD Implementation Plan

### 6.1 Continuous Integration

The `ci.yml` workflow should run on pull requests and pushes to `develop` or
`main`.

Checks:

- Set up Python 3.11.
- Install `requirements-dev.txt`.
- Compile key runtime modules:
  - `src/api/app.py`
  - `apps/integration/backend/api.py`
  - `apps/streamlit/main.py`
  - `src/document_processor/chunker.py`
- Run `python -m pytest -q`.
- Validate JSON fixtures and benchmark artifacts.
- Validate `docker-compose.yml` and `docker-compose.gpu.yml` with Docker
  Compose config.

Required status before merging Sprint 5 PRs:

- Python test job passes.
- Docker Compose validation passes.
- Sprint 5 demo service contract check confirms `api`, `streamlit`, `postgres`,
  `chromadb`, and `ollama` are present with the expected service dependency
  chain.
- No benchmark or fixture JSON parse errors.
- PR description states whether the change affects demo behaviour.

### 6.2 Docker Demo Readiness

The `docker-demo.yml` workflow should be available as a manual
`workflow_dispatch` run and should also run when Docker-related files change on
`develop`.

Checks:

- Validate the Compose bundle.
- Build and start `postgres`, `chromadb`, Ollama, Flask API, and Streamlit
  without pulling the full generation model.
- Smoke-test PostgreSQL with `pg_isready`.
- Smoke-test ChromaDB heartbeat.
- Smoke-test Ollama `/api/tags`.
- Smoke-test Flask API `/api/health`.
- Smoke-test Streamlit `/_stcore/health`.
- Smoke-test the lightweight `tools` profile container with `python --version`.
- Always tear the stack down after the run.

Sprint 5 should not treat this as production deployment. It is a controlled
demo-readiness gate: if the workflow is green, the infrastructure layer is ready
for a rehearsal; if it is red, the team fixes the stack before recording A3
evidence.

### 6.3 Deployment Boundary

For Sprint 5, "CD" means repeatable demo delivery, not public hosting. The team
can add public or cloud deployment only after answering:

- Where is the app hosted?
- Who owns the secrets?
- What data is loaded?
- What is the cost cap?
- How will the demo be shut down?

Until those answers are documented, the release target is a local Docker demo
stack plus GitHub Actions evidence.

## 7. Docker Demo Target

Minimum Sprint 5 demo command path:

```bash
docker compose up -d --build postgres chromadb ollama api streamlit
docker compose exec ollama ollama pull qwen3:14b
```

If the selected model is already pulled, the second command should be skipped.
The local UI and API should then be reachable at:

```text
http://localhost:8501
http://localhost:5000/api/health
```

Fallback direct-run path for debugging:

```bash
docker compose up -d postgres chromadb ollama
python apps/integration/backend/api.py
PAEDIA_API_URL=http://localhost:5000 PAEDIA_USE_FIXTURES=false streamlit run apps/streamlit/main.py --server.port 8501
```

Preferred Sprint 5 target path:

```bash
docker compose up -d --build
```

This path is now the expected Docker packaging direction. The remaining Sprint
5 work is to complete the live ChromaDB plus Ollama query path behind the API
contract and then record demo evidence from this stack.

## 8. Sprint Calendar

| Date | Focus | Exit condition |
|---|---|---|
| 11-13 May | Close Sprint 4 Task 3, Task 4, and Task 5 | Benchmark JSON, RAG config update, recording link filed, Sprint 5 plan, initial workflows |
| 14-16 May | CI and Docker gates | Green CI on a test PR and manual Docker demo workflow run |
| 17-20 May | Live RAG seed path | Seed corpus ingests into ChromaDB and query API returns citations |
| 21-23 May | UI/API demo hardening | Login, upload, query, sessions, and fallback demo path rehearsed |
| 24-26 May | Live 31-query benchmark | Fixture benchmark replaced or supplemented by live retrieval evidence |
| 27-28 May | A3 evidence freeze | Recording script, screenshots, limitations, and final checklist complete |
| 29 May | Submission buffer | No new feature work unless needed to fix a demo blocker |

## 9. Acceptance Criteria

| ID | Criterion |
|---|---|
| S5-AC-01 | Every PR to `develop` runs GitHub Actions CI. |
| S5-AC-02 | CI runs the Python unit/integration test suite and fails on regression. |
| S5-AC-03 | CI validates all committed JSON benchmark and fixture files. |
| S5-AC-04 | CI validates Docker Compose config for CPU and GPU variants. |
| S5-AC-05 | Manual Docker demo workflow can start and smoke-test core infrastructure services. |
| S5-AC-06 | Demo runbook uses a clean checkout and does not rely on undocumented local state. |
| S5-AC-07 | At least five seeded CSIT321 questions return grounded answers with source references. |
| S5-AC-08 | Off-topic questions return a clear course-grounded fallback. |
| S5-AC-09 | Ambiguous questions either ask for clarification or are explicitly marked as low-confidence fallback. |
| S5-AC-10 | Live 31-query benchmark evidence is stored separately from fixture-mode evidence. |
| S5-AC-11 | A3 demo script states what is implemented, what is fixture-backed, and what remains planned. |
| S5-AC-12 | No raw private course files, secrets, cache folders, or local agent artifacts are committed. |
| S5-AC-13 | Sprint 4 handoff PR includes the recording link, UI readability fixes, benchmark artifacts, risk register, Sprint 5 plan, and publishable evidence notes. |

## 10. Demo Script Outline

1. Show GitHub Actions CI status on the latest `develop` commit.
2. Show Docker Compose validation or the Docker demo workflow result.
3. Start the local demo stack.
4. Log in as a student.
5. Ask a grounded CSIT321 question and show citations.
6. Ask an off-topic question and show fallback behaviour.
7. Log in as a lecturer and upload a supported document.
8. Show indexing job status and document list.
9. Show session history.
10. Close with the benchmark summary and limitations.
11. Link the final recording and screenshots back to the A3 evidence folder.

## 11. Risk Register

| Risk | Impact | Mitigation |
|---|---|---|
| Python dependencies make CI slow | PR feedback becomes painful | Cache pip and keep Docker service smoke tests separate from normal CI |
| Ollama model pull is too large for GitHub Actions | Demo workflow becomes flaky or expensive | Do not pull the full model in CI; keep model validation local/manual |
| Fixture benchmark is mistaken for live RAG quality | A3 evidence overclaims readiness | Keep fixture and live benchmark artifacts separate |
| Docker app services drift from local direct-run commands | Clean checkout demo fails | Keep `api` and `streamlit` Compose services aligned with `apps/integration/start.sh` and validate the service contract in CI |
| Team commits raw sample files or secrets | Repository hygiene and privacy risk | Keep `.gitignore` strict and make CI validate safe fixture/document paths |
| Streamlit/API drift | Demo fails during rehearsal | Add a smoke route and run the demo script from a clean checkout before recording |
| Unpublished Sprint 4 handoff work | Sprint 5 starts from local-only evidence | Open one short PR from a dedicated handoff branch into `develop` before starting larger Sprint 5 implementation |

## 12. Handoff

Sprint 5 starts with two automation gates and one clear product goal:

- CI proves that code and fixtures still pass after each PR.
- Docker demo readiness proves that the infrastructure can be started from a
  clean repository state.
- The team then spends the sprint replacing fixture answers with a seeded live
  RAG path and records A3 evidence from that path.

The first Sprint 5 PR should publish the Sprint 4 handoff artifacts and the
workflow files from a dedicated handoff branch into `develop`. The next PR
should focus on the app-container or API/UI service packaging decision.

## 13. Thanh Branch Validation - 13 May 2026

Current branch: `feature/s5-thanh-demo-readiness`

Local checks completed:

- `python -m py_compile src/api/app.py apps/integration/backend/api.py apps/streamlit/main.py src/document_processor/chunker.py`
- JSON validation for `fixtures/sample_responses.json`, `tests/test_queries.json`,
  `docs/rag_config_benchmark_2026-04-22.json`, and
  `docs/rag_config_benchmark_31q.json`
- `docker compose -f docker-compose.yml config`
- `docker compose -f docker-compose.yml -f docker-compose.gpu.yml config`
- Sprint 5 demo service contract readback from Compose JSON
- Flask API health checked with the Flask test client
- `python -m pytest -q` result: `104 passed`

Not completed locally:

- Full Docker image build and container startup, because Docker Desktop was not
  running on the local machine during validation. The GitHub
  `docker-demo.yml` workflow is the intended remote validation gate for that
  step.

Follow-up local Docker validation:

- Docker Desktop was started and the demo image build completed.
- First startup attempt found stopped legacy `edurag-sprint3` containers using
  fixed names such as `edurag-chromadb`.
- `docker-compose.yml` now avoids fixed global `container_name` values so Sprint
  5 demo containers use Compose project-scoped names and do not collide with
  older local experiments.
- Second startup succeeded with
  `docker compose up -d --build postgres chromadb ollama api streamlit`.
- Local smoke checks passed for PostgreSQL `pg_isready`, ChromaDB heartbeat,
  Ollama `/api/tags`, Flask `/api/health`, Streamlit `/_stcore/health`, and the
  `tools` profile Python container.

## 14. Sprint 5 Integration Gate - 19 May 2026

Thanh's final integration gate is now backed by `scripts/sprint5_integration_gate.py`.
The gate is intentionally lightweight so it can run in both the normal Python CI
job and the Docker demo workflow.

The gate checks:

- no committed text files contain unresolved merge-conflict markers;
- no old misspelled `itegration/` paths are tracked;
- no raw `data/samples/` binaries are tracked without an explicit policy change;
- no local agent metadata paths are tracked;
- the Docker Compose demo contract still contains `postgres`, `chromadb`,
  `ollama`, `api`, and `streamlit`;
- the `api` service depends on PostgreSQL, ChromaDB, and Ollama;
- the `streamlit` service depends on the API service;
- the API and Streamlit services expose health checks.

The normal CI workflow runs the hygiene side of the gate before pytest. The
Docker Compose validation job and Docker demo workflow pass rendered Compose
JSON into the same gate to validate the service contract from the actual
Compose output.

The seeded corpus ingestion module was also corrected so it imports the current
`fixtures.seed_documents` dataset and the local offline embedder from
`src.document_processor.offline_embedder`. Tests now cover the gate helpers and
the offline seeded-ingestion import path, which gives S5-T04 a repeatable local
check before the final demo rehearsal.
