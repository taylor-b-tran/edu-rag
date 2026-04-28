# Decision 0001: Initial Agent Memory Setup

## Status

Accepted

## Context

The repository has grown across multiple Sprint 3 branches and includes both code and documentation-heavy deliverables. Agents repeatedly need to rediscover architecture, canonical paths, and workflow constraints.

## Decision

Introduce a Markdown-based in-repo agent memory system:

- `AGENTS.md` for top-level agent operating rules
- `.ai/` for durable architecture/conventions/workflow memory
- `.agents/skills/` for reusable task-oriented agent behavior

## Rationale

This approach is lightweight, version-controlled, auditable in PRs, and appropriate for a university project where onboarding speed and consistency matter more than heavyweight external tooling.

## Consequences

- Agents should read `AGENTS.md` and `.ai/INDEX.md` before non-trivial changes.
- Durable findings should be captured in `.ai/` updates.
- Canonical path policy and branch safety rules are now documented for continuity.
