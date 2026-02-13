"""Tests for lmgate.config — YAML loading, env var overrides, defaults."""

import os
from pathlib import Path

import pytest

from lmgate.config import load_config


class TestLoadConfig:
    def test_defaults_when_no_file(self, tmp_path: Path) -> None:
        config = load_config(tmp_path / "nonexistent.yaml")
        assert config["server"]["port"] == 8081
        assert config["auth"]["poll_interval_seconds"] == 30
        assert config["stats"]["flush_interval_seconds"] == 10
        assert config["logging"]["level"] == "INFO"

    def test_yaml_overrides_defaults(self, tmp_path: Path) -> None:
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("server:\n  port: 9090\n")
        config = load_config(yaml_file)
        assert config["server"]["port"] == 9090
        # Other defaults preserved
        assert config["auth"]["poll_interval_seconds"] == 30

    def test_env_var_overrides_yaml(self, tmp_path: Path, monkeypatch) -> None:
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("server:\n  port: 9090\n")
        monkeypatch.setenv("LMGATE_SERVER__PORT", "7070")
        config = load_config(yaml_file)
        assert config["server"]["port"] == 7070

    def test_env_var_bool_coercion(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setenv("LMGATE_LOGGING__LEVEL", "DEBUG")
        config = load_config(tmp_path / "nonexistent.yaml")
        assert config["logging"]["level"] == "DEBUG"


class TestShutdown:
    def test_stats_writer_flush_on_close(self, tmp_path: Path) -> None:
        """StatsWriter.close() must flush buffered entries."""
        from lmgate.stats import StatsWriter

        output = tmp_path / "stats.jsonl"
        writer = StatsWriter(str(output))
        writer.write({"data": "entry1"})
        writer.write({"data": "entry2"})
        # Don't call flush — only close
        writer.close()

        lines = output.read_text().strip().split("\n")
        assert len(lines) == 2

    async def test_app_cleanup_flushes_stats(self, tmp_path: Path) -> None:
        """App cleanup signal should flush the stats writer."""
        from aiohttp import web
        from lmgate.server import create_app

        allowlist = tmp_path / "allowlist.csv"
        allowlist.write_text("id,api_key,owner,added\n1,sk-key,team,2025-01-01\n")
        stats_path = tmp_path / "stats.jsonl"

        config = {
            "server": {"port": 8081},
            "auth": {"allowlist_path": str(allowlist), "poll_interval_seconds": 30},
            "stats": {"output_path": str(stats_path), "flush_interval_seconds": 10},
            "logging": {"level": "INFO"},
        }
        app = create_app(config)
        writer = app["stats_writer"]
        writer.write({"data": "buffered"})

        # Run the full app lifecycle so on_cleanup fires
        runner = web.AppRunner(app)
        await runner.setup()
        await runner.cleanup()

        lines = stats_path.read_text().strip().split("\n")
        assert len(lines) == 1
