---
status: done
---

# Add Code Quality Tooling (Linter, Formatter, Type Checker)

**Date**: 2026-02-16

## Context

The LMGate MVP was implemented as a one-day prototype. The project skeleton (`pyproject.toml`) includes runtime and test dependencies but no code quality tooling. There is no linter, formatter, or type checker configured.

## Problem

Without automated code quality tooling:

- Code style is inconsistent and depends on whoever wrote the code (human or AI agent).
- Common bugs that static analysis catches (unused imports, type mismatches, unreachable code) go undetected until runtime.
- New contributors (human or agent) have no guardrails — they must infer the style from existing code.
- The `/software-build` workflow's Phase 0 (project skeleton) didn't establish these tools, so all 75 tests and all production code were written without linting or type checking.

**Cost of inaction**: As the codebase grows, style drift accumulates and static-analysis-catchable bugs slip through. Retrofitting linting on a larger codebase is more painful than establishing it early.

## Goals

- A linter and formatter is configured and passes on the existing codebase.
- A type checker is configured and passes on the existing codebase (or has a documented baseline of known issues).
- Running quality checks is a single command.

## Non-Goals

- CI/CD pipeline integration — that is a separate task.
- Enforcing 100% type coverage on day one — a pragmatic baseline is sufficient.
- Changing the existing code style significantly — configure the tools to match the existing style where possible.

## Constraints & Assumptions

- Python 3.12+ project using `pyproject.toml` for configuration.
- Tooling should be added as dev dependencies in `pyproject.toml`.
- Configuration should live in `pyproject.toml` (not separate config files) where the tool supports it.
- The existing 75 tests must continue to pass after tooling is added.

## Acceptance Criteria

- [ ] A linter + formatter (e.g., ruff) is configured in `pyproject.toml` and runs cleanly on `lmgate/` and `tests/`.
- [ ] A type checker (e.g., mypy) is configured in `pyproject.toml` and runs on `lmgate/` with no errors (or a documented, minimal exclusion list).
- [ ] A script `scripts/lint.sh` (or equivalent) runs all quality checks in a single command.
- [ ] Dev dependencies are updated in `pyproject.toml`.
- [ ] All existing 75 tests continue to pass.
- [ ] Existing code requires minimal changes to pass the new checks (tools are configured to match the existing style).

## Validation Steps

1. Install dev dependencies: `uv pip install -e ".[dev]"`.
2. Run the lint script: `./scripts/lint.sh`.
3. Verify zero lint errors and zero type errors.
4. Run the test suite: `pytest tests/`. Verify all 75 tests pass.
5. Intentionally introduce a lint violation (e.g., unused import) and verify the linter catches it.

## Risks & Rollback

- **Risk**: Strict linter/type checker settings may require many changes to existing code. Mitigation: configure with pragmatic defaults that match the existing style; use per-file ignores sparingly if needed.
- **Rollback**: Remove the tooling configuration from `pyproject.toml` and delete the lint script. No impact on production code or tests.
