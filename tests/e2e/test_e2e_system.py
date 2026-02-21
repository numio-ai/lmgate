"""End-to-end system tests against real LLM APIs.

These tests send real HTTP requests through the full Docker Compose stack
(nginx -> real LLM provider -> njs stats -> lmgate) and verify that JSONL
stats entries are recorded correctly.

Tests are skipped if the corresponding API key is not set in the environment.
The stack must already be running (started by run-e2e-system-tests.sh).
"""

import json
import os
import time
import urllib.request
import urllib.error

import pytest

NGINX_BASE = os.environ.get("E2E_NGINX_URL", "http://localhost:8080")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
STATS_PATH = os.environ.get(
    "E2E_STATS_PATH",
    os.path.join(os.path.dirname(__file__), "data", "stats.jsonl"),
)

MAX_STATS_WAIT = 10  # seconds to poll for stats entry


def _request(method, path, headers=None, body=None, timeout=30):
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
        resp = urllib.request.urlopen(req, timeout=timeout)
        return resp.status, dict(resp.headers), resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode()


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


def _poll_stats(min_entries=1):
    """Poll for stats entries up to MAX_STATS_WAIT seconds."""
    for _ in range(MAX_STATS_WAIT * 10):
        entries = _read_stats_entries()
        if len(entries) >= min_entries:
            return entries
        time.sleep(0.1)
    return _read_stats_entries()


@pytest.mark.skipif(not OPENAI_API_KEY, reason="OPENAI_API_KEY not set")
class TestOpenAI:
    def test_chat_completion_stats(self):
        """Send a real request to OpenAI and verify stats entry."""
        _clear_stats()

        status, _, body = _request(
            "POST",
            "/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            body={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "Say hi"}],
                "max_tokens": 10,
            },
        )
        assert status == 200, f"OpenAI request failed with status {status}: {body}"

        # Verify response is valid OpenAI format
        data = json.loads(body)
        assert "choices" in data
        assert "usage" in data

        # Poll for stats entry
        entries = _poll_stats()
        assert len(entries) >= 1, "Expected at least one stats entry"

        entry = entries[-1]
        assert entry["provider"] == "openai"
        assert entry["model"], "model should be non-empty"
        assert entry["input_tokens"] is not None and entry["input_tokens"] > 0
        assert entry["output_tokens"] is not None and entry["output_tokens"] > 0
        assert entry["status"] == 200
        assert "/v1/chat/completions" in entry["endpoint"]


@pytest.mark.skipif(not ANTHROPIC_API_KEY, reason="ANTHROPIC_API_KEY not set")
class TestAnthropic:
    def test_message_stats(self):
        """Send a real request to Anthropic and verify stats entry."""
        _clear_stats()

        status, _, body = _request(
            "POST",
            "/anthropic/v1/messages",
            headers={
                "X-Api-Key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
            },
            body={
                "model": "claude-3-haiku-20240307",
                "max_tokens": 10,
                "messages": [{"role": "user", "content": "Say hi"}],
            },
        )
        assert status == 200, f"Anthropic request failed with status {status}: {body}"

        # Verify response is valid Anthropic format
        data = json.loads(body)
        assert "content" in data
        assert "usage" in data

        # Poll for stats entry
        entries = _poll_stats()
        assert len(entries) >= 1, "Expected at least one stats entry"

        entry = entries[-1]
        assert entry["provider"] == "anthropic"
        assert entry["model"], "model should be non-empty"
        assert entry["input_tokens"] is not None and entry["input_tokens"] > 0
        assert entry["output_tokens"] is not None and entry["output_tokens"] > 0
        assert entry["status"] == 200
        assert "/v1/messages" in entry["endpoint"]
