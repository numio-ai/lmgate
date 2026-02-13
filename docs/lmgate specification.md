# LMGate — Functional & Non-Functional Specification

## 1. Overview

LMGate is a transparent pass-through proxy that sits between client applications and LLM API providers. It controls access and collects usage statistics without modifying or interpreting API calls.

LMGate is designed so that client applications require minimal changes to adopt it — they simply point their LLM SDK base URL at LMGate instead of directly at the provider. LMGate handles authorization, forwards the request unchanged, and silently collects usage data on the way back.

## 2. Architecture Summary

LMGate is a two-process system:

1. **nginx + njs** — Reverse proxy handling all client traffic. Performs authorization checks before proxying, and collects response metadata after proxying.
2. **LMGate Python service** — Async REST API (aiohttp) that makes authorization decisions and ingests usage statistics.

```
Client ──HTTP──► nginx ──auth_request──► LMGate /auth
                  │                         │
                  │◄── 200 (allow) ─────────┘
                  │
                  ├──proxy_pass──► LLM Provider API
                  │◄── response ──┘
                  │
                  ├── stream response to client
                  │
                  └── njs POST ──► LMGate /stats (fire-and-forget)
```

Both processes run as Docker containers via docker-compose on a single host.

## 3. Supported Providers

| Provider | Host | Path Prefix |
|----------|------|-------------|
| OpenAI | `api.openai.com` | `/openai/` |
| Anthropic | `api.anthropic.com` | `/anthropic/` |
| Google Vertex AI | `aiplatform.googleapis.com` | `/google/` |
| AWS Bedrock | `bedrock-runtime.<region>.amazonaws.com` | `/bedrock/` |

Clients call LMGate using the provider path prefix. nginx strips the prefix and proxies to the real provider host. For example, a request to `http://lmgate:8080/openai/v1/chat/completions` is proxied to `https://api.openai.com/v1/chat/completions`.

## 4. Functional Requirements

### 4.1 Transparent Proxying

- Forward HTTP requests from clients to LLM provider endpoints unchanged.
- Return provider responses to clients unchanged.
- Preserve all headers and body content — SigV4 signed requests pass through intact.
- Support SSE streaming: nginx streams response chunks to the client as they arrive, with no buffering delay.
- The njs layer accumulates response body (up to 2 MB) for stats extraction without blocking client streaming.

### 4.2 Access Control (AuthZ)

LMGate extracts the API key from each incoming request and checks it against a file-based allow-list. Requests with valid keys are forwarded; all others are rejected with HTTP 403.

**Key extraction precedence** (first valid match wins):

1. `Authorization: Bearer <key>` — Used by OpenAI, Anthropic, Google
2. `Authorization: AWS4-HMAC-SHA256 Credential=<AccessKeyId>/...` — Used by AWS Bedrock (Access Key ID is extracted)
3. `x-api-key` header — Alternative header supported by some providers

**Behavior rules:**
- Missing key → 403
- Key not in allow-list → 403
- LMGate service unreachable → 403 (fail closed)
- On successful auth, LMGate returns an internal ID via `X-LMGate-ID` header for correlation in stats

### 4.3 Allow-List Management

The allow-list is a CSV file with four required columns:

```
id,api_key,owner,added
1,sk-abc123...xyz,team-alpha,2025-01-15
2,AKIA...,team-beta,2025-02-01
```

| Column | Purpose |
|--------|---------|
| `id` | Internal identifier, used in stats records and `X-LMGate-ID` header |
| `api_key` | The full API key string to match against |
| `owner` | Human-readable owner label |
| `added` | Date the key was added to the list |

**Loading behavior:**
- Loaded at startup. Missing or malformed file causes a fatal startup error.
- File mtime is polled every 30 seconds (configurable).
- On change, the full file is reloaded and the in-memory lookup table is atomically swapped.
- In-memory structure: hash map keyed by `api_key` for O(1) lookup.

### 4.4 Usage Statistics

LMGate collects metadata from every proxied request and writes it to an append-only JSONL file.

**Data captured per request:**

| Field | Description |
|-------|-------------|
| `timestamp` | ISO-8601 timestamp of the request |
| `lmgate_id` | Internal ID from the allow-list |
| `provider` | Detected provider name (openai, anthropic, google, bedrock, unknown) |
| `endpoint` | Request URI path |
| `model` | Model name extracted from response (if available) |
| `status` | HTTP response status code |
| `input_tokens` | Input/prompt token count (null if extraction failed) |
| `output_tokens` | Output/completion token count (null if extraction failed) |
| `masked_key` | Last 6 characters of the API key (for debugging) |
| `error_type` | Error classification (null on success) |

**Token extraction by provider:**

| Provider | Input tokens field | Output tokens field |
|----------|--------------------|---------------------|
| OpenAI | `usage.prompt_tokens` | `usage.completion_tokens` |
| Anthropic | `usage.input_tokens` | `usage.output_tokens` |
| Google Vertex AI | `usageMetadata.promptTokenCount` | `usageMetadata.candidatesTokenCount` |
| AWS Bedrock | `usage.inputTokens` | `usage.outputTokens` |

**SSE/streaming responses:** The njs layer accumulates the complete streamed response body. Token counts are typically found in the final SSE event. Best-effort extraction — if not found, the stats entry records null token counts.

**Graceful fallback:** If the response body is not JSON, fields are missing, or the body exceeds the 2 MB capture limit, the stats entry is written with null token counts. Stats errors never cause request failures.

**Write behavior:**
- Entries are buffered in memory and flushed to disk periodically (default 10 seconds, configurable).
- Size-based rotation: when the file exceeds 100 MB, it is renamed with a timestamp suffix and a new file is started.
- On graceful shutdown, remaining buffered entries are flushed.

### 4.5 Health Check

LMGate exposes a `/healthz` endpoint that returns HTTP 200 with body `ok`. This is used by docker-compose to gate nginx startup on LMGate readiness.

## 5. Configuration

### 5.1 Configuration Sources

Configuration is loaded from two sources, with environment variables taking precedence:

1. **YAML config file** (`config/lmgate.yaml`) — Primary configuration source
2. **Environment variables** — Override any YAML setting using the `LMGATE_` prefix

### 5.2 Default Configuration

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

### 5.3 Environment Variable Overrides

Environment variables use double underscore (`__`) for nested keys:

- `LMGATE_SERVER__PORT=9090` overrides `server.port`
- `LMGATE_AUTH__POLL_INTERVAL_SECONDS=60` overrides `auth.poll_interval_seconds`
- `LMGATE_LOGGING__LEVEL=DEBUG` overrides `logging.level`

Values are automatically coerced to the appropriate type (boolean, integer, float, or string).

## 6. Protocol Support

| Protocol | Status |
|----------|--------|
| HTTP/1.1 | Supported |
| SSE (streaming) | Supported (native nginx streaming) |
| AWS EventStream | Supported (transparent byte streaming) |
| AWS SigV4 passthrough | Supported (headers/body untouched) |
| HTTP/2 (client-facing) | Post-MVP (nginx config-only change) |
| gRPC | Out of scope |

## 7. Non-Functional Requirements

- **Latency**: Near-zero overhead on proxied calls. Authorization is a single in-memory lookup. Stats collection is asynchronous (fire-and-forget POST from njs).
- **Throughput**: Designed for up to 100 requests per second.
- **Availability**: AuthZ failure blocks calls (fail closed). Stats failure does not affect proxying (fail open).
- **Deployment**: Single-host Docker Compose deployment for MVP.
- **Security**: API keys in stats are masked to last 6 characters. Full keys exist only in the allow-list file and in transit.

## 8. Out of Scope (MVP)

- TLS termination (planned as nginx configuration change)
- Dashboard or stats query API
- Multi-host / HA deployment
- Rate limiting
- Per-key permissions beyond allow/deny
- Request/response modification
- Authentication (AuthN) — LMGate performs authorization only
