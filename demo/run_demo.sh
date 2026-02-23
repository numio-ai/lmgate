#!/usr/bin/env bash
# Run the LMGate demo and print the resulting stats entry.
#
# Usage:
#   ./demo/run_demo.sh <anthropic-api-key>
#
# The script:
#   1. Calls demo.py with the provided key
#   2. Waits for the stats flush interval (15 s)
#   3. Prints the last entry from data/stats.jsonl

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
STATS_FILE="${REPO_ROOT}/data/stats.jsonl"
FLUSH_WAIT=15

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <anthropic-api-key>" >&2
    exit 1
fi

API_KEY="$1"

echo "==> Sending request through LMGate..."
python "${SCRIPT_DIR}/demo.py" --api-key "${API_KEY}"
EXIT_CODE=$?

if [[ ${EXIT_CODE} -ne 0 ]]; then
    echo ""
    echo "==> Request was not forwarded to the provider (blocked or error). No stats entry expected."
    exit ${EXIT_CODE}
fi

echo ""
echo "==> Waiting ${FLUSH_WAIT}s for stats flush..."
sleep "${FLUSH_WAIT}"

echo ""
echo "==> Last stats entry from ${STATS_FILE}:"
if [[ ! -f "${STATS_FILE}" ]]; then
    echo "    (stats file not found — no entries have been written yet)"
    exit 0
fi

# Print the last line; pipe through jq if available for readability
if command -v jq &>/dev/null; then
    tail -n 1 "${STATS_FILE}" | jq .
else
    tail -n 1 "${STATS_FILE}"
fi
