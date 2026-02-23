---
status: done
---

# Demo Application: LMGate Quick-Start Example

**Date:** 2026-02-22

## Context

LMGate is a transparent proxy that monitors and controls LLM API usage. The README shows curl-based examples, but there is no runnable Python application demonstrating how a real app integrates with LMGate and how usage data appears in `data/stats.jsonl`.

## Problem

Prospective users lack a concrete, runnable example that shows:
- How a Python application routes calls through LMGate instead of going directly to the provider
- What happens when an authorized key is used (success path)
- What happens when an unauthorized key is used (blocked path)
- How usage statistics are captured in `data/stats.jsonl`

## Goals

- Provide a minimal Python demo script (`demo/`) that calls the Anthropic API via LMGate
- Provide a shell wrapper script that runs the demo and prints the resulting stats entry
- Accept the API key as a CLI argument so the same script demonstrates both the success and blocked scenarios
- Provide `demo/README.md` with setup prerequisites and usage instructions

## Non-Goals

- Multi-provider demo (OpenAI, Google) — Anthropic only
- Interactive UI or web interface
- Automated test coverage of the demo itself
- Modifying the LMGate core codebase

## Constraints & Assumptions

- LMGate must be running locally (`docker compose up -d`) before the demo is executed; the demo does not start it
- A valid Anthropic API key must be present in `data/allowlist.csv`; the demo does not manage the allow-list
- The demo targets the local LMGate instance at `http://localhost:8080/anthropic`
- Python 3.12+ and the `anthropic` SDK must be available in the demo environment
- Stats flush interval is 10 seconds (default); the shell wrapper must account for this when waiting

## Acceptance Criteria

- AC1: `demo/` directory exists with: `demo.py`, `run_demo.sh`, `README.md`, and `requirements.txt`
- AC2: `demo.py` accepts an Anthropic API key as a CLI argument and sends one message through LMGate using the `anthropic` Python SDK
- AC3: When a valid (allow-listed) key is passed, the script prints the LLM response to stdout
- AC4: When an invalid (blocked) key is passed, the script prints a clear error indicating the request was rejected (HTTP 403)
- AC5: `run_demo.sh` invokes `demo.py` with the provided key, waits for the stats flush interval, then reads and prints the last entry from `data/stats.jsonl`
- AC6: `demo/README.md` documents: prerequisites (Docker, allow-list setup), how to run the success scenario, how to run the blocked scenario, and what to expect in the output
- AC7: `demo/requirements.txt` lists the `anthropic` package (pinned or minimum version)

## Validation Steps

1. Start LMGate: `docker compose up -d`
2. Confirm running: `curl http://localhost:8080/healthz` → `ok`
3. Add a valid Anthropic key to `data/allowlist.csv`
4. Install demo dependencies: `pip install -r demo/requirements.txt`
5. Run success scenario: `./demo/run_demo.sh <valid-key>` → LLM response printed, stats entry printed from `data/stats.jsonl`
6. Run blocked scenario: `./demo/run_demo.sh sk-ant-fake-key` → 403 error message printed, no new stats entry

## Risks & Rollback

- **Risk:** `data/stats.jsonl` may not exist if no prior calls were made; the shell wrapper must handle this gracefully (e.g., wait and re-check, or print a warning if file is absent)
- **Rollback:** The demo is a self-contained directory with no changes to core code; removal is `rm -rf demo/`
