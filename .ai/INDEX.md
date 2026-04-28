# Agent Memory Index

This directory contains persistent project memory for AI coding agents.

Agents should read this file after `AGENTS.md` and before making non-trivial changes.

## Files

- `architecture.md` — high-level system structure and major modules.
- `conventions.md` — coding style, naming rules, and repo conventions.
- `known-issues.md` — recurring limitations, fragile areas, and workarounds.
- `workflows/development.md` — local setup and development flow.
- `workflows/testing.md` — validation strategy and test commands.
- `workflows/debugging.md` — issue triage and debugging tactics.
- `decisions/` — short architectural/implementation decision records.

## Memory Rules for Agents

Update this directory when you learn durable project facts that future contributors should not rediscover.

Good memory candidates:

- Non-obvious architecture decisions
- Canonical file-path conventions
- Repeated setup or branch workflow gotchas
- Integration constraints and fallback behavior
- Durable validation and test practices

Do not store:

- Secrets or credentials
- Temporary speculation
- Large copied source blocks
- Obvious facts directly visible from one nearby file

## Before Starting Work

1. Read `AGENTS.md`.
2. Read this index.
3. Read relevant `.ai/` files.
4. Inspect the real code before changing anything.
5. Follow existing project patterns.

## After Finishing Work

If durable project knowledge changed, update the relevant `.ai/` file and summarize the new memory in your final report.
