#!/usr/bin/env bash
# Run end-to-end Docker integration tests.
#
# Usage: ./scripts/run-e2e-tests.sh [pytest-args...]
#
# Brings up the full stack (nginx + lmgate + mock-upstream) via Docker Compose,
# runs the e2e pytest suite, then tears everything down.

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_FILES="-f ${PROJECT_ROOT}/docker-compose.yaml -f ${PROJECT_ROOT}/tests/e2e/docker-compose.e2e.yaml"
COMPOSE="docker compose ${COMPOSE_FILES}"
STATS_PATH="${PROJECT_ROOT}/tests/e2e/data/stats.jsonl"

cleanup() {
    echo "--- Tearing down e2e stack ---"
    ${COMPOSE} down -v --remove-orphans 2>/dev/null || true
    rm -f "${STATS_PATH}"
}

trap cleanup EXIT

echo "--- Cleaning previous state ---"
rm -f "${STATS_PATH}"

echo "--- Building and starting e2e stack ---"
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

echo "--- Running e2e tests ---"
export E2E_NGINX_URL="http://localhost:8080"
export E2E_STATS_PATH="${STATS_PATH}"

python -m pytest "${PROJECT_ROOT}/tests/e2e/" "${@:--v}"
TEST_EXIT=$?

echo "--- Done (exit code: ${TEST_EXIT}) ---"
exit ${TEST_EXIT}
