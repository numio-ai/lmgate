"""Tests for lmgate.auth — key extraction and /auth endpoint."""

from pathlib import Path

import pytest
from aiohttp import web

from lmgate.auth import extract_key
from lmgate.server import create_app


class TestExtractKey:
    def test_bearer_token(self) -> None:
        headers = {"Authorization": "Bearer sk-abc123xyz"}
        assert extract_key(headers) == "sk-abc123xyz"

    def test_bearer_case_insensitive(self) -> None:
        headers = {"Authorization": "bearer sk-abc123xyz"}
        assert extract_key(headers) == "sk-abc123xyz"

    def test_x_api_key(self) -> None:
        headers = {"x-api-key": "sk-from-x-api-key"}
        assert extract_key(headers) == "sk-from-x-api-key"

    def test_precedence_bearer_over_x_api_key(self) -> None:
        headers = {
            "Authorization": "Bearer sk-bearer",
            "x-api-key": "sk-xapikey",
        }
        assert extract_key(headers) == "sk-bearer"

    def test_missing_all_credentials(self) -> None:
        assert extract_key({}) is None

    def test_empty_bearer(self) -> None:
        headers = {"Authorization": "Bearer "}
        assert extract_key(headers) is None

    def test_unknown_auth_scheme(self) -> None:
        headers = {"Authorization": "Basic dXNlcjpwYXNz"}
        assert extract_key(headers) is None


class TestAuthEndpoint:
    @pytest.fixture
    def allowlist_path(self, tmp_path: Path) -> Path:
        path = tmp_path / "allowlist.csv"
        path.write_text("id,api_key,owner,added\n1,sk-validkey,team-alpha,2025-01-15\n")
        return path

    @pytest.fixture
    def app(self, allowlist_path: Path) -> web.Application:
        config = {
            "server": {"port": 8081},
            "auth": {
                "allowlist_path": str(allowlist_path),
                "poll_interval_seconds": 30,
            },
            "stats": {
                "output_path": "/tmp/stats.jsonl",
                "flush_interval_seconds": 10,
            },
            "logging": {"level": "INFO"},
        }
        return create_app(config)

    async def test_valid_bearer_returns_200(self, aiohttp_client, app) -> None:
        client = await aiohttp_client(app)
        resp = await client.get(
            "/auth", headers={"Authorization": "Bearer sk-validkey"}
        )
        assert resp.status == 200
        assert resp.headers.get("X-LMGate-ID") == "1"

    async def test_invalid_key_returns_403(self, aiohttp_client, app) -> None:
        client = await aiohttp_client(app)
        resp = await client.get("/auth", headers={"Authorization": "Bearer sk-invalid"})
        assert resp.status == 403

    async def test_missing_key_returns_403(self, aiohttp_client, app) -> None:
        client = await aiohttp_client(app)
        resp = await client.get("/auth")
        assert resp.status == 403

    async def test_healthz(self, aiohttp_client, app) -> None:
        client = await aiohttp_client(app)
        resp = await client.get("/healthz")
        assert resp.status == 200
