#!/usr/bin/env bash
# Run all code quality checks: ruff (lint + format) and mypy (type check).
set -euo pipefail

echo "==> ruff: lint"
uv run ruff check lmgate/ tests/

echo "==> ruff: format"
uv run ruff format --check lmgate/ tests/

echo "==> mypy"
uv run mypy lmgate/

echo "All checks passed."
