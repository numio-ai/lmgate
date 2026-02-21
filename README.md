# LMGate

LMGate is a transparent proxy that sits between your applications and LLM API providers (OpenAI, Anthropic, Google Vertex AI). It controls access via API key allow-lists and collects usage statistics — without modifying API calls.

```
Your Apps  -->  LMGate (proxy)  -->  LLM Provider APIs
```

## Quick Start

### 1. Clone and prepare the allow-list

```bash
git clone git@github.com:numio-ai/lmgate.git
cd lmgate
```

Create `data/allowlist.csv` with the API keys you want to authorize:

```csv
id,api_key,owner,added
1,sk-proj-your-openai-key-here,dev-team,2026-02-16
2,sk-ant-your-anthropic-key-here,dev-team,2026-02-16
```

All four columns are required. The `id` field appears in stats records as `lmgate_id`.

### 2. Start LMGate

```bash
docker compose up -d
```

This starts two containers:
- **lmgate** — Python service (port 8081, internal only)
- **nginx** — Reverse proxy (port 8080, client-facing)

### 3. Point your client at LMGate

Set your LLM SDK's base URL to `http://<lmgate-host>:8080/<provider>/`:

**OpenAI (Python SDK):**

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

**Anthropic (Python SDK):**

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

**curl (OpenAI):**

```bash
curl http://localhost:8080/openai/v1/chat/completions \
  -H "Authorization: Bearer sk-proj-your-openai-key-here" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4","messages":[{"role":"user","content":"Hello"}]}'
```

### 4. Verify

```bash
curl http://localhost:8080/healthz
# Expected: ok
```

A request with a valid key returns the normal provider response. A request with an invalid key returns HTTP 403.

## Provider Routing

LMGate routes requests by URL path prefix. nginx strips the prefix before forwarding to the provider.

| Path Prefix | Upstream Provider |
|-------------|-------------------|
| `/openai/` | `https://api.openai.com/` |
| `/anthropic/` | `https://api.anthropic.com/` |
| `/google/` | `https://aiplatform.googleapis.com/` |

The request body, headers, and query parameters are forwarded unchanged.

## Allow-List Management

### File format

The allow-list is a CSV file with four required columns:

| Column | Description |
|--------|-------------|
| `id` | Internal identifier (appears in stats as `lmgate_id`) |
| `api_key` | The full API key to match |
| `owner` | Human-readable label for the key owner |
| `added` | Date the key was added |

### Adding or removing keys

Edit the CSV file directly. LMGate polls the file every 30 seconds (configurable) and reloads automatically when it detects a change. No restart is needed.

```bash
echo '4,sk-new-key-here,new-team,2026-02-16' >> data/allowlist.csv
```

### Key extraction

LMGate extracts the API key from request headers in this order:

1. `Authorization: Bearer <key>`
2. `x-api-key` header

## Configuration

### Config file

Primary configuration: `config/lmgate.yaml`

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

LMGate writes usage records to an append-only JSONL file (one JSON object per line). Default location: `data/stats.jsonl`.

### Record format

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

Token counts may be null when the provider response format is unrecognized, the response body exceeds the 2 MB capture limit, or the streaming response's final event doesn't contain usage data.

### File rotation

When the stats file exceeds 100 MB, it is automatically renamed with a timestamp suffix (e.g., `stats.jsonl.20260216120000`) and a new file is started. Old files are not automatically deleted.

### Querying stats

```bash
# Count requests per provider
cat data/stats.jsonl | jq -r '.provider' | sort | uniq -c | sort -rn

# Total tokens by provider
cat data/stats.jsonl | jq -r '[.provider, .input_tokens // 0, .output_tokens // 0] | @tsv' \
  | awk -F'\t' '{in[$1]+=$2; out[$1]+=$3} END {for(p in in) print p, in[p], out[p]}'
```

## Docker Compose Reference

### Services

| Service | Exposed Port | Purpose |
|---------|-------------|---------|
| `lmgate` | None (internal) | Auth decisions + stats collection |
| `nginx` | `8080` | Client-facing reverse proxy |

### Volumes

Both containers mount:
- `./config` -> `/app/config` (read-only) — configuration files
- `./data` -> `/data` — allow-list and stats output

### Common operations

```bash
docker compose up -d              # Start
docker compose logs -f            # View all logs
docker compose logs -f lmgate     # Python service logs
docker compose logs -f nginx      # nginx logs
docker compose restart lmgate     # Restart after config changes
docker compose down               # Stop
docker compose up -d --build      # Rebuild after code changes
```

## Troubleshooting

### All requests return 403

1. Check that your API key is in `data/allowlist.csv` and matches exactly.
2. Check that the CSV has correct headers: `id,api_key,owner,added`.
3. Check LMGate logs: `docker compose logs lmgate`.

### Stats file is empty

1. Verify requests are being proxied (check nginx access log).
2. Stats are written after the response completes — check that provider responses are succeeding.
3. The stats buffer flushes every 10 seconds by default. Wait and check again.

### Token counts are null

Expected for providers/endpoints that don't return usage data, streaming responses where the final event doesn't contain token counts, or responses larger than 2 MB.

### LMGate won't start

1. Check that `config/lmgate.yaml` exists and is valid YAML.
2. Check that `data/allowlist.csv` exists and has the required columns.
3. Review startup logs: `docker compose logs lmgate`.

### nginx returns 502

The LMGate Python service is not reachable:

```bash
docker compose ps
docker compose logs lmgate
```

## Security Notes

- API keys in stats are masked to the last 6 characters. Full keys are never written to the stats file.
- The allow-list CSV contains full API keys — protect this file with appropriate filesystem permissions.
- LMGate does not terminate TLS. For production use, place it behind a TLS-terminating load balancer or add TLS configuration to nginx.
- LMGate performs authorization (is this key allowed?), not authentication (who is the caller?).

## License

Apache 2.0 — see [LICENSE](LICENSE) for details.
