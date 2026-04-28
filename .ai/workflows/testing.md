# Testing Workflow

## Test Commands

```bash
# Unit tests
pytest

# Targeted parser/chunker tests
pytest test/test_chunker.py

# Lint/compile sanity for integration backend
python -m py_compile apps/integration/backend/api.py

# Validate compose config
docker compose -f docker-compose.yml config
```

## When to Add Tests

Add or update tests when:

- Parser/chunker/embedder behavior changes
- Query/API response schema changes
- Fallback/grounding logic changes
- Integration adapter behavior changes

## Validation Strategy for Agents

For small changes:

1. Run the most targeted command first.
2. Validate syntax/format-sensitive artifacts (JSON/YAML/Python compile).
3. Run `pytest` when behavior changes touch tested code.

For larger changes:

1. Run `pytest`.
2. Validate API schema files parse.
3. Validate integration scripts and startup assumptions.
4. Report any environment-dependent commands not executed.
