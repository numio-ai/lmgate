---
status: done
---

# Implement Initial Prototype for LMGate

**Date**: 2026-02-16
**Completed**: 2026-02-16

## Context

LMGate is a transparent pass-through proxy that sits between client applications and LLM API providers. It controls access via API key allow-lists and collects usage statistics without modifying API calls. The functional and non-functional specification is at `docs/lmgate specification.md`. The design document is at `docs/lmgate-design-claude.md`.

## Problem

There is no working implementation of LMGate. Client applications currently call LLM providers directly with no centralized access control or usage tracking. This means:

- No visibility into usage patterns (who called what, when, how many tokens)
- No single point of control for LLM API access
- No way to restrict which API keys can access providers

## Goals

Deliver a working LMGate prototype that:

- **Proxies HTTP requests transparently** — Forwards requests from clients to an upstream LLM provider and returns responses unchanged.
- **Supports multiple providers** — Routes requests to OpenAI, Anthropic, Google Vertex AI, or AWS Bedrock based on path prefix.
- **Collects usage statistics** — Captures call metadata, performs best-effort token count extraction, writes append-only JSONL stats.
- **Enforces access control** — Checks API keys against a CSV allow-list, blocks unauthorized requests with 403.
- **Provides configuration via file** — YAML config with environment variable overrides.
- **Includes tests and validation tooling** — 75 tests (unit + integration) covering all core logic.

## Non-Goals

- Per-key permissions or rate limiting
- Dashboard or UI
- Authentication (AuthN)
- Request/response modification
- CI/CD pipeline
- Multi-host deployment
- TLS termination

## Acceptance Criteria

- [x] LMGate starts from a config file and listens on the configured host:port.
- [x] Requests with API keys on the allow-list are forwarded to the upstream and responses are returned unchanged.
- [x] Each proxied request generates a stats record containing: API key (masked), upstream endpoint, timestamp, HTTP status, and token counts (when extractable).
- [x] Stats records are persisted to the configured flat file (JSONL).
- [x] Stats collection failure does not block or delay proxying.
- [x] Token counts are correctly extracted from OpenAI, Anthropic, Google, and Bedrock response payloads.
- [x] Requests with API keys NOT on the allow-list receive a 403 response and are not forwarded.
- [x] Requests with no API key in recognized headers receive a 403 response.
- [x] Unrecognized response formats result in null token counts (no crash, no error response).
- [x] Unit tests pass for: key extraction from headers, allow-list checking, token count parsing for each supported provider format, config loading.
- [x] Integration tests pass exercising the full auth + stats flow via aiohttp test client.
- [x] The proxy can be started and exercised manually with curl for ad-hoc smoke testing.

## Quality Gates

- [x] 75 tests passing (9 allowlist + 14 auth + 22 providers + 10 stats + 6 config + 14 integration)
- [x] Design document walked section-by-section for coverage gaps
- [x] Gap-closing tests added for Google Vertex AI integration and x-api-key endpoint

## Implementation Summary

Built using strict TDD (Red-Green cycle) across 5 steps:

### Step 1: Project skeleton + Docker setup
- `pyproject.toml` with dependencies
- `lmgate/config.py`: YAML + env var config loading
- `nginx/nginx.conf`: basic reverse proxy config
- Both Dockerfiles
- `docker-compose.yaml`
- Verify: containers start and nginx proxies a request (no auth, no stats)

### Step 2: AuthZ — allow-list + /auth endpoint
- `lmgate/allowlist.py`: CSV loading, polling, atomic reload
- `lmgate/auth.py`: key extraction (Bearer, x-api-key, SigV4)
- `lmgate/server.py`: `/auth` and `/health` endpoints
- nginx `auth_request` directive
- `nginx/scripts/auth.js`: subrequest callout
- `test_auth.py`, `test_allowlist.py`
- Verify: authorized requests pass, unauthorized return 403

### Step 3: Stats collection — njs POST + Python /stats endpoint
- `nginx/scripts/stats.js`: response body accumulation + POST to `/stats`
- `lmgate/stats.py`: `/stats` endpoint, entry accumulation, JSONL flush
- `lmgate/providers.py`: token extraction per provider
- `test_stats.py`, `test_providers.py`
- Verify: proxied requests produce stats entries in JSONL

### Step 4: Integration tests
- `tests/integration/test_proxy.py`: full flow via aiohttp test client
- End-to-end verification of auth + proxying + stats

### Step 5: Polish
- Graceful shutdown (on_cleanup flush)
- Config loading tests
- Logging configuration
- Example config and allow-list files
