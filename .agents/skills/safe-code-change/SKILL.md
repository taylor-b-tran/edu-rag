---
name: safe-code-change
description: Make minimal, validated changes while preserving project structure and contracts.
---

# Safe Code Change Skill

Use this skill for any code or documentation modification in EduRAG.

## Before Editing

1. Read `AGENTS.md`.
2. Check `.ai/INDEX.md` and relevant memory files.
3. Confirm canonical destination path for each file (`docs`, `apps`, `fixtures`, `tests`, `data`).
4. Scope changes narrowly and avoid unrelated edits.

## Editing Rules

- Preserve API response contracts unless explicitly requested to change them.
- Keep `Team_Contributions` as ownership index folders (no duplicate source-of-truth files).
- Avoid adding new dependencies unless clearly necessary.
- Do not modify sponsor-review artifacts until explicitly instructed.

## Validation

- Run targeted tests/syntax checks first.
- Run `pytest` when behavior changes affect tested paths.
- Validate JSON/YAML contract files when they change.
- Report unrun or environment-blocked checks honestly.

## Final Report Format

Always summarize:

1. Files changed
2. What/why changes were made
3. Validation run
4. Remaining risks or deferred items
