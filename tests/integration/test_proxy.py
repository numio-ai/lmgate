"""Integration tests — full request flow through the LMGate Python app.

Tests the combined auth + stats pipeline end-to-end:
1. Auth check (valid/invalid keys)
2. Stats ingestion with token extraction
3. JSONL output verification
"""

import json
from pathlib import Path

import pytest
from aiohttp import web

from lmgate.server import create_app


@pytest.fixture
def allowlist_path(tmp_path: Path) -> Path:
    path = tmp_path / "allowlist.csv"
    path.write_text(
        "id,api_key,owner,added\n"
        "1,sk-validkey123,team-alpha,2025-01-15\n"
        "2,sk-anthropic-key99,team-gamma,2025-03-01\n"
    )
    return path


@pytest.fixture
def stats_path(tmp_path: Path) -> Path:
    return tmp_path / "stats.jsonl"


@pytest.fixture
def app(allowlist_path: Path, stats_path: Path) -> web.Application:
    config = {
        "server": {"port": 8081},
        "auth": {
            "allowlist_path": str(allowlist_path),
            "poll_interval_seconds": 30,
        },
        "stats": {
            "output_path": str(stats_path),
            "flush_interval_seconds": 10,
        },
        "logging": {"level": "INFO"},
    }
    return create_app(config)


class TestAuthFlow:
    """End-to-end auth verification."""

    async def test_bearer_auth_accepted(self, aiohttp_client, app) -> None:
        client = await aiohttp_client(app)
        resp = await client.get(
            "/auth", headers={"Authorization": "Bearer sk-validkey123"}
        )
        assert resp.status == 200
        assert resp.headers["X-LMGate-ID"] == "1"

    async def test_unknown_key_rejected(self, aiohttp_client, app) -> None:
        client = await aiohttp_client(app)
        resp = await client.get(
            "/auth", headers={"Authorization": "Bearer sk-unknown"}
        )
        assert resp.status == 403

    async def test_x_api_key_auth_accepted(self, aiohttp_client, app) -> None:
        client = await aiohttp_client(app)
        resp = await client.get(
            "/auth", headers={"x-api-key": "sk-anthropic-key99"}
        )
        assert resp.status == 200
        assert resp.headers["X-LMGate-ID"] == "2"

    async def test_no_credentials_rejected(self, aiohttp_client, app) -> None:
        client = await aiohttp_client(app)
        resp = await client.get("/auth")
        assert resp.status == 403


class TestStatsFlow:
    """End-to-end stats ingestion and JSONL output verification."""

    async def test_openai_stats_written(
        self, aiohttp_client, app, stats_path: Path
    ) -> None:
        client = await aiohttp_client(app)
        payload = {
            "timestamp": "2025-06-15T10:30:00Z",
            "client_ip": "10.0.0.1",
            "method": "POST",
            "uri": "/v1/chat/completions",
            "host": "api.openai.com",
            "status": 200,
            "auth_key_header": "Bearer sk-validkey123",
            "auth_x_api_key": "",
            "lmgate_internal_id": "1",
            "response_body": json.dumps({
                "model": "gpt-4",
                "usage": {"prompt_tokens": 150, "completion_tokens": 80},
            }),
        }
        resp = await client.post("/stats", json=payload)
        assert resp.status == 200

        lines = stats_path.read_text().strip().split("\n")
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["provider"] == "openai"
        assert entry["model"] == "gpt-4"
        assert entry["input_tokens"] == 150
        assert entry["output_tokens"] == 80
        assert entry["lmgate_id"] == "1"
        assert entry["masked_key"] == "key123"

    async def test_anthropic_stats_written(
        self, aiohttp_client, app, stats_path: Path
    ) -> None:
        client = await aiohttp_client(app)
        payload = {
            "timestamp": "2025-06-15T10:31:00Z",
            "client_ip": "10.0.0.2",
            "method": "POST",
            "uri": "/v1/messages",
            "host": "api.anthropic.com",
            "status": 200,
            "auth_key_header": "",
            "auth_x_api_key": "sk-anthropic-key99",
            "lmgate_internal_id": "2",
            "response_body": json.dumps({
                "model": "claude-sonnet-4-5-20250929",
                "usage": {"input_tokens": 200, "output_tokens": 100},
            }),
        }
        resp = await client.post("/stats", json=payload)
        assert resp.status == 200

        entry = json.loads(stats_path.read_text().strip())
        assert entry["provider"] == "anthropic"
        assert entry["input_tokens"] == 200
        assert entry["output_tokens"] == 100

    async def test_google_vertex_stats_written(
        self, aiohttp_client, app, stats_path: Path
    ) -> None:
        client = await aiohttp_client(app)
        payload = {
            "timestamp": "2025-06-15T10:32:30Z",
            "client_ip": "10.0.0.5",
            "method": "POST",
            "uri": "/v1/projects/my-project/locations/us-central1/publishers/google/models/gemini-pro:generateContent",
            "host": "aiplatform.googleapis.com",
            "status": 200,
            "auth_key_header": "Bearer ya29.google-token",
            "auth_x_api_key": "",
            "lmgate_internal_id": "1",
            "response_body": json.dumps({
                "candidates": [{"content": {"parts": [{"text": "Hello"}]}}],
                "usageMetadata": {"promptTokenCount": 300, "candidatesTokenCount": 50},
            }),
        }
        resp = await client.post("/stats", json=payload)
        assert resp.status == 200

        entry = json.loads(stats_path.read_text().strip())
        assert entry["provider"] == "google"
        assert entry["input_tokens"] == 300
        assert entry["output_tokens"] == 50

    async def test_stats_with_failed_token_extraction(
        self, aiohttp_client, app, stats_path: Path
    ) -> None:
        """Non-JSON response body: stats entry written with null tokens."""
        client = await aiohttp_client(app)
        payload = {
            "timestamp": "2025-06-15T10:33:00Z",
            "client_ip": "10.0.0.4",
            "method": "POST",
            "uri": "/v1/chat/completions",
            "host": "api.openai.com",
            "status": 500,
            "auth_key_header": "Bearer sk-validkey123",
            "auth_x_api_key": "",
            "lmgate_internal_id": "1",
            "response_body": "Internal Server Error",
        }
        resp = await client.post("/stats", json=payload)
        assert resp.status == 200

        entry = json.loads(stats_path.read_text().strip())
        assert entry["input_tokens"] is None
        assert entry["output_tokens"] is None
        assert entry["status"] == 500


class TestCombinedFlow:
    """Auth + stats together — simulates the full proxy lifecycle."""

    async def test_auth_then_stats(
        self, aiohttp_client, app, stats_path: Path
    ) -> None:
        """Simulate: nginx auth_request → proxy → njs stats POST."""
        client = await aiohttp_client(app)

        # Step 1: Auth check
        auth_resp = await client.get(
            "/auth", headers={"Authorization": "Bearer sk-validkey123"}
        )
        assert auth_resp.status == 200
        lmgate_id = auth_resp.headers["X-LMGate-ID"]
        assert lmgate_id == "1"

        # Step 2: Stats POST (as njs would send after proxying)
        stats_resp = await client.post(
            "/stats",
            json={
                "timestamp": "2025-06-15T10:35:00Z",
                "client_ip": "10.0.0.1",
                "method": "POST",
                "uri": "/v1/chat/completions",
                "host": "api.openai.com",
                "status": 200,
                "auth_key_header": "Bearer sk-validkey123",
                "auth_x_api_key": "",
                "lmgate_internal_id": lmgate_id,
                "response_body": json.dumps({
                    "model": "gpt-4",
                    "usage": {"prompt_tokens": 50, "completion_tokens": 25},
                }),
            },
        )
        assert stats_resp.status == 200

        # Step 3: Verify JSONL output
        entry = json.loads(stats_path.read_text().strip())
        assert entry["lmgate_id"] == "1"
        assert entry["provider"] == "openai"
        assert entry["input_tokens"] == 50
        assert entry["output_tokens"] == 25

    async def test_rejected_auth_no_stats(
        self, aiohttp_client, app, stats_path: Path
    ) -> None:
        """Rejected auth should not produce stats (nginx wouldn't proxy)."""
        client = await aiohttp_client(app)

        auth_resp = await client.get(
            "/auth", headers={"Authorization": "Bearer sk-invalid"}
        )
        assert auth_resp.status == 403
        # No stats file should be created
        assert not stats_path.exists()

    async def test_multiple_requests_accumulate_stats(
        self, aiohttp_client, app, stats_path: Path
    ) -> None:
        client = await aiohttp_client(app)

        for i in range(3):
            resp = await client.post(
                "/stats",
                json={
                    "timestamp": f"2025-06-15T10:4{i}:00Z",
                    "client_ip": "10.0.0.1",
                    "method": "POST",
                    "uri": "/v1/chat/completions",
                    "host": "api.openai.com",
                    "status": 200,
                    "auth_key_header": "Bearer sk-validkey123",
                    "auth_x_api_key": "",
                    "lmgate_internal_id": "1",
                    "response_body": json.dumps({
                        "model": "gpt-4",
                        "usage": {"prompt_tokens": 10 * i, "completion_tokens": 5 * i},
                    }),
                },
            )
            assert resp.status == 200

        lines = stats_path.read_text().strip().split("\n")
        assert len(lines) == 3

    async def test_healthz_always_available(self, aiohttp_client, app) -> None:
        client = await aiohttp_client(app)
        resp = await client.get("/healthz")
        assert resp.status == 200
        assert await resp.text() == "ok"
