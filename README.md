# EduRAG / Paedia

> A course-aware AI study assistant with source citations and a visible fallback label when course evidence is insufficient.

Paedia applies Retrieval-Augmented Generation (RAG) to higher education. Lecturers upload course material; students ask questions and inspect the sources used in an answer. The default stack runs locally with Streamlit, Flask/Gunicorn, PostgreSQL, ChromaDB and Ollama.

## Start here

| I want to… | Where to go |
|---|---|
| Try the team's shared instance | [Shared access](#shared-access) |
| Install a standalone copy | [Quick start](#quick-start), then the [full installation guide](README_docker.md) |
| Start, maintain or troubleshoot my stack | [Operations](docs/operations.md) |
| Understand the code or contribute | [Architecture and development](docs/architecture.md) |
| Review the project or run a demo | [Reviewer checklist](#reviewer-checklist) |

## Shared access

You do not need to install Docker to use the shared instance.

1. Ask the host administrator to share the Paedia host with your Tailscale account.
2. Install Tailscale, sign in with that account and connect. Confirm the shared host is online.
3. Open `http://<shared-host-address>:8501`, or the address and port supplied by the administrator.
4. Sign in or create a student account. New lecturer accounts need administrator approval before sign-in.

If the page does not load, check the host share, Tailscale connection, address and port, then ask the administrator to check the services. `localhost` in installation examples refers to a stack on your own machine.

The repository binds services to loopback by default. Shared-host access requires administrator configuration; it is not enabled by cloning the repository.

## Quick start

This path is for a **new standalone installation**. Follow the [installation guide](README_docker.md) for prerequisites, model selection and complete commands. Run the following from PowerShell.

### 1. Check prerequisites

Install Git and Docker Desktop with the WSL 2 engine, and ensure Docker is running. NVIDIA acceleration is optional and requires working container GPU access. Python 3.11 on the host is optional unless you run notebooks or helper scripts there.

See [prerequisites](README_docker.md#install-the-prerequisites) and [GPU validation](README_docker.md#verify-your-gpu-setup-nvidia).

### 2. Clone and configure

```powershell
git clone --branch develop https://github.com/taylor-b-tran/edu-rag.git
cd edu-rag
Copy-Item .env.example .env
```

Set `PAEDIA_DEMO_ADMIN_PASSWORD`, `PAEDIA_DEMO_LECTURER_PASSWORD` and `PAEDIA_DEMO_STUDENT_PASSWORD` in `.env` if you need the demo accounts. Blank values create new accounts without a known sign-in password. Keep `.env` local.

Review [configuration](README_docker.md#clone-and-configure) and [demo accounts](README_docker.md#demo-credentials), especially if the default ports are in use.

### 3. Start the stack

```powershell
.\scripts\start_stack.ps1
```

The Windows wrapper detects NVIDIA VRAM, writes a model choice to `.env`, starts the matching Compose stack and pulls the selected Ollama model. Current tiers are `gemma4:12b` (at least 12 GB detected VRAM), `qwen2.5:7b` (less than 12 GB) and `llama3.2` (no NVIDIA GPU detected). Model fit and speed depend on the workload.

For manual CPU/GPU commands, PowerShell options or Bash setup, use [startup options](README_docker.md#first-time-startup). The Bash wrapper currently has a different high-tier default; the guide explains the override.

### 4. Prepare course content

**Before querying, [provision the embedding cache](README_docker.md#provision-the-embedding-model-cache).** It is not included in a fresh clone. Manual startup also requires [pulling the selected Ollama model](README_docker.md#pull-the-llm-model).

Upload PDF, PPTX or DOCX material through an approved lecturer account. For a fresh standalone demo, you can instead [load the optional sample corpus](README_docker.md#seed-the-course-corpus). Do not seed an existing shared corpus as an installation shortcut.

### 5. Open and verify

Open `http://localhost:8501` (or your configured `APP_PORT`), sign in, select an enrolled course and ask a question supported by its indexed material. Compare the answer with its source.

Use [service checks](README_docker.md#verify-the-stack-works) and the [demo checklist](docs/operations.md#demo-checklist). An HTTP health response alone does not establish retrieval quality or grounded answers.

For subsequent starts, use the matching [CPU/GPU operation command](docs/operations.md#start-everything-cached). The wrapper saves the model choice but does not persist the GPU Compose overlay.

## Features and roles

| Role | Main actions |
|---|---|
| Student | Sign up, join or leave active courses, ask course-scoped questions, choose an answer style, inspect sources, and continue, search or delete conversations. |
| Lecturer | After approval, create and manage owned courses, upload and delete course documents, track indexing, and tune retrieval for managed courses. Upload/delete rights follow account role plus course membership. |
| Administrator | Manage courses and membership across the system, approve or reject lecturer accounts, change global settings and inspect system status. Administrator accounts are created during installation. |

Answers show source tags such as `[S1]`, filenames, available page/slide references, a confidence label and model information. PDF and PPTX citations can include page or slide numbers; DOCX citations identify the file without inventing a page.

Retrieval is scoped to the selected course, including installed sample material. When usable evidence is absent, an answer may use general knowledge and is labelled as a fallback. Citations and confidence labels still require source checking.

## How it works

1. A lecturer uploads a supported document to an authorised course.
2. The API extracts text, chunks it, embeds it and indexes course-scoped metadata in ChromaDB.
3. A student question retrieves relevant evidence, including supported source-context and lexical matches.
4. Ollama generates an answer; the API validates citation tags and returns the answer with source references.
5. PostgreSQL persists accounts, courses, tokens, conversations, settings, feedback and upload metadata.

The default embedding model is `all-MiniLM-L6-v2` (384 dimensions). The default LLM configuration uses local Ollama; initial setup downloads images, dependencies and model weights.

See [architecture](docs/architecture.md) for the service table, diagrams, query/upload flows, confidence logic, repository layout and dependency versions.

## Known limitations

- **Grounding:** generated answers can be wrong. General-knowledge fallbacks are not course-authoritative answers.
- **Document extraction:** image-only or sparse-text material is limited; provide a text-accessible copy. Exercise statements are material to evaluate, not an answer key. DOCX citations have no page number.
- **Uploads:** PDF, PPTX and DOCX are supported up to 50 MB each. Streamlit's upload caption can still say 200 MB; the enforced application limit is 50 MB.
- **Permissions:** lecturer upload/delete rights follow the account role plus course membership, even when the course membership itself is a student role. New lecturer accounts require approval.
- **Sign-in:** access tokens last about an hour. Reloaded tabs retain the access token but no refresh-token cookie; expiry returns the user to sign-in.
- **Deployment:** the tracked configuration serves HTTP; shared access uses administrator-configured Tailscale connectivity.
- **Missing features:** no audit log, system-wide user directory, password reset, chat export or document replacement in place. Replace a document by deleting and uploading it again.
- **Tuning:** Prompt Strategy is not offered per course because the pipeline reads its strategy at startup.
- **Evaluation:** earlier benchmarks describe their own corpus and revision, not a guarantee of current retrieval quality.

For operational symptoms and recovery steps, use [troubleshooting](docs/operations.md#troubleshooting). For implementation checks, see [code and test links](docs/architecture.md#implementation-and-tests).

## Team

The table summarises assigned responsibilities across sprints, including shared tasks.

| Name | Assigned responsibilities |
|---|---|
| Thanh Binh Tran | Team lead; RAG integration and prompt strategy; authentication, courses and settings backend; shared-host infrastructure; final integration, packaging and technical report coordination. |
| Tai Huynh | API specification, privacy and ethics documentation; deployment guidance and fixture-remnant review; user manuals, assessment evidence indexes and poster. |
| Tung Phuong Anh Huynh | Testing and regression QA; test query corpus and course-material sourcing; demo-readiness checks; meeting agendas, minutes and review records. |
| Andre (Kahavidanage Namaratne) | Data and architecture design (ERD/DFD, schema, risks and storage); requirements traceability; authentication rate limiting and GPU-tier verification; marketing video work with Tai. |
| Thi Hong Ngoc Nguyen | Document parsing, chunking and embeddings; retrieval tuning and evaluation; response-style and feedback backend; RAG review for technical documentation. |
| Anmoldeep Singh | Streamlit frontend and API integration; course selection/joining, response-style selector and History actions; feedback UI, interface design and accessibility. |

## Contributing

- Agree scope and merge timing with the team lead. Work in a separate development checkout and use pull requests into `develop`.
- Keep changes focused. Include relevant checks; new routes need happy-path and permission coverage.
- Review CI results before merging. Compose and Python checks run in CI; the Docker Demo Readiness workflow is path-filtered.

Run product tests in your development stack:

```powershell
docker compose exec api pytest test -q
```

See [development conventions and CI](docs/architecture.md#contributing) for details.

## Reviewer checklist

1. Use shared access or complete installation, including credentials, embedding cache, model and indexed material.
2. Sign in as a student, select an enrolled course and compare a cited answer with the original material.
3. Use an approved lecturer account to upload a short document and follow indexing to completion or inspect its error.
4. Ask a question that depends on that upload, then test a follow-up and an unsupported question.
5. Use the [demo checklist](docs/operations.md#demo-checklist) and [implementation/test map](docs/architecture.md#implementation-and-tests) to inspect the result.

The [A4 requirements matrix](docs/rtm_a4.md) is a historical baseline. Use the requirements matrix and reports accompanying the assessment version being reviewed for its delivery status.

## Documentation

| Document | Contents |
|---|---|
| [Installation and configuration](README_docker.md) | Prerequisites, CPU/GPU setup, environment variables, embedding cache, model pulls, sample seeding, accounts and verification. |
| [Operations and troubleshooting](docs/operations.md) | Start/stop, persistence, environment changes, logs, warm-up, recovery and demo checks. |
| [Architecture and development](docs/architecture.md) | Services, ingestion/retrieval, source context, repository layout, stack versions, contributing and tests. |
| [API specification](docs/api/api_spec.yaml) | API contract; consult the routes for current implementation details. |

## Project context

| Item | Value |
|---|---|
| Subject | UOW CSIT321 Annual Session 2026 — Project 37 |
| Campus | University of Wollongong, Liverpool Campus (SWS) |
| Group | Group 19 — Aletheia's Zetetes |
| Supervisor | Prof. Jun Yan |

## License

University of Wollongong course project repository. Licensing and reuse terms are not yet finalised.
