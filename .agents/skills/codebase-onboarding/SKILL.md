---
name: codebase-onboarding
description: Analyze an unfamiliar codebase and build a practical project map.
---

# Codebase Onboarding Skill

Use this skill when first entering the EduRAG repository or when major structural updates land.

## Process

1. Read `AGENTS.md` and `.ai/INDEX.md`.
2. Read `README.md` and `README_docker.md`.
3. Inspect dependency/config files (`requirements.txt`, `docker-compose.yml`, `.env.example`, `pytest.ini`).
4. Map major folders (`apps`, `src`, `db`, `docs`, `test`, `tests`).
5. Identify entry points (`apps/streamlit/main.py`, `apps/integration/backend/api.py`, `notebooks/rag_poc.ipynb`).
6. Identify commands for run/test/validation.
7. Document risky areas and deferred items.

## Output

Produce an onboarding summary containing:

- project purpose/status
- stack and module map
- local run commands
- test/validation commands
- known risky areas and pending artifacts

## Rules

- Do not invent commands.
- Do not assume architecture without file evidence.
- Prefer canonical path policy documented in Sprint 3 cleanup matrix.
