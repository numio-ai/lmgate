# LMGate User Guide

This guide covers how to deploy, configure, and operate LMGate — a transparent proxy for LLM API providers with access control and usage statistics.

## Prerequisites

- Docker and Docker Compose
- Access to at least one LLM provider API (OpenAI, Anthropic, or Google Vertex AI)
- API keys that your client applications will use

## Quick Start

### 1. Prepare the allow-list

Create a CSV file at `data/allowlist.csv` with the API keys you want to authorize:

```csv
id,api_key,owner,added
1,sk-proj-your-openai-key-here,dev-team,2026-02-16
2,sk-ant-your-anthropic-key-here,dev-team,2026-02-16
```

All four columns are required. The `id` field is used internally for correlation in stats records.

### 2. Start LMGate

```bash
docker compose up -d
```

This starts two containers:
- **lmgate** — Python service (port 8081, internal only)
- **nginx** — Reverse proxy (port 8080, client-facing)

nginx waits for lmgate to be healthy before accepting traffic.

### 3. Point your client at LMGate

Configure your LLM client to use LMGate as the base URL. The URL pattern is:

```
http://<lmgate-host>:8080/<provider>/<original-path>
```

**OpenAI example (Python SDK):**

```python
from openai import OpenAI

client = OpenAI(
    api_key="sk-proj-your-openai-key-here",
    base_url="http://localhost:8080/openai/v1"
)

response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello"}]
)
```

**Anthropic example (Python SDK):**

```python
import anthropic

client = anthropic.Anthropic(
    api_key="sk-ant-your-anthropic-key-here",
    base_url="http://localhost:8080/anthropic"
)

message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello"}]
)
```

**curl example (OpenAI):**

```bash
curl http://localhost:8080/openai/v1/chat/completions \
  -H "Authorization: Bearer sk-proj-your-openai-key-here" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4","messages":[{"role":"user","content":"Hello"}]}'
```

### 4. Verify it works

Check that LMGate is running:

```bash
curl http://localhost:8080/healthz
# Expected: ok
```

Send a request with a valid key — you should get the normal provider response. Send a request with an invalid key — you should get HTTP 403.

## Provider Routing

LMGate routes requests by URL path prefix. nginx strips the prefix before forwarding to the provider.

| Path Prefix | Upstream Provider |
|-------------|-------------------|
| `/openai/` | `https://api.openai.com/` |
| `/anthropic/` | `https://api.anthropic.com/` |
| `/google/` | `https://aiplatform.googleapis.com/` |

The request body, headers, and query parameters are forwarded unchanged to the upstream provider.

## Allow-List Management

### File format

The allow-list is a CSV file with these required columns:

| Column | Description |
|--------|-------------|
| `id` | Internal identifier (appears in stats as `lmgate_id`) |
| `api_key` | The full API key to match |
| `owner` | Human-readable label for the key owner |
| `added` | Date the key was added |

### Adding or removing keys

Edit the CSV file directly. LMGate polls the file every 30 seconds (configurable) and automatically reloads when it detects a change. No restart is needed.

```bash
# Add a new key
echo '4,sk-new-key-here,new-team,2026-02-16' >> data/allowlist.csv
```

The reload is atomic — in-flight requests are not affected.

### Key extraction

LMGate extracts the API key from request headers using this precedence:

1. `Authorization: Bearer <key>` — OpenAI, Anthropic, Google
2. `x-api-key` header — Alternative for some providers

The key from the request must match an `api_key` entry in the CSV exactly.

## Configuration

### Config file

The primary configuration file is `config/lmgate.yaml`:

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

### Environment variable overrides

Any setting can be overridden via environment variables with the `LMGATE_` prefix. Use double underscores for nested keys:

| Environment Variable | Overrides |
|---------------------|-----------|
| `LMGATE_SERVER__PORT` | `server.port` |
| `LMGATE_AUTH__ALLOWLIST_PATH` | `auth.allowlist_path` |
| `LMGATE_AUTH__POLL_INTERVAL_SECONDS` | `auth.poll_interval_seconds` |
| `LMGATE_STATS__OUTPUT_PATH` | `stats.output_path` |
| `LMGATE_STATS__FLUSH_INTERVAL_SECONDS` | `stats.flush_interval_seconds` |
| `LMGATE_LOGGING__LEVEL` | `logging.level` |

Set environment variables in `docker-compose.yaml`:

```yaml
services:
  lmgate:
    environment:
      - LMGATE_LOGGING__LEVEL=DEBUG
      - LMGATE_AUTH__POLL_INTERVAL_SECONDS=60
```

## Usage Statistics

### Stats file

LMGate writes usage records to an append-only JSONL file (one JSON object per line). Default location: `data/stats.jsonl`.

Each line contains:

```json
{
  "timestamp": "2026-02-16T12:00:00.000Z",
  "lmgate_id": "1",
  "provider": "openai",
  "endpoint": "/openai/v1/chat/completions",
  "model": "gpt-4",
  "status": 200,
  "input_tokens": 150,
  "output_tokens": 80,
  "masked_key": "y-here",
  "error_type": null
}
```

### Field reference

| Field | Description |
|-------|-------------|
| `timestamp` | ISO-8601 time of the request |
| `lmgate_id` | Internal ID from the allow-list `id` column |
| `provider` | Detected provider: openai, anthropic, google, or unknown |
| `endpoint` | Original request URI |
| `model` | Model name from the response (null if not available) |
| `status` | HTTP status code from the provider |
| `input_tokens` | Prompt/input token count (null if extraction failed) |
| `output_tokens` | Completion/output token count (null if extraction failed) |
| `masked_key` | Last 6 characters of the API key |
| `error_type` | Error classification (null on success) |

### Token counts

Token extraction is best-effort. Counts may be null when:
- The provider response format is unrecognized
- The response body exceeds the 2 MB capture limit
- The response is streamed and the final event doesn't contain usage data

### File rotation

When the stats file exceeds 100 MB, it is automatically renamed with a timestamp suffix (e.g., `stats.jsonl.20260216120000`) and a new file is started. Old files are not automatically deleted — manage retention externally.

### Querying stats

The stats file is standard JSONL. Use any tool that reads line-delimited JSON:

```bash
# Count requests per provider
cat data/stats.jsonl | jq -r '.provider' | sort | uniq -c | sort -rn

# Total tokens by provider
cat data/stats.jsonl | jq -r '[.provider, .input_tokens // 0, .output_tokens // 0] | @tsv' \
  | awk -F'\t' '{in[$1]+=$2; out[$1]+=$3} END {for(p in in) print p, in[p], out[p]}'

# Requests by owner (match lmgate_id to allowlist)
cat data/stats.jsonl | jq -r '.lmgate_id' | sort | uniq -c | sort -rn
```

## Docker Compose Reference

### Services

| Service | Image | Exposed Port | Purpose |
|---------|-------|-------------|---------|
| `lmgate` | Built from `lmgate/Dockerfile` | None (internal) | Auth decisions + stats collection |
| `nginx` | Built from `nginx/Dockerfile` | `8080` | Client-facing reverse proxy |

### Volumes

Both containers mount:
- `./config` → `/app/config` (read-only) — Configuration files
- `./data` → `/data` — Allow-list and stats output

### Common operations

```bash
# Start
docker compose up -d

# View logs
docker compose logs -f
docker compose logs -f lmgate   # Python service only
docker compose logs -f nginx    # nginx only

# Restart after config changes
docker compose restart lmgate

# Stop
docker compose down

# Rebuild after code changes
docker compose up -d --build
```

## Troubleshooting

### All requests return 403

1. Check that your API key is in `data/allowlist.csv` and matches exactly.
2. Check that the allow-list CSV has the correct headers: `id,api_key,owner,added`.
3. Check LMGate logs: `docker compose logs lmgate`.

### Stats file is empty

1. Verify that requests are being proxied (check nginx access log).
2. Stats are written after the response completes — check that provider responses are succeeding.
3. The stats buffer flushes every 10 seconds by default. Wait and check again.

### Token counts are null

This is expected for:
- Providers or endpoints that don't return usage data in the response body
- Streaming responses where the final event doesn't contain token counts
- Responses larger than 2 MB (body capture is truncated)

### LMGate won't start

1. Check that `config/lmgate.yaml` exists and is valid YAML.
2. Check that `data/allowlist.csv` exists and has the required columns.
3. Review startup logs: `docker compose logs lmgate`.

### nginx returns 502

The LMGate Python service is not reachable. Check that it started successfully:

```bash
docker compose ps
docker compose logs lmgate
```

## Security Notes

- API keys in stats are masked to the last 6 characters. Full keys are never written to the stats file.
- The allow-list CSV contains full API keys — protect this file with appropriate filesystem permissions.
- LMGate does not terminate TLS in the MVP. For production use, place it behind a TLS-terminating load balancer or add TLS configuration to nginx.
- LMGate performs authorization (is this key allowed?), not authentication (who is the caller?). It trusts that the API key identifies the caller.
