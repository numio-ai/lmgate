# LMGate Demo

A minimal Python example that demonstrates routing Anthropic API calls through LMGate and inspecting the captured usage statistics.

## Prerequisites

| Requirement | Notes |
|---|---|
| Docker + Docker Compose | To run LMGate locally |
| Python 3.12+ | For the demo script |
| Valid Anthropic API key | Must be added to `data/allowlist.csv` before running the success scenario |

### 1. Start LMGate

From the repository root:

```bash
docker compose up -d
curl http://localhost:8080/healthz   # Expected: ok
```

### 2. Add your key to the allow-list

Edit `data/allowlist.csv` (create it if absent):

```csv
id,api_key,owner,added
1,sk-ant-your-real-key-here,demo,2026-02-22
```

LMGate hot-reloads the allow-list; no restart needed.

### 3. Install demo dependencies

```bash
pip install -r demo/requirements.txt
```

---

## Success scenario (authorized key)

```bash
./demo/run_demo.sh sk-ant-your-real-key-here
```

Expected output:

```
==> Sending request through LMGate...
Hello! I'm Claude, an AI assistant made by Anthropic. How can I help you today?

==> Waiting 15s for stats flush...

==> Last stats entry from data/stats.jsonl:
{
  "timestamp": "2026-02-22T12:00:10.123456",
  "lmgate_id": "1",
  "provider": "anthropic",
  "endpoint": "/anthropic/v1/messages",
  "model": "claude-haiku-4-5",
  "status": 200,
  "input_tokens": 13,
  "output_tokens": 22,
  ...
}
```

---

## Blocked scenario (unauthorized key)

```bash
./demo/run_demo.sh sk-ant-fake-key-000000000000
```

Expected output:

```
==> Sending request through LMGate...
Request blocked by LMGate (403): API key not authorized

==> Request was not forwarded to the provider (blocked or error). No stats entry expected.
```

The script exits with code 1. No stats entry is written because the request never reaches Anthropic.

---

## How it works

`demo.py` creates an `anthropic.Anthropic` client pointed at `http://localhost:8080/anthropic` instead of the default Anthropic endpoint. The API key travels in the `x-api-key` header exactly as it would in a direct call — LMGate intercepts it, checks the allow-list, and either forwards the request or returns 403.

`run_demo.sh` wraps the Python script, waits 15 seconds for LMGate's stats flush interval, then prints the last line of `data/stats.jsonl`.
