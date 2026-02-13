"""YAML + environment variable configuration loading.

Config file: config/lmgate.yaml
Env var override prefix: LMGATE_
Nesting convention: double underscore (e.g. LMGATE_SERVER__PORT)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

_DEFAULT_CONFIG_PATH = Path("config/lmgate.yaml")

_DEFAULTS: dict[str, Any] = {
    "server": {
        "port": 8081,
    },
    "auth": {
        "allowlist_path": "/data/allowlist.csv",
        "poll_interval_seconds": 30,
    },
    "stats": {
        "output_path": "/data/stats.jsonl",
        "flush_interval_seconds": 10,
    },
    "logging": {
        "level": "INFO",
    },
}

ENV_PREFIX = "LMGATE_"


def _deep_merge(base: dict, override: dict) -> dict:
    """Merge override into base, recursively for nested dicts."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _coerce_value(value: str) -> int | float | bool | str:
    """Attempt to coerce a string env var value to a typed value."""
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value


def _apply_env_overrides(config: dict) -> dict:
    """Apply LMGATE_ prefixed environment variables as overrides.

    Double underscore separates nesting levels:
        LMGATE_SERVER__PORT=9090 -> config["server"]["port"] = 9090
    """
    for key, value in os.environ.items():
        if not key.startswith(ENV_PREFIX):
            continue
        parts = key[len(ENV_PREFIX) :].lower().split("__")
        target = config
        for part in parts[:-1]:
            if part not in target:
                target[part] = {}
            target = target[part]
        target[parts[-1]] = _coerce_value(value)
    return config


def load_config(config_path: Path | None = None) -> dict[str, Any]:
    """Load configuration from YAML file with env var overrides.

    Precedence (highest wins): env vars > YAML file > defaults.
    """
    config = _DEFAULTS.copy()
    config = {k: v.copy() if isinstance(v, dict) else v for k, v in config.items()}

    path = config_path or _DEFAULT_CONFIG_PATH
    if path.exists():
        with open(path) as f:
            file_config = yaml.safe_load(f) or {}
        config = _deep_merge(config, file_config)

    config = _apply_env_overrides(config)
    return config
