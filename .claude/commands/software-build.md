---
description: Workflow for implementing a solution from a design document using test-driven development
---

# Software Build Workflow

## Usage
Invoke with: `/software-build <design-document>`

Example: `/software-build @docs/lmgate-design-claude.md`

## Objective
Implement the solution described in the design document following **strict test-driven development (TDD)**. Each implementation step defined in the design document is executed in a red-green cycle: write tests first, confirm they run (and fail), implement the functionality, confirm tests pass. Only then move to the next step.

## Scope — What Build IS and IS NOT

**Build IS**:
- Implementation of production code, test code, configuration, and build system files
- Following the architecture, component design, and implementation order from the design document
- Test-driven development: tests before implementation, always
- Creating automation scripts in `./scripts/` when repetitive tasks are identified
- Validating each step before proceeding

**Build IS NOT**:
- Rewriting or questioning the design (that's `/design`)
- Adding features not described in the design document (YAGNI)
- Skipping or deferring tests
- Marking a step complete when tests are failing

## Inputs
- A **design document** (the `<design-document>` argument) containing an "Implementation Order" section with numbered steps
- Each step describes what to build and how to verify it

## Outputs
- Working implementation matching the design
- Complete test suite (unit + integration) covering all implemented functionality
- Automation scripts in `./scripts/` for recurring development tasks
- All tests passing

## TDD Execution Process

### Phase 0: Preparation

1. **Read and internalize the design document.**
   - Identify all implementation steps from the "Implementation Order" section.
   - Create a TodoWrite checklist mapping each design step to a build task.
   - Present the build plan to the user and get approval before writing any code.

2. **Establish the project foundation.**
   - Set up the build system and test runner so that `pytest` (or the project's test command) can execute and report results, even with zero tests.
   - Confirm the test runner works by executing it. If a test runner script does not yet exist in `./scripts/`, create one (e.g., `./scripts/run-tests.sh`).

### Phase 1: Step-by-Step TDD Implementation

For **each** implementation step from the design document, execute in strict order:

#### Step N.1 — Write Tests First (RED)
- Write test files covering the functionality described in this step.
- Tests must exercise the **business logic and edge cases** specified in the design.
- Tests must be runnable. Run them and confirm they **fail** for the right reasons (missing implementation, not import errors or syntax errors). Fix any structural issues until the test runner executes cleanly and reports failures due to missing functionality.
- Present test coverage plan to the user: what scenarios are covered, what edge cases are included.

#### Step N.2 — Implement Functionality (GREEN)
- Write the minimum production code needed to make the tests pass.
- Follow existing code patterns in the repository.
- Do not add functionality beyond what is needed for the current step.
- Run tests. Iterate until **all tests for this step pass**.

#### Step N.3 — Validate and Review
- Run the full test suite (not just the current step's tests) to catch regressions.
- If any test fails, fix the issue before proceeding.
- Present the implementation summary to the user:
  - What was implemented
  - What tests were added
  - Test results
- Get explicit user approval before marking the step complete and moving on.

#### Automation Checkpoint
- During any step, if you find yourself running the same command or sequence repeatedly (test execution, data setup, container management, linting, etc.), create a script in `./scripts/` to automate it.
- Scripts must be executable (`chmod +x`) and have a brief usage comment at the top.
- Keep `./scripts/` organized: one script per concern, descriptive names.

### Phase 2: Final Validation

After all implementation steps are complete:

1. **Run the full test suite.**
   - Execute all unit and integration tests. Every test must pass.

2. **Revisit test completeness.**
   - Walk through the design document section by section.
   - For each functional requirement and edge case described in the design, verify a corresponding test exists.
   - Identify gaps: scenarios described in the design but not yet tested.
   - Write additional tests to close gaps.
   - Run the full suite again and confirm all tests pass.

3. **Final system validation.**
   - If the design includes integration or end-to-end verification steps, execute them.
   - Present the final results to the user.

## Rules

- **Tests before code**: Never write production code without a failing test that demands it. The only exception is project scaffolding (build files, config, directory structure) in Phase 0.
- **No skipping steps**: Execute implementation steps in the order defined by the design document. If a step depends on a prior one, that dependency is already captured in the design's ordering.
- **No silent failures**: If a test fails unexpectedly, stop and investigate. Do not proceed to the next step with failing tests.
- **Scripts are first-class**: Treat `./scripts/` as a project toolbox. Anything you run more than twice during development is a candidate for a script.
- **YAGNI/KISS**: Implement what the design specifies. No extras.
- **User checkpoints**: Get explicit user approval after each implementation step before proceeding. Never batch multiple steps without review.
- **Follow existing patterns**: Reference `first-principles.md` and `CLAUDE.md` for project conventions.
- **Single-task focus**: Work on one step at a time. Do not mix changes from different steps in a single commit.
