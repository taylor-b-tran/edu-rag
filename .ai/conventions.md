# Project Conventions

## General Style

- Primary language: Python (3.10+ expected in practice; container image is 3.11).
- Documentation: Markdown under structured `docs/` domains.
- Config formats: YAML (`docker-compose`, OpenAPI), JSON (fixtures/test corpus).
- Keep focused, minimal changes and avoid broad unrelated formatting churn.

## Naming Conventions

- Python modules/files: snake_case.
- Documentation files: lowercase with underscores where practical.
- Branch naming: follows `SPRINT_BRANCH_WORKFLOW.md` (`feature/s3-*`, `docs/s3-*`, `test/s3-*`).
- Environment variables: uppercase with underscore separators.

## Code Organization

- UI code -> `apps/streamlit/`
- Integration wrapper scripts/backend -> `apps/integration/`
- Core parser/chunker/embedder logic -> `src/`
- Schema/migrations -> `db/`
- Unit tests -> `test/`
- Test corpora/assets -> `tests/`, `data/`, `fixtures/`
- Documentation source-of-truth -> `docs/` (not member subfolders)

## Dependency Rules

- Prefer existing dependencies in `requirements.txt`.
- Do not add new dependencies unless there is clear project need.
- Keep runtime dependencies distinct from optional local tooling where possible.

## Documentation Rules

Update docs when:

- API contracts change (`docs/api/*`)
- Governance behavior changes (`docs/governance/*`)
- Architecture paths or canonical structure changes (`docs/sprint3_cleanup_matrix.md`)
- Integration behavior/commands change (`apps/integration/*`, `README*`)
