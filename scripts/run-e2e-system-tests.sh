#!/usr/bin/env bash
# Run end-to-end system tests against real LLM APIs.
#
# Usage: ./scripts/run-e2e-system-tests.sh [pytest-args...]
#
# Brings up the full stack (nginx + lmgate) via Docker Compose using the
# production nginx config (real API upstreams), generates an allowlist
# containing the real API keys, runs the e2e system pytest suite, then
# tears everything down.
#
# Requires OPENAI_API_KEY and/or ANTHROPIC_API_KEY in .env or environment.
# Tests for missing keys are skipped, not failed.

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_FILES="-f ${PROJECT_ROOT}/docker-compose.yaml -f ${PROJECT_ROOT}/tests/e2e/docker-compose.e2e-system.yaml"
COMPOSE="docker compose ${COMPOSE_FILES}"
DATA_DIR="${PROJECT_ROOT}/tests/e2e/data"
STATS_PATH="${DATA_DIR}/stats.jsonl"
ALLOWLIST_PATH="${DATA_DIR}/allowlist.csv"
ALLOWLIST_BACKUP="${ALLOWLIST_PATH}.bak"

# Source .env if present
if [ -f "${PROJECT_ROOT}/.env" ]; then
    set -a
    source "${PROJECT_ROOT}/.env"
    set +a
fi

# Check for at least one API key
if [ -z "${OPENAI_API_KEY:-}" ] && [ -z "${ANTHROPIC_API_KEY:-}" ]; then
    echo "WARNING: Neither OPENAI_API_KEY nor ANTHROPIC_API_KEY is set."
    echo "All system tests will be skipped."
fi

cleanup() {
    echo "--- Tearing down e2e system stack ---"
    ${COMPOSE} down -v --remove-orphans 2>/dev/null || true
    rm -f "${STATS_PATH}"
    # Restore original allowlist
    if [ -f "${ALLOWLIST_BACKUP}" ]; then
        mv "${ALLOWLIST_BACKUP}" "${ALLOWLIST_PATH}"
    fi
}

trap cleanup EXIT

echo "--- Cleaning previous state ---"
rm -f "${STATS_PATH}"

# Back up the original allowlist and generate one with real API keys
echo "--- Generating allowlist with real API keys ---"
cp "${ALLOWLIST_PATH}" "${ALLOWLIST_BACKUP}"

NEXT_ID=100
if [ -n "${OPENAI_API_KEY:-}" ]; then
    echo "${NEXT_ID},${OPENAI_API_KEY},e2e-system-openai,2026-01-01" >> "${ALLOWLIST_PATH}"
    NEXT_ID=$((NEXT_ID + 1))
fi
if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
    echo "${NEXT_ID},${ANTHROPIC_API_KEY},e2e-system-anthropic,2026-01-01" >> "${ALLOWLIST_PATH}"
fi

echo "--- Building and starting e2e system stack ---"
${COMPOSE} up --build -d

echo "--- Waiting for stack to be healthy ---"
MAX_WAIT=30
for i in $(seq 1 ${MAX_WAIT}); do
    if curl -sf http://localhost:8080/healthz > /dev/null 2>&1; then
        echo "Stack healthy after ${i}s"
        break
    fi
    if [ "$i" -eq "${MAX_WAIT}" ]; then
        echo "ERROR: Stack did not become healthy within ${MAX_WAIT}s"
        echo "--- Container logs ---"
        ${COMPOSE} logs
        exit 1
    fi
    sleep 1
done

echo "--- Running e2e system tests ---"
export E2E_NGINX_URL="http://localhost:8080"
export E2E_STATS_PATH="${STATS_PATH}"

python -m pytest "${PROJECT_ROOT}/tests/e2e/test_e2e_system.py" "${@:--v}"
TEST_EXIT=$?

echo "--- Done (exit code: ${TEST_EXIT}) ---"
exit ${TEST_EXIT}
