---
description: Workflow for defining a task
---
# Task-Init Workflow

## Usage
Invoke with: `/task-init <task-title>` (or `/task-define @tasks/backlog/<new-task-file>.md`).

## Objective
Collaborate with the user to **define a new task** with **clear, non-ambiguous requirements** that can be executed later.

This command mimics a **product manager** workflow (problem definition), not a developer workflow (solution design).

This command is **requirements definition only**:
- Do **not** implement the task.
- Do **not** make code/config changes beyond writing the task definition document (if requested).
- Do **not** propose or evaluate solutions/approaches. If the user asks “how should we build it?”, capture that as a follow-up to be handled later under execution/planning.

## Output
Produce a task definition document saved under `tasks/backlog/` following the naming and structure defined in `@docs/task-management.md`. The document must contain:
- Problem statement and motivation
- Explicit scope and non-goals
- Constraints and assumptions
- Success metrics (if applicable)
- Acceptance criteria (definition of done)
- Validation steps (how to verify the outcome)
- Risks and rollback (when applicable)

## Collaboration Process

### 1) Establish the problem (and whether it’s real)
Ask for:
- **Current situation**: what is happening today?
- **Problem statement**: what is the concrete pain / failure / risk?
- **Evidence**: errors, screenshots/log snippets, links to docs, etc.
- **Impact**: who is affected and how often?
Optional (but useful for clarity):
- **Who is the user** (or system) experiencing the problem?
- **What decision or workflow is blocked/degraded?**

Apply these checks (ask explicitly if unclear):
- **Do we understand what problem we solve?**
- **Is it really a problem?** (or just a preference / “nice to have”)
- **What happens if we don’t do it?** (cost of inaction, risks, opportunity cost)

### 2) Specify scope precisely (avoid ambiguity)
Convert goals into precise statements:
- **In-scope**: what must change (and where), what must be true afterward
- **Out-of-scope**: what we explicitly will not do
- **Dependencies**: environments, hosts, repos/submodules, external services
- **Constraints**: security, availability, performance, backwards compatibility, deadlines
- **Assumptions**: what we assume is true; how we’ll validate assumptions

Identify missing details and ask targeted clarification questions until the task is executable without guesswork.

### 3) Define success (PM-style)
Turn the problem into measurable success where possible:
- **Success metrics** (optional): what metric should move, in what direction? (e.g., reduce failures, reduce manual steps, shorten time-to-deploy)
- **Acceptance criteria**: observable outcomes that must be true when done
- **Non-goals**: explicitly list tempting adjacent work that will not be included

Do not choose an implementation approach here.

### 4) Define acceptance criteria and validation steps
Requirements must be testable. Write:
- **Acceptance criteria**: specific, observable outcomes (bulleted)
- **Validation steps**: exact commands and/or manual steps to confirm success
- **Rollback plan**: how to revert safely (when relevant)

### 5) Produce the task file
If the user did not provide a file path, create one under `tasks/backlog/` using the naming convention from `@docs/task-management.md`:
- `tasks/backlog/YYYYMMDD[_NN]_<description>.md`

The file must start with a YAML header:
```yaml
---
status: backlog
---
```

Followed by these sections:
- Title
- Date
- Context
- Problem
- Goals
- Non-goals
- Constraints & assumptions
- Success metrics (optional)
- Acceptance criteria
- Validation steps
- Risks & rollback

Stop after the definition is written and confirmed by the user (no execution yet).
