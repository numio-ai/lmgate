"""Tests for lmgate.stats — stats ingestion, JSONL writes, rotation."""

import json
from pathlib import Path

import pytest
from aiohttp import web

from lmgate.server import create_app
from lmgate.stats import StatsWriter, build_stats_entry


class TestBuildStatsEntry:
    def test_full_payload(self) -> None:
        payload = {
            "timestamp": "2025-06-15T10:30:00Z",
            "client_ip": "10.0.0.1",
            "method": "POST",
            "uri": "/v1/chat/completions",
            "host": "api.openai.com",
            "status": 200,
            "auth_key_header": "Bearer sk-abc123xyz",
            "auth_x_api_key": "",
            "lmgate_internal_id": "1",
            "response_body": json.dumps(
                {
                    "model": "gpt-4",
                    "usage": {"prompt_tokens": 150, "completion_tokens": 80},
                }
            ),
        }
        entry = build_stats_entry(payload)
        assert entry["provider"] == "openai"
        assert entry["input_tokens"] == 150
        assert entry["output_tokens"] == 80
        assert entry["model"] == "gpt-4"
        assert entry["lmgate_id"] == "1"
        assert entry["status"] == 200
        assert entry["masked_key"] == "123xyz"
        assert entry["endpoint"] == "/v1/chat/completions"

    def test_missing_response_body(self) -> None:
        payload = {
            "timestamp": "2025-06-15T10:30:00Z",
            "client_ip": "10.0.0.1",
            "method": "POST",
            "uri": "/v1/messages",
            "host": "api.anthropic.com",
            "status": 200,
            "auth_key_header": "Bearer sk-short",
            "auth_x_api_key": "",
            "lmgate_internal_id": "2",
            "response_body": "",
        }
        entry = build_stats_entry(payload)
        assert entry["input_tokens"] is None
        assert entry["output_tokens"] is None
        assert entry["model"] is None

    def test_masked_key_short(self) -> None:
        payload = {
            "timestamp": "2025-06-15T10:30:00Z",
            "client_ip": "10.0.0.1",
            "method": "POST",
            "uri": "/v1/chat/completions",
            "host": "api.openai.com",
            "status": 200,
            "auth_key_header": "Bearer abc",
            "auth_x_api_key": "",
            "lmgate_internal_id": "1",
            "response_body": "",
        }
        entry = build_stats_entry(payload)
        assert entry["masked_key"] == "abc"

    def test_x_api_key_fallback(self) -> None:
        payload = {
            "timestamp": "2025-06-15T10:30:00Z",
            "client_ip": "10.0.0.1",
            "method": "POST",
            "uri": "/v1/messages",
            "host": "api.anthropic.com",
            "status": 200,
            "auth_key_header": "",
            "auth_x_api_key": "sk-ant-key123456",
            "lmgate_internal_id": "3",
            "response_body": "",
        }
        entry = build_stats_entry(payload)
        assert entry["masked_key"] == "123456"


class TestStatsWriter:
    def test_write_single_entry(self, tmp_path: Path) -> None:
        output = tmp_path / "stats.jsonl"
        writer = StatsWriter(str(output))
        entry = {
            "timestamp": "2025-06-15T10:30:00Z",
            "provider": "openai",
            "input_tokens": 150,
        }
        writer.write(entry)
        writer.flush()

        lines = output.read_text().strip().split("\n")
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["provider"] == "openai"

    def test_write_multiple_entries(self, tmp_path: Path) -> None:
        output = tmp_path / "stats.jsonl"
        writer = StatsWriter(str(output))
        for i in range(5):
            writer.write({"index": i})
        writer.flush()

        lines = output.read_text().strip().split("\n")
        assert len(lines) == 5

    def test_flush_on_close(self, tmp_path: Path) -> None:
        output = tmp_path / "stats.jsonl"
        writer = StatsWriter(str(output))
        writer.write({"data": "test"})
        writer.close()

        lines = output.read_text().strip().split("\n")
        assert len(lines) == 1

    def test_rotation_on_size(self, tmp_path: Path) -> None:
        output = tmp_path / "stats.jsonl"
        writer = StatsWriter(str(output), max_bytes=200)
        # Write enough entries to trigger rotation
        for i in range(20):
            writer.write({"index": i, "padding": "x" * 20})
            writer.flush()

        # Original file should still exist and be small
        assert output.exists()
        # At least one rotated file should exist
        rotated = list(tmp_path.glob("stats.jsonl.*"))
        assert len(rotated) >= 1


class TestStatsEndpoint:
    @pytest.fixture
    def allowlist_path(self, tmp_path: Path) -> Path:
        path = tmp_path / "allowlist.csv"
        path.write_text("id,api_key,owner,added\n1,sk-key,team,2025-01-01\n")
        return path

    @pytest.fixture
    def stats_path(self, tmp_path: Path) -> Path:
        return tmp_path / "stats.jsonl"

    @pytest.fixture
    def app(self, allowlist_path: Path, stats_path: Path) -> web.Application:
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

    async def test_stats_endpoint_returns_200(self, aiohttp_client, app) -> None:
        client = await aiohttp_client(app)
        payload = {
            "timestamp": "2025-06-15T10:30:00Z",
            "client_ip": "10.0.0.1",
            "method": "POST",
            "uri": "/v1/chat/completions",
            "host": "api.openai.com",
            "status": 200,
            "auth_key_header": "Bearer sk-abc123xyz",
            "auth_x_api_key": "",
            "lmgate_internal_id": "1",
            "response_body": json.dumps(
                {
                    "model": "gpt-4",
                    "usage": {"prompt_tokens": 150, "completion_tokens": 80},
                }
            ),
        }
        resp = await client.post("/stats", json=payload)
        assert resp.status == 200

    async def test_stats_endpoint_malformed_payload(self, aiohttp_client, app) -> None:
        client = await aiohttp_client(app)
        resp = await client.post("/stats", json={"garbage": True})
        assert resp.status == 200  # graceful handling, never fail
