---
status: backlog
---

# Improve Agentic Workflow Rules for Traceability and Spec Consistency

**Date**: 2026-02-16

## Context

During the LMGate MVP implementation, the `/software-build` workflow was used to build the system from a design document. A post-implementation retrospective identified two related problems with the agentic rules and workflows in this project's `.claude/` configuration.

## Problem

**1. Spec vs. design vs. implementation drift.**
The original specification (`docs/lmgate specification.md`) said "simple list of API keys" and "flat file." The design document evolved this to a CSV with `id`, `api_key`, `owner`, `added` columns. The spec was not updated during design or implementation — it was only reconciled after the fact in a manual docs pass. This means the spec was stale and potentially misleading for the entire build phase.

The root cause: no workflow rule requires the spec to be updated when the design introduces new details. The `/software-build` command focuses on implementing the design document but has no checkpoint for spec consistency.

**2. Task files lack artifact links.**
The backlog task `20260216_implement_lmgate_prototype.md` described the problem and goals well, but did not reference the design document (`docs/lmgate-design-claude.md`) that was used as the build input. Anyone picking up the task later would have to guess which design doc applies. Similarly, completed tasks don't link to the commits or test results that prove completion.

The root cause: the task file structure in `.claude/task-management.md` doesn't require or suggest artifact references.

**Cost of inaction**: As more tasks are created and executed, the same drift and traceability gaps will repeat. Specs become unreliable, tasks become disconnected from their design artifacts, and post-implementation docs passes become a recurring manual burden.

## Goals

- Task files link to their related artifacts (design documents, specs, PRs) so that any participant can trace a task to its inputs and outputs.
- The `/software-build` workflow includes a checkpoint that catches spec-vs-design divergence before implementation is complete.
- The `/docs` workflow explicitly checks for spec-design consistency as part of its review.

## Non-Goals

- Changing the shared `agent-conf` repo — these improvements are scoped to LMGate's `.claude/` configuration only.
- Introducing formal change management or approval workflows for spec updates — a simple consistency check is sufficient.
- Automating spec-design diff detection — manual review during workflow checkpoints is acceptable.

## Constraints & Assumptions

- Changes are limited to files under `.claude/` in the LMGate repo: `task-management.md`, `commands/software-build.md`, `commands/docs.md`.
- The task file structure must remain compatible with the organization-wide standard defined in `agent-conf`.
- Artifact references in task files are optional fields (not all tasks have design documents).

## Acceptance Criteria

- [ ] `.claude/task-management.md` includes an optional "Related artifacts" section in the task file structure, with examples showing links to design docs, specs, and PRs.
- [ ] `.claude/commands/software-build.md` includes a step in Phase 2 (Final Validation) that requires checking the functional spec against the design document for consistency, and updating the spec if they have diverged.
- [ ] `.claude/commands/docs.md` includes a step to verify that the functional spec reflects decisions made in the design document.
- [ ] The changes are additive — existing task files and workflows continue to work without modification.

## Validation Steps

1. Read the updated `.claude/task-management.md` and verify the "Related artifacts" section is present with clear examples.
2. Read the updated `.claude/commands/software-build.md` and verify the spec-consistency checkpoint exists in Phase 2.
3. Read the updated `.claude/commands/docs.md` and verify the spec-design consistency check is included.
4. Verify that existing task files (e.g., `tasks/done/20260216_implement_lmgate_prototype.md`) remain valid under the updated structure (backward compatible).

## Risks & Rollback

- **Risk**: Over-prescriptive rules could slow down workflows. Mitigation: keep the additions lightweight — a checklist item, not a gate.
- **Rollback**: Revert the `.claude/` file changes via git.
