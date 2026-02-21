---
status: done
---

# Add E2E Tests Against Real LLM APIs

**Date**: 2026-02-16

## Context

LMGate's test suite currently has two layers:
- **Unit tests**: individual Python components in isolation
- **Integration tests**: Python app endpoints (`/auth`, `/stats`) via `aiohttp_client`, no external systems

The Docker Compose e2e suite (task `20260216_01_add_e2e_docker_integration_tests`) validates nginx + njs + lmgate with a mock upstream. That confirms the plumbing works, but it does not confirm that real LLM provider responses are parsed correctly — specifically, that token counts and model names are extracted accurately from actual API response payloads.

This task adds a real-API e2e test suite that runs the full stack against OpenAI and Anthropic.

**Prerequisite**: Task `20260216_01_add_e2e_docker_integration_tests` (Docker Compose e2e with mock upstream) must be complete before this task is executed.

## Problem

There is no automated test that sends a real request through the full LMGate stack (nginx → LLM provider → njs → lmgate `/stats`) and asserts that the resulting JSONL entry contains correct provider, model, and token count data.

Without this, a regression in provider-specific stats parsing (e.g. a response schema change from OpenAI or Anthropic) would not be caught until production.

**Cost of inaction**: Silent stats corruption — JSONL records with null or incorrect token counts — would go undetected.

## Goals

- A `tests/e2e/` pytest suite that:
  - Starts the full Docker Compose stack (nginx + njs + lmgate)
  - Sends one real HTTP request through nginx to OpenAI (`gpt-4o-mini`)
  - Sends one real HTTP request through nginx to Anthropic (`claude-haiku-3`)
  - After each request, reads the JSONL stats file and asserts the entry is correct
  - Tears down the stack after the suite completes

## Non-Goals

- Testing mock upstreams (covered by `20260216_01_add_e2e_docker_integration_tests`)
- Testing auth rejection flows (covered by existing integration tests)
- Load or volume testing
- Testing any other provider (AWS Bedrock, Google Vertex) — may be added later
- CI integration — local execution only at this stage

## Constraints & Assumptions

- Requires Docker and Docker Compose
- API keys are sourced from a `.env` file at the repo root (not committed); tests skip gracefully if keys are absent
- Models: `gpt-4o-mini` (OpenAI), `claude-haiku-3` (Anthropic) — cheapest available options to minimise cost per test run
- Requests must be minimal: single-turn, short prompt, short expected response
- Tests must clean up after themselves (docker compose down, volumes removed)
- The `.env` file format and variable names must be documented

## Acceptance Criteria

- [ ] `tests/e2e/` directory exists with a pytest suite runnable via a single command
- [ ] Test for OpenAI: sends a real request through nginx to `api.openai.com`, asserts JSONL entry contains `provider=openai`, non-empty `model`, `input_tokens > 0`, `output_tokens > 0`
- [ ] Test for Anthropic: sends a real request through nginx to `api.anthropic.com`, asserts JSONL entry contains `provider=anthropic`, non-empty `model`, `input_tokens > 0`, `output_tokens > 0`
- [ ] Tests are skipped (not failed) if `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` are absent from the environment
- [ ] Docker Compose stack is started before the suite and torn down after, regardless of test outcome
- [ ] All existing unit and integration tests continue to pass (no regressions)
- [ ] `.env.example` file documents required variables

## Validation Steps

1. Copy `.env.example` to `.env` and populate with real API keys
2. Run the e2e suite: `pytest tests/e2e/ -v` (or via a dedicated script)
3. Confirm both OpenAI and Anthropic tests pass
4. Inspect `data/stats.jsonl` inside the container to verify entries manually
5. Run `docker compose down -v` and confirm cleanup
6. Remove API keys from `.env` and re-run — confirm tests are skipped, not errored
7. Run full suite: `pytest tests/` — confirm all existing tests still pass

## Risks & Rollback

- **Risk**: OpenAI or Anthropic response schema changes between now and execution. Mitigation: tests assert field presence and type, not exact values.
- **Risk**: API call cost accumulation if tests are run frequently. Mitigation: minimal prompts, cheapest models; tests are not wired to CI by default.
- **Risk**: Network flakiness causes intermittent failures. Mitigation: single retry on connection error; test marked as `xfail` on timeout rather than hard fail.
- **Rollback**: Delete `tests/e2e/` directory. No impact on existing tests or production code.
