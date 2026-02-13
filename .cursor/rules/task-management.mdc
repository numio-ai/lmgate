---
description: Task management rules. Must be followed when creating, executing, or completing tasks.
alwaysApply: true
---

# Task Management Workflow

This document defines how project tasks are managed across all projects in the organization. It applies to all participants — human and AI agent alike.
It is the reference for task lifecycle, naming conventions, storage structure, approval rules, and quality gates. Agent commands (`/task-init`, `/task-do`) implement this standard.

## Task Lifecycle

Every task moves through three states:

```
backlog → active → done
```

| State | Meaning |
|-------|---------|
| **backlog** | Defined and waiting to be picked up |
| **active** | Currently being worked on |
| **done** | Completed and verified |

## Storage

Tasks are stored as Markdown files under the `tasks/` directory. Each lifecycle state has a corresponding subfolder:

```
tasks/
  backlog/
  active/
  done/
```

A task file moves between subfolders as it transitions between states.

## Naming Convention

```
YYYYMMDD[_NN]_<description>.md
```

- `YYYYMMDD` — date the task was created
- `_NN` — optional sequence number when multiple tasks are created on the same day
- `<description>` — short, lowercase, underscore-separated summary

Examples:
- `20260208_fix_numio_demo_cicd_pipeline.md`
- `20260210_01_add_user_auth.md`
- `20260210_02_update_landing_page.md`

## Task File Structure

Every task file must contain a YAML header with at minimum the task status:

```yaml
---
status: backlog | active | done
---
```

The body of the task must include:

- **Problem statement** — what problem are we solving and why
- **Scope** — what is in scope and what is explicitly out of scope
- **Acceptance criteria** — testable conditions that prove completion
- **Quality gates** — validation steps, required reviews, or checks that must pass before the task can be marked done

Optional sections (include when relevant):

- Constraints and assumptions
- Success metrics
- Risks and rollback plan

## Approval

The **initiator** of the task approves state transitions:

- If a **human** initiated the task, the human approves transitions (backlog → active, active → done).
- If a **team lead agent** initiated the task, the agent approves after validation and notification of the product owner.

## Relationship to Git

No formal relationship between tasks and git branches at this time. This is reserved for future scope (e.g., worktree per task).

