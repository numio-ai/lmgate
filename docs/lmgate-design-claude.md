# LMGate MVP — Design Document

**Date**: 2026-02-16
**Input**: `docs/lmgate specification.md`

---

## 1. Architecture Overview

LMGate is a two-process system deployed as Docker containers via docker-compose.

```
                         ┌─────────────────────────────────────────┐
                         │              nginx + njs                │
  Client ──HTTP/1.1───►  │                                         │
         ◄────────────   │  auth_request ──► LMGate /auth          │
                         │                                         │
                         │  proxy_pass ────► LLM Provider API      │
                         │                                         │
                         │  njs: accumulate response body          │
                         │  njs: POST stats ──► LMGate /stats      │
                         └─────────────────────────────────────────┘

                         ┌─────────────────────────────────────────┐
                         │              LMGate (Python)            │
                         │                                         │
                         │  /auth endpoint (AuthZ decisions)       │
                         │  /stats endpoint (usage data collection)│
                         │  /health endpoint (readiness probe)     │
                         │  allow-list loader (CSV, poll reload)   │
                         └─────────────────────────────────────────┘
```

**Process 1 — nginx + njs**: Reverse proxy handling all client traffic. Delegates AuthZ to LMGate via `auth_request`. njs accumulates response bodies and POSTs combined request metadata + response body to LMGate `/stats` endpoint after the response completes.

**Process 2 — LMGate (Python)**: Single async process (aiohttp) exposing a REST API with two endpoints: `/auth` (AuthZ decisions) and `/stats` (usage data collection). Parses provider responses, extracts token counts, and writes append-only JSONL stats records.

### 1.1 Design Principles

- **Maximize reuse**: nginx handles proxying, HTTP/2 (post-MVP), TLS, SSE streaming — no custom proxy code
- **Minimal new development**: njs scripts are thin glue (~15 lines each); all business logic lives in Python
- **Uniform REST interface**: nginx communicates with LMGate exclusively via HTTP (`/auth`, `/stats`) — consistent, debuggable, no shared filesystem for data exchange
- **Fail closed for AuthZ**: if LMGate is unreachable, nginx returns 403
- **Fail open for stats**: if stats POST fails, proxying continues unaffected
- **Single-host deployment**: docker-compose on one machine for MVP

### 1.2 Protocol Support

| Protocol | MVP | Post-MVP |
|----------|-----|----------|
| HTTP/1.1 | Yes | Yes |
| SSE (streaming) | Yes (native nginx) | Yes |
| HTTP/2 (client-facing) | No | Yes (nginx native, config-only change) |
| AWS EventStream | Yes (transparent byte streaming) | Yes |
| AWS SigV4 passthrough | Yes (headers/body untouched) | Yes |
| gRPC | Out of scope | Out of scope |

Post-MVP HTTP/2: nginx natively terminates HTTP/2 from clients and proxies upstream over HTTP/1.1. No application changes required — configuration only.

---

## 2. Request Flow

Clients call LMGate with a provider prefix. nginx routes based on prefix and strips it before proxying.

Example (configurable):
- `/openai/*` → `https://api.openai.com/*`
- `/anthropic/*` → `https://api.anthropic.com/*`
- `/google/*` → `https://aiplatform.googleapis.com/*`
- `/bedrock/*` → `https://bedrock-runtime.<region>.amazonaws.com/*`

`provider` is derived from the matched prefix.


### 2.1 Happy Path (Authorized, Non-Streaming)

```
1.  Client sends request to `https://lmgate/<provider>/<path>`.
2.  nginx matches location, issues auth_request to LMGate /auth
3.  LMGate /auth extracts API key from Authorization header
4.  LMGate looks up key in allow-list → found
5.  LMGate returns 200 + X-LMGate-ID header (internal ID)
6.  nginx proceeds with proxy_pass to upstream provider
7.  Upstream returns response
8.  njs js_body_filter accumulates response body into variable
9.  nginx streams response to client unchanged
--- client interaction complete ---
10. njs POSTs combined data (request metadata + response body) to LMGate /stats
11. LMGate parses response, extracts tokens, writes JSONL stats entry.

```

### 2.2 Rejected Request

Steps 1-3 same. At step 4, key not in allow-list → LMGate returns 403 → nginx returns 403 to client. No upstream connection.

### 2.3 Streaming Response (SSE)

Same as 2.1 through step 6. nginx streams SSE chunks to client as they arrive. njs accumulates the full streamed body. After streaming completes, njs POSTs to `/stats` as usual. Token counts are typically in the final event (`data: [DONE]` or `message_stop`). Best-effort extraction — if not found, stats entry has null token counts.

### 2.4 AWS SigV4 Requests

Same flow. nginx passes all headers and body unchanged — SigV4 integrity is preserved because nginx does not modify the signed payload. Key extraction: LMGate parses Access Key ID from the `Authorization: AWS4-HMAC-SHA256 Credential=<AKID>/...` header.

---

## 3. Component Design

### 3.1 nginx Reverse Proxy

**Responsibilities:**
- Terminate HTTP/1.1 and HTTP/2.
- Perform `auth_request` to LMGate `/auth` before proxying
- Routes requests by path prefix to upstream LLM providers.
- Proxy requests/responses unchanged (preserve SigV4).
- Stream responses back to clients (including SSE, EventStream)
- After response completes: run njs body tee to send POSTs request + response body to LMGate `/stats`

**Key nginx directives:**
- `auth_request /auth` — subrequest to LMGate
- `proxy_pass` — to upstream provider
- `js_body_filter` — njs response body accumulation
- njs `ngx.fetch()` — POST stats to LMGate after response completes

**Fail-closed behavior:** `auth_request` returns 200 (allow) or 403 (deny). If LMGate is unreachable, nginx treats it as an error and returns 403 to the client.

### 3.2 njs Scripts

Two thin scripts, deliberately limited to glue logic with no business decisions.

**`auth.js`** — Auth subrequest callout:
- Forwards relevant headers (Authorization, x-api-key) to the LMGate `/auth` endpoint
- Returns LMGate's response status to nginx

**`stats.js`** — Response body accumulation + stats POST:
**Responsibilities:**
- Copy response body chunks without blocking client streaming.
- Enforce a **2 MB cap** on copied data.
- If cap exceeded, stop capture and mark token counts as `unknown`.
- POST a metadata envelope + captured body to LMGate `/stats`.

- Uses `js_body_filter` to accumulate response body chunks into a variable
- On the last chunk, fires `ngx.fetch()` POST to LMGate `/stats` with a JSON payload
- The POST is fire-and-forget — does not block the response to the client
- Does NOT parse, interpret, or make decisions about the response content
njs does **not** parse or interpret JSON; it only forwards bytes and metadata.

**Stats POST payload** (sent by njs to LMGate `/stats`):
```json
{
  "timestamp": "2026-02-16T12:00:00+00:00",
  "client_ip": "10.0.0.1",
  "method": "POST",
  "uri": "/v1/chat/completions",
  "host": "api.openai.com",
  "status": 200,
  "auth_key_header": "Bearer sk-abc123...xyz",
  "auth_x_api_key": "",
  "lmgate_internal_id": "1",
  "response_body": "{...full response JSON...}"
}
```

The `lmgate_internal_id` is returned by LMGate in a response header during `auth_request`, so nginx can include it in the stats POST without LMGate needing to correlate the request later.

### 3.3 LMGate (Python)

Single aiohttp async process exposing a REST API.
- `/auth` for AuthZ decisions
- `/stats` for usage collection
- `/healthz` for readiness

Stats ingestion is async with a bounded in-memory queue; overflow drops stats but never blocks proxying.

#### 3.3.1 AuthZ Endpoint (`/auth`)

**Request flow:**
1. nginx sends `auth_request` with original client headers.
2. LMGate extracts the first valid credential using this precedence:
   - `Authorization: Bearer <key>`
   - `Authorization: AWS4-HMAC-SHA256 Credential=<AccessKeyId>/...` (extract Access Key ID)
   - `x-api-key`
3. LMGate checks the key in the in-memory allow-list.
4. If allowed, returns 200 with `X-LMGate-ID` (internal key ID).
5. If missing, invalid, or not found, returns 403.

#### 3.3.2 Allow-List Management

**File format:** CSV with headers:
```
id,api_key,owner,added
1,sk-abc123...xyz,team-alpha,2025-01-15
2,AKIA...,team-beta,2025-02-01
```

- `id` — internal identifier used in logs and `X-LMGate-ID`
- `api_key` — key used for matching
- `owner` — human-readable owner label
- `added` — date the key was added

**Loading behavior:**
- Load at startup; missing/malformed file fails closed and logs FATAL.
- Check file mtime every 30 seconds.
- On change, reload full file and atomically swap in-memory state.
- In-memory structure: `dict[str, AllowListEntry]` keyed by `api_key` for O(1) lookup.

#### 3.3.3 Stats Endpoint (`/stats`)

**Request flow:**
1. njs POSTs JSON payload with request metadata + response body
2. LMGate detects provider from `host` field (e.g., `api.openai.com` → OpenAI)
3. Parses `response_body` to extract token counts
4. Accumulates stats entry in memory
5. Returns 200 immediately (processing is fast; no async offload needed)

**Provider-specific token extraction:**
- Parse `response_body` JSON based on detected provider

| Provider | Input tokens field | Output tokens field |
|----------|--------------------|---------------------|
| OpenAI | `usage.prompt_tokens` | `usage.completion_tokens` |
| Anthropic | `usage.input_tokens` | `usage.output_tokens` |
| Google Vertex AI | `usageMetadata.promptTokenCount` | `usageMetadata.candidatesTokenCount` |
| AWS Bedrock | `usage.inputTokens` | `usage.outputTokens` |

- **SSE/streaming responses**: njs accumulates the full response. Token counts are typically in the final event. Best-effort extraction — if not found, log with null token counts
- **Graceful fallback**: if response body is not JSON or fields are missing, log the entry with null token counts. Never fail the stats daemon on a parse error

**Stats output format:** append-only JSONL:
```json
{"timestamp":"2025-06-15T10:30:00Z","request_id":"req-123","lmgate_id":"1","provider":"openai","endpoint":"/v1/chat/completions","model":"gpt-4","status":200,"duration_ms":420,"input_tokens":150,"output_tokens":80,"bytes_in":1024,"bytes_out":8492,"masked_key":"sk-abc...xyz","error_type":null}
```

- `lmgate_id` — internal ID from allow-list (primary identifier for the caller)
- `masked_key` — last 6 characters of API key, for debugging only
- `input_tokens`, `output_tokens` — `null` if extraction failed
- `error_type` — nullable parse/capture error classification (for diagnostics only)

**Write behavior and rotation:**
- Buffered async writes from the in-memory queue
- Flush interval configurable (default 10s)
- Size-based rotation (configurable); rotated file gets a timestamp suffix
- On shutdown: flush remaining buffered entries

---

## 4. Configuration

### 4.1 Requirements

- **YAML config file** as primary configuration source
- **Environment variable overrides**: env vars can override any setting from the YAML file
- **Env var prefix**: `LMGATE_` to avoid collisions
- **Nesting convention**: double underscore for nested keys (e.g., `LMGATE_AUTH__POLL_INTERVAL_SECONDS`)

Library choice deferred to implementation. Candidates: `dynaconf`, `pydantic-settings`, `omegaconf`, or manual `PyYAML` + env var layer.

### 4.2 Config File: `config/lmgate.yaml`

```yaml
server:
  port: 8081

auth:
  allowlist_path: /data/allowlist.csv
  poll_interval_seconds: 30

stats:
  output_path: /data/stats.jsonl
  flush_interval_seconds: 10

logging:
  level: INFO
```

### 4.3 Environment Variable Override Examples

- `LMGATE_SERVER__PORT=9090` overrides `server.port`
- `LMGATE_AUTH__POLL_INTERVAL_SECONDS=60` overrides `auth.poll_interval_seconds`

### 4.4 nginx Configuration

`nginx/nginx.conf` is a separate file, not managed by the Python config system. Deployment-specific values (ports, upstream timeouts) are set via environment variables in docker-compose.

---

## 5. Project Structure

```
lmgate/
├── nginx/
│   ├── nginx.conf              # proxy config, upstream routing
│   ├── Dockerfile              # nginx:alpine + njs module
│   └── scripts/
│       ├── auth.js             # auth_request callout
│       └── stats.js            # response body accumulation + POST to /stats
├── lmgate/
│   ├── Dockerfile              # python:3.12-slim + dependencies
│   ├── __main__.py             # entry point: start aiohttp server
│   ├── config.py               # YAML + env var config loading
│   ├── server.py               # aiohttp app: /auth, /stats, /health endpoints
│   ├── auth.py                 # key extraction, allow-list lookup
│   ├── allowlist.py            # CSV loading, polling, atomic reload
│   ├── stats.py                # stats ingestion, token extraction, JSONL writes + rotation
│   └── providers.py            # provider detection, per-provider response parsing
├── config/
│   └── lmgate.yaml             # default configuration
├── data/                       # mounted volume (runtime)
│   ├── allowlist.csv           # API key allow-list
│   └── stats.jsonl             # usage statistics output
├── scripts/                    # development, testing, operations scripts
├── docker-compose.yaml         # nginx + lmgate services, shared volumes
├── tests/
│   ├── unit/
│   │   ├── test_auth.py        # key extraction, allow-list lookup
│   │   ├── test_allowlist.py   # CSV loading, reload, edge cases
│   │   ├── test_stats.py       # stats ingestion, JSONL writes + rotation
│   │   └── test_providers.py   # token extraction per provider format
│   └── integration/
│       └── test_proxy.py       # full flow: docker-compose + HTTP requests
├── pyproject.toml
└── README.md
```

---

## 6. Deployment

### 6.1 docker-compose.yaml

**Services:**

| Service | Image | Ports | Volumes |
|---------|-------|-------|---------|
| nginx | `lmgate-nginx` (built from `nginx/Dockerfile`) | `8080:80` (client-facing) | `./config`, `./data` |
| lmgate | `lmgate-app` (built from `lmgate/Dockerfile`) | none (internal only) | `./config`, `./data` |

**Shared volume:** `./data/` is mounted into both containers for allow-list and stats CSV.

**Networking:** Both services on the same Docker network. nginx reaches LMGate at `http://lmgate:8081/auth` and `http://lmgate:8081/stats`.

**Startup order:** LMGate starts first (dependency). nginx starts after LMGate is healthy (`/health` endpoint).

### 6.2 Dockerfiles

**`nginx/Dockerfile`:**
- Base: `nginx:alpine` (install njs module via `apk add nginx-module-njs`)
- Copy `nginx.conf` and `scripts/`

**`lmgate/Dockerfile`:**
- Base: `python:3.12-slim`
- Install dependencies from `pyproject.toml`
- Copy `lmgate/` source

---

## 7. Testing Strategy

### 7.1 Unit Tests (pytest)

| Module | Coverage |
|--------|----------|
| `auth.py` | Key extraction from Authorization (Bearer, SigV4), x-api-key; missing key handling |
| `allowlist.py` | CSV load, malformed file handling, reload on change, atomic swap |
| `stats.py` | Stats ingestion, JSONL writes + rotation, graceful handling of malformed data |
| `providers.py` | Token extraction for OpenAI, Anthropic, Google, AWS response formats; streaming responses; missing fields |

### 7.2 Integration Tests

- Spin up docker-compose (nginx + LMGate)
- Send HTTP requests through nginx with valid/invalid API keys
- Verify: AuthZ accept (200), AuthZ deny (403), response passthrough unchanged
- Verify: stats CSV populated by LMGate after proxied requests
- Verify: SSE streaming responses pass through correctly

### 7.3 No Separate njs Tests

njs scripts are thin glue. Their correctness is verified by integration tests that exercise the full request flow. No separate njs unit test framework is needed.

---

## 8. Post-MVP: HTTP/2 Client-Facing

Enable HTTP/2 by adding to `nginx.conf`:
```
listen 443 ssl http2;
```

nginx terminates HTTP/2 from clients and proxies upstream over HTTP/1.1. No changes to LMGate or njs scripts. This is a configuration-only change.

---

## 9. Implementation Order

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
- `lmgate/stats.py`: `/stats` endpoint, entry accumulation, CSV flush
- `lmgate/providers.py`: token extraction per provider
- `test_stats.py`, `test_providers.py`
- Verify: proxied requests produce stats entries in CSV

### Step 4: Integration tests
- `tests/integration/test_proxy.py`: full flow via docker-compose
- End-to-end verification of auth + proxying + stats

### Step 5: Polish
- Graceful shutdown
- Logging configuration
- Example config and allow-list files

---

## 10. Open Items (Out of Scope for MVP)

- TLS termination (nginx config, certificate management)
- Log rotation for stats JSONL
- Dashboard / stats query API
- Multi-host / HA deployment
- Rate limiting
- Per-key permissions (beyond allow/deny)
