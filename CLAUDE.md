# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project

LMGate is a transparent pass-through proxy for LLM API providers (OpenAI, Anthropic, Google Vertex AI) with API key allow-list access control and usage statistics collection. Python 3.12+ / aiohttp backend, nginx + njs reverse proxy frontend. Deployed via Docker Compose.

- **User documentation**: `README.md` — installation, configuration, usage
- **Developer documentation**: `DEVELOPMENT.md` — architecture, project structure, local setup, testing
- **Functional specification**: `docs/LMGate functional specification.md`
- **Detailed design**: `docs/LMGate detailed design.md`

## Current State

MVP implemented. Two-process system (nginx + Python service) running in Docker Compose. Unit, integration, and e2e tests in place.

## Tech Stack

- **Python service**: aiohttp async server, PyYAML for config
- **Proxy**: nginx with njs scripts for auth subrequests and stats collection
- **Packaging**: pyproject.toml with setuptools, uv for dependency management
- **Testing**: pytest, pytest-asyncio, pytest-aiohttp, aioresponses

## Key File Paths

| File | Purpose |
|------|---------|
| `lmgate/server.py` | aiohttp app setup, route handlers (`/auth`, `/stats`, `/healthz`) |
| `lmgate/auth.py` | API key extraction from headers, allow-list validation |
| `lmgate/allowlist.py` | CSV loader with mtime-polling and atomic swap |
| `lmgate/providers.py` | Provider detection from hostname, token count extraction per provider |
| `lmgate/stats.py` | JSONL writer with buffered async writes and size-based rotation |
| `lmgate/config.py` | YAML config loading with `LMGATE_` env var overrides |
| `nginx/nginx.conf` | Production nginx config — provider routing, proxy_pass, njs hooks |
| `nginx/scripts/auth.js` | njs: triggers auth subrequest to Python `/auth` |
| `nginx/scripts/stats.js` | njs: accumulates response body (<=2 MB cap), POSTs to `/stats` |
| `config/lmgate.yaml` | Default runtime configuration |
| `data/allowlist.csv` | API key allow-list (CSV: id, api_key, owner, added) |
| `docker-compose.yaml` | Production compose: lmgate (port 8081 internal) + nginx (port 8080 external) |

## Commands

```bash
# Unit + integration tests
python -m pytest tests/unit/ tests/integration/ -v

# E2E with mock upstream (requires Docker)
./scripts/run-e2e-integration-tests.sh

# E2E with real APIs (requires Docker + .env with API keys)
./scripts/run-e2e-system-tests.sh

# Start the full stack
docker compose up -d

# Rebuild after code changes
docker compose up -d --build
```

## Architecture Notes for AI Agents

- nginx communicates with the Python service exclusively via HTTP subrequests (`/auth` before proxying, `/stats` fire-and-forget after response)
- Auth is fail-closed (Python unreachable = 403), stats is fail-open (stats failure doesn't affect proxying)
- njs scripts are thin glue (~15 lines each) — they never parse or modify request/response content
- The allow-list is an in-memory `dict[str, AllowListEntry]` for O(1) lookup, rebuilt atomically on file change
- Stats entries are buffered in-memory, flushed to JSONL on a configurable interval (default 10s), with 100 MB size-based rotation
- Token extraction is provider-specific: OpenAI uses `usage.prompt_tokens`/`usage.completion_tokens`, Anthropic uses `usage.input_tokens`/`usage.output_tokens`, Google uses `usageMetadata.promptTokenCount`/`usageMetadata.candidatesTokenCount`
- SSE streaming: njs accumulates the full response for stats extraction, but response chunks are streamed to the client without buffering delay
