# Known Issues and Gotchas

## Known Issues

| Issue | Area | Impact | Workaround / Status |
|---|---|---|---|
| Sponsor review artifact intentionally deferred | Meetings docs | Task 19 not complete yet | Do not create/modify sponsor review file until meeting occurs |
| Integration startup historically used misspelled folder (`itegration`) | Task 20 branch artifacts | Path confusion and broken script assumptions | Canonicalized to `apps/integration`; keep all new work there |
| `test/` and `tests/` both exist | Test structure | Contributor confusion | Use `test/` for pytest unit tests, `tests/` for corpus assets |
| Requirements file contains mixed pinned and broad spec lines | Dependency management | Potential install variance across machines | Keep existing for now; rationalize only with explicit dependency task |

## Gotchas

- Run commands from repository root unless a script clearly states otherwise.
- Streamlit/UI integration depends on backend availability and fixture fallback behavior.
- Docker stack includes a bootstrap `app` container, not a production API service.
- Raw sample materials belong outside git; only manifest metadata should be tracked.

## Environment Notes

- `.env.example` provides required variable names; keep real secrets out of git.
- Ollama model pull is manual (`qwen3:14b` default) and can be hardware-dependent.
- GPU override requires Docker + NVIDIA runtime support (`docker-compose.gpu.yml`).
