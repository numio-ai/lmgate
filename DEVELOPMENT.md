# LMGate — Development Guide

## Architecture Overview

LMGate is a two-process system deployed as Docker containers via docker-compose:

- **nginx + njs** — Reverse proxy handling all client traffic. njs scripts trigger auth subrequests and collect response metadata for stats.
- **LMGate Python service (aiohttp)** — Async REST API providing `/auth`, `/stats`, and `/healthz` endpoints.

For the full architecture, request lifecycle, and design rationale, see [docs/LMGate detailed design.md](docs/LMGate%20detailed%20design.md).

For functional requirements and protocol support, see [docs/LMGate functional specification.md](docs/LMGate%20functional%20specification.md).

## Project Structure

```
lmgate/
├── lmgate/                    # Python service
│   ├── __init__.py
│   ├── __main__.py            # Entry point
│   ├── server.py              # aiohttp app setup and route handlers
│   ├── auth.py                # /auth endpoint — key extraction and validation
│   ├── allowlist.py           # CSV allow-list loader with file-polling
│   ├── providers.py           # Provider detection and token extraction
│   ├── stats.py               # /stats endpoint — JSONL writer with buffering/rotation
│   ├── config.py              # YAML config + env var override loading
│   └── Dockerfile
├── nginx/
│   ├── nginx.conf             # Production nginx config (provider routing, proxy_pass)
│   ├── scripts/
│   │   ├── auth.js            # njs: auth subrequest trigger
│   │   └── stats.js           # njs: response body accumulation + stats POST
│   └── Dockerfile
├── config/
│   └── lmgate.yaml            # Default configuration
├── data/
│   └── allowlist.csv          # API key allow-list
├── scripts/
│   ├── run-tests.sh           # Run unit + integration tests
│   ├── run-e2e-integration-tests.sh  # E2E with mock upstream
│   ├── run-e2e-system-tests.sh       # E2E with real APIs
│   └── lmgate-manager.sh
├── tests/                     # See "Testing" section below
├── docs/
│   ├── LMGate functional specification.md
│   ├── LMGate detailed design.md
│   └── LMGate user guide.md
├── docker-compose.yaml        # Production compose file
├── pyproject.toml             # Python project metadata and dependencies
└── uv.lock                    # Dependency lock file
```

## Local Development Setup

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) 
- Docker and Docker Compose 

### Setup

```bash
# Clone
git clone git@github.com:numio-ai/lmgate.git
cd lmgate

# Create venv and install dependencies (using uv)
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

### Dependencies

Runtime dependencies are in `pyproject.toml` under `[project.dependencies]`:
- `aiohttp` — async HTTP server
- `pyyaml` — YAML config parsing

Dev dependencies are under `[project.optional-dependencies.dev]`:
- `pytest`, `pytest-asyncio`, `pytest-aiohttp` — test framework
- `aioresponses` — mock aiohttp requests in tests

## Testing

LMGate has three test layers. Unit and integration tests require only Python; e2e tests require Docker.

### Unit tests

Pure Python tests covering individual modules (allowlist, auth, config, providers, stats):

```bash
python -m pytest tests/unit/ -v
```

### Integration tests

Tests the aiohttp app in-process — no Docker, no network calls:

```bash
python -m pytest tests/integration/ -v
```

### Run both unit and integration

```bash
python -m pytest tests/unit/ tests/integration/ -v
# or
./scripts/run-tests.sh
```

### E2E integration tests (mock upstream)

Runs the full Docker Compose stack (nginx + lmgate + mock upstream). Validates the auth -> proxy -> stats pipeline without real LLM API calls:

```bash
./scripts/run-e2e-integration-tests.sh
```

The script builds the stack, waits for health, runs `tests/e2e/test_e2e_integration.py`, and tears everything down.

### E2E system tests (real APIs)

Runs the full stack with production nginx config and sends real requests to OpenAI and Anthropic:

1. Copy `.env_example` to `.env` and populate with real API keys:

   ```bash
   cp .env_example .env
   # Edit .env with your OPENAI_API_KEY and ANTHROPIC_API_KEY
   ```

2. Run the suite:

   ```bash
   ./scripts/run-e2e-system-tests.sh
   ```

Tests are individually skipped (not failed) if their API key is missing. Uses minimal prompts and cheapest models to minimize cost.

### Test file layout

```
tests/
├── unit/
│   ├── test_allowlist.py
│   ├── test_auth.py
│   ├── test_config.py
│   ├── test_providers.py
│   └── test_stats.py
├── integration/
│   └── test_proxy.py
└── e2e/
    ├── test_e2e_integration.py
    ├── test_e2e_system.py
    ├── docker-compose.e2e-integration.yaml
    ├── docker-compose.e2e-system.yaml
    ├── nginx.e2e-integration.conf
    ├── Dockerfile.mock
    ├── mock_upstream.py
    └── data/
        └── allowlist.csv
```

## Key Design Decisions

- **Two-process architecture**: nginx handles proxying, TLS, and SSE streaming natively. Python handles business logic only (auth + stats). Communication is via HTTP subrequests (`/auth`, `/stats`).
- **Fail closed for auth**: If the Python service is unreachable, nginx returns 403.
- **Fail open for stats**: If the stats POST fails, proxying continues unaffected.
- **njs body accumulation**: njs copies response body chunks (up to 2 MB) without blocking client streaming. It never parses JSON — raw bytes are forwarded to the stats endpoint.
- **File-based allow-list**: CSV polled by mtime every 30s, atomically swapped on change. Simple and requires no database.

## Out of Scope (MVP)

See the detailed list in [docs/LMGate functional specification.md](docs/LMGate%20functional%20specification.md) section 8.
