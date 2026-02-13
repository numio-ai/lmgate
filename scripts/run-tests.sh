#!/usr/bin/env bash
# Run the LMGate test suite using pytest.
# Usage: ./scripts/run-tests.sh [pytest-args...]
set -euo pipefail

cd "$(dirname "$0")/.."
python -m pytest "${@:--v}"
