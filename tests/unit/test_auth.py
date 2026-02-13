"""Tests for lmgate.auth — key extraction and /auth endpoint."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, TestClient

from lmgate.auth import extract_key
from lmgate.allowlist import AllowList
from lmgate.server import create_app


class TestExtractKey:
    def test_bearer_token(self) -> None:
        headers = {"Authorization": "Bearer sk-abc123xyz"}
        assert extract_key(headers) == "sk-abc123xyz"

    def test_bearer_case_insensitive(self) -> None:
        headers = {"Authorization": "bearer sk-abc123xyz"}
        assert extract_key(headers) == "sk-abc123xyz"

    def test_aws_sigv4(self) -> None:
        headers = {
            "Authorization": (
                "AWS4-HMAC-SHA256 "
                "Credential=AKIAIOSFODNN7EXAMPLE/20250601/us-east-1/bedrock/aws4_request, "
                "SignedHeaders=host;x-amz-date, "
                "Signature=abcdef1234567890"
            )
        }
        assert extract_key(headers) == "AKIAIOSFODNN7EXAMPLE"

    def test_x_api_key(self) -> None:
        headers = {"x-api-key": "sk-from-x-api-key"}
        assert extract_key(headers) == "sk-from-x-api-key"

    def test_precedence_bearer_over_x_api_key(self) -> None:
        headers = {
            "Authorization": "Bearer sk-bearer",
            "x-api-key": "sk-xapikey",
        }
        assert extract_key(headers) == "sk-bearer"

    def test_precedence_sigv4_over_x_api_key(self) -> None:
        headers = {
            "Authorization": "AWS4-HMAC-SHA256 Credential=AKIAEXAMPLE/20250601/us-east-1/bedrock/aws4_request, SignedHeaders=host, Signature=abc",
            "x-api-key": "sk-xapikey",
        }
        assert extract_key(headers) == "AKIAEXAMPLE"

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
        path.write_text(
            "id,api_key,owner,added\n"
            "1,sk-validkey,team-alpha,2025-01-15\n"
            "2,AKIAIOSFODNN7EXAMPLE,team-beta,2025-02-01\n"
        )
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
        resp = await client.get("/auth", headers={"Authorization": "Bearer sk-validkey"})
        assert resp.status == 200
        assert resp.headers.get("X-LMGate-ID") == "1"

    async def test_valid_sigv4_returns_200(self, aiohttp_client, app) -> None:
        client = await aiohttp_client(app)
        resp = await client.get(
            "/auth",
            headers={
                "Authorization": "AWS4-HMAC-SHA256 Credential=AKIAIOSFODNN7EXAMPLE/20250601/us-east-1/bedrock/aws4_request, SignedHeaders=host, Signature=abc"
            },
        )
        assert resp.status == 200
        assert resp.headers.get("X-LMGate-ID") == "2"

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
