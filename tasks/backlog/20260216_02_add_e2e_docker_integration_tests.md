---
status: backlog
---

# Add End-to-End Docker Integration Tests

**Date**: 2026-02-16

## Context

LMGate was implemented using strict TDD with 75 passing tests. However, all "integration" tests use `aiohttp_client` to test the Python endpoints directly. No tests exercise the full deployment stack: nginx receiving a request, issuing an `auth_request` to LMGate, proxying to an upstream, njs accumulating the response body, and POSTing stats back to LMGate.

## Problem

The current test suite validates the Python service in isolation but does not verify the nginx + njs + LMGate integration. This means:

- nginx routing configuration (`nginx.conf`) is untested — a misconfigured `proxy_pass` or `auth_request` directive would not be caught.
- njs scripts (`stats.js`, `auth.js`) are untested — a JavaScript error in body accumulation or stats POST would not be caught.
- The `docker-compose.yaml` health check and startup ordering are untested.
- The response body accumulation + fire-and-forget stats flow (nginx → njs → LMGate `/stats`) is not exercised end-to-end.

**Cost of inaction**: Configuration regressions in nginx or njs will only be discovered during manual testing or in production. The njs layer is particularly fragile because it has no unit test framework — end-to-end tests are the only way to validate it.

## Goals

- Automated tests that bring up the full Docker Compose stack (nginx + LMGate), send HTTP requests through nginx, and verify:
  - Authorized requests are proxied and responses are returned
  - Unauthorized requests are rejected with 403
  - Stats records are written to the JSONL file after proxied requests
- Tests can run in CI or locally with `docker compose`.

## Non-Goals

- Testing against real LLM provider APIs (use a mock upstream instead).
- Load testing or performance benchmarking.
- Testing TLS termination (out of scope for MVP).
- Replacing the existing unit/integration tests — the new tests are additive.

## Constraints & Assumptions

- Tests require Docker and Docker Compose to be available.
- A mock upstream HTTP server is needed to simulate LLM provider responses (can be a simple Python HTTP server or a container).
- Tests must clean up after themselves (stop containers, remove volumes).
- Test execution time should be reasonable (under 60 seconds for the full e2e suite).

## Acceptance Criteria

- [ ] A test script or pytest suite exists that starts the Docker Compose stack, runs e2e tests, and tears it down.
- [ ] Tests verify: authorized request passes through nginx to the mock upstream and response is returned unchanged.
- [ ] Tests verify: unauthorized request (invalid key) returns 403 from nginx without reaching the upstream.
- [ ] Tests verify: after a proxied request completes, a stats entry appears in `data/stats.jsonl` with the correct provider, endpoint, and status.
- [ ] Tests verify: the Docker health check passes and nginx starts only after LMGate is healthy.
- [ ] All existing 75 tests continue to pass.

## Validation Steps

1. Run the e2e test suite: `./scripts/run-e2e-tests.sh` (or equivalent).
2. Verify all e2e tests pass.
3. Run the existing unit/integration suite: `pytest tests/`. Verify all 75 tests still pass.
4. Run `docker compose down -v` to confirm cleanup is complete.

## Risks & Rollback

- **Risk**: Docker-in-CI may have networking constraints. Mitigation: test locally first; CI integration is a separate concern.
- **Risk**: Flaky tests due to container startup timing. Mitigation: use health check polling with retries before sending test requests.
- **Rollback**: Remove the e2e test files and script. No impact on existing tests.
