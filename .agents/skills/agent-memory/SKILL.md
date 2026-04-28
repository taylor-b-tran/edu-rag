---
name: agent-memory
description: Maintain durable project memory for AI coding agents.
---

# Agent Memory Skill

Use this skill when working in repositories that maintain `.ai/` memory files.

## Before Work

1. Read `AGENTS.md`.
2. Read `.ai/INDEX.md`.
3. Read relevant memory files for the task.
4. Inspect real code before editing.

## During Work

Capture durable knowledge such as:

- architecture boundaries and canonical file paths
- repeated setup/debugging gotchas
- stable workflow/validation commands
- branch/process constraints that prevent regressions

## After Work

Update the appropriate memory file:

- architecture -> `.ai/architecture.md`
- conventions -> `.ai/conventions.md`
- issues/gotchas -> `.ai/known-issues.md`
- workflows -> `.ai/workflows/*.md`
- major decision -> `.ai/decisions/*.md`

## Quality Bar

Store only information that is durable, specific, and safe to commit.
Do not store secrets, temporary speculation, or large code dumps.
