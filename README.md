# LMGate

LMGate is a lightweight transparent proxy that monitors and controls your applications' GenAI API usage. It tracks calls and token consumption across multiple LLM providers — with no code changes required.

```mermaid
graph LR
    A[Your Apps] --> B[LMGate]
    B --> C[LLM Providers]
    B --> C[LLM Providers]
    B --> C[LLM Providers]
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

Confirm it's running:

```bash
curl http://localhost:8080/healthz
# Expected: ok
```

### 3. Make a test call through the proxy

Replace `sk-ant-your-anthropic-key-here` with a key from your allow-list:

```bash
curl http://localhost:8080/anthropic/v1/messages \
  -H "x-api-key: sk-ant-your-anthropic-key-here" \
  -H "anthropic-version: 2023-06-01" \
  -H "Content-Type: application/json" \
  -d '{"model":"claude-sonnet-4-20250514","max_tokens":32,"messages":[{"role":"user","content":"Say hello in one sentence."}]}'
```

You get the normal Anthropic response. A key not in the allow-list returns HTTP 403:

```json
{"error":"forbidden","message":"API key not authorized"}
```

### 4. Inspect captured stats

Stats flush every 10 seconds. After your call:

```bash
sleep 10 && cat data/stats.jsonl | jq .
```

```json
{"timestamp":"...","lmgate_id":"2","provider":"anthropic","endpoint":"/anthropic/v1/messages","model":"claude-sonnet-4-20250514","status":200,"input_tokens":13,"output_tokens":13,...}
```

LMGate is operational.

## Integrate with your application

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

## Provider Routing

| Path Prefix | Upstream |
|-------------|----------|
| `/openai/` | `https://api.openai.com/` |
| `/anthropic/` | `https://api.anthropic.com/` |
| `/google/` | `https://aiplatform.googleapis.com/` |

Request body, headers, and query parameters are forwarded unchanged.

## Operations

```bash
docker compose up -d              # Start
docker compose logs -f            # View logs
docker compose restart lmgate     # Restart after config changes
docker compose down               # Stop
docker compose up -d --build      # Rebuild after code changes
```

## Troubleshooting

**All requests return 403**
1. Check your key is in `data/allowlist.csv` and matches exactly.
2. Check headers: `id,api_key,owner,added` are all present.
3. `docker compose logs lmgate`

**LMGate won't start**
1. Check `config/lmgate.yaml` exists and is valid YAML.
2. Check `data/allowlist.csv` exists with required columns.
3. `docker compose logs lmgate`

## Further reading

- [User Guide](docs/LMGate%20user%20guide.md) — configuration, allow-list management, stats schema, Docker reference
- [Functional Specification](docs/LMGate%20functional%20specification.md) — requirements and design

## License

Apache 2.0 — see [LICENSE](LICENSE) for details.
