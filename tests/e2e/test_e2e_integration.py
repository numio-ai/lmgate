"""End-to-end tests for the full Docker Compose stack.

These tests assume the stack is already running (started by run-e2e-tests.sh).
They send HTTP requests through nginx on port 8080 and verify the complete
auth -> proxy -> stats pipeline.
"""

import json
import os
import time
import urllib.error
import urllib.request

NGINX_BASE = os.environ.get("E2E_NGINX_URL", "http://localhost:8080")
VALID_KEY = "sk-test-valid-key-123456"
INVALID_KEY = "sk-invalid-bogus-key"
STATS_PATH = os.environ.get(
    "E2E_STATS_PATH",
    os.path.join(os.path.dirname(__file__), "data", "stats.jsonl"),
)


def _request(method, path, headers=None, body=None):
    """Send an HTTP request and return (status, headers, body_text)."""
    url = f"{NGINX_BASE}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    if body:
        req.add_header("Content-Type", "application/json")
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        return resp.status, dict(resp.headers), resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode()


def _chat_request(api_key):
    """Send a chat completion request through the OpenAI proxy path."""
    return _request(
        "POST",
        "/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        body={
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "hello"}],
        },
    )


def _read_stats_entries():
    """Read all entries from the stats JSONL file."""
    if not os.path.exists(STATS_PATH):
        return []
    entries = []
    with open(STATS_PATH) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def _clear_stats():
    """Remove existing stats file for a clean slate."""
    if os.path.exists(STATS_PATH):
        os.remove(STATS_PATH)


class TestHealthCheck:
    def test_healthz_returns_200(self):
        status, _, body = _request("GET", "/healthz")
        assert status == 200
        assert body == "ok"


class TestAuthorizedRequest:
    def test_valid_key_proxied_to_upstream(self):
        """Authorized request passes through nginx to mock upstream."""
        status, _, body = _chat_request(VALID_KEY)
        assert status == 200
        data = json.loads(body)
        assert data["model"] == "gpt-4"
        assert data["choices"][0]["message"]["content"] == "Hello from mock upstream"
        assert data["usage"]["prompt_tokens"] == 10
        assert data["usage"]["completion_tokens"] == 5


class TestUnauthorizedRequest:
    def test_invalid_key_returns_403(self):
        """Invalid API key is rejected by the auth subrequest."""
        status, _, _ = _chat_request(INVALID_KEY)
        assert status == 403

    def test_missing_key_returns_403(self):
        """Request without any auth header is rejected."""
        status, _, _ = _request(
            "POST",
            "/openai/v1/chat/completions",
            body={"model": "gpt-4", "messages": []},
        )
        assert status == 403


class TestStatsRecording:
    def test_stats_entry_written_after_proxied_request(self):
        """After a successful proxied request, a stats entry appears in JSONL."""
        _clear_stats()

        # Send an authorized request
        status, _, _ = _chat_request(VALID_KEY)
        assert status == 200

        # Stats are written asynchronously (njs fire-and-forget POST).
        # Poll for up to 5 seconds.
        entries = []
        for _ in range(50):
            entries = _read_stats_entries()
            if entries:
                break
            time.sleep(0.1)

        assert len(entries) >= 1, "Expected at least one stats entry"
        entry = entries[-1]
        assert entry["provider"] == "openai"
        assert "/v1/chat/completions" in entry["endpoint"]
        assert entry["status"] == 200
        assert entry["model"] == "gpt-4"
        assert entry["input_tokens"] == 10
        assert entry["output_tokens"] == 5
        # last 6 chars of sk-test-valid-key-123456
        assert entry["masked_key"] == "123456"
