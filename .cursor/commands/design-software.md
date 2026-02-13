---
description: Workflow for software design phase — iterative collaboration to produce an approved design document
---

# Design Workflow

## Usage
Invoke with: `/design <spec-or-task-file>`

Example: `/design @docs/lmgate specification.md`

## Objective
Collaborate with the user **iteratively** to produce a **design document** that captures all architectural decisions, component structures, and operational concerns needed for implementation.

This command mimics a **software architect** workflow: analyze requirements, identify design decisions, evaluate options with the user, and converge on an agreed approach.

## Scope — What Design IS and IS NOT

**Design IS**:
- Architecture views: how components are structured and interact
- Component responsibilities and interfaces (conceptual, not code)
- Technology choices with rationale
- Data flow and request flow descriptions
- Configuration and file formats
- Project/module structure
- Dependency choices with justification
- Testing strategy
- Operational concerns: logging, startup/shutdown, security, performance
- Implementation order (what to build first and why)

**Design IS NOT**:
- Implementation code (no Python, YAML, bash, etc. beyond illustrative snippets in the design doc)
- Exact variable names, function signatures, or class hierarchies
- Step-by-step coding instructions
- Requirements definition (that's `task-init`)
- Actual implementation (that's `task-do`)

## Output
A design document saved under `docs/` with a descriptive filename (e.g., `docs/<project>-design.md`). The document must be **reviewed and approved by the user** before the workflow is considered complete.

## Collaboration Process

### 1) Read and internalize the input
- Read the referenced specification or task file.
- Summarize back to the user: what you understand the system must do, key constraints, and non-goals.
- Ask the user to confirm or correct your understanding before proceeding.

### 2) Identify key design decisions
Analyze the requirements and list the **design decisions** that need to be made. These typically include:
- Technology/framework choices
- Architecture pattern (monolith vs. services, sync vs. async, etc.)
- Component decomposition
- Data flow and storage approach
- Error handling and failure modes
- Configuration approach
- Testing approach

Present this list to the user. Ask if there are additional decisions or constraints you missed.

### 3) Discuss each design decision
For **each** key decision:
- Present **2–3 options** with concrete tradeoffs (pros, cons, fit for this project).
- State your recommendation and why.
- **Ask the user** which option they prefer or if they have a different approach.
- Record the decision and rationale.

Do **not** bundle all decisions into one message. Work through them one at a time or in small related groups, giving the user space to think and respond.

### 4) Validate assumptions
Before drafting the document, explicitly list all assumptions you're making (about the runtime environment, deployment model, scale, dependencies, etc.) and ask the user to confirm or correct each one.

### 5) Draft the design document
Write the design document to `docs/`. The document should include:
- Architecture overview (with ASCII diagrams where helpful)
- Request/data flow
- Component design with responsibilities and interfaces
- Configuration format
- Project structure (module layout)
- Dependencies with rationale
- Testing strategy
- Implementation order
- Operational concerns (logging, shutdown, security, performance)

Present the draft to the user for review.

### 6) Iterate on feedback
The user will review the document and provide comments. Incorporate feedback and present the updated version. Repeat until the user approves.

**Do not** consider the design complete until the user explicitly confirms approval.

## Rules

- **No implementation**: Do not write production code, test code, config files, or build system files. The only artifact is the design document.
- **Iterate, don't monologue**: Every step must include a question or checkpoint for the user. Never produce the full design in one shot.
- **One decision at a time**: Present design options in digestible chunks. Let the user steer.
- **YAGNI/KISS**: Propose the simplest design that meets the requirements. Flag complexity and justify it when necessary.
- **Tradeoffs over opinions**: Always present tradeoffs. State your recommendation but let the user decide.
- **Separate concerns**: Keep the design document focused on architecture and structure. Implementation details belong in the coding phase.
- **Follow existing patterns**: Reference `first-principles.md` and `CLAUDE.md` for project conventions.
